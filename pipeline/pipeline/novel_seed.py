"""Deterministic cast seed for novel corpora — anchor persons from ground truth.

WHAT: Parses a corpus's canonical name registry (the roman's `etat/noms.md`) into
a Cast of known persons (canonical FR name + cross-language aliases), and inserts
them into the DB as person entities BEFORE extraction.

WHY: the LLM alone extracts generic role-nouns as persons ("Fille", "Garçon")
and misses cross-language names — and the wishlist §6 low-trust rule says
intimate links must not be hallucinated. Seeding the KNOWN cast deterministically
gives extraction a canonical anchor: because the runner builds its entity_lookup
from the DB, seeded persons + their aliases are automatically fed to the pattern
pass, so mentions canonicalize to the real character (e.g. a Chinese name → the
FR canonical) instead of spawning a generic-noun person. The LLM still enriches
descriptions and relations, but around a trustworthy person list.

This is DATA-DRIVEN, not hardcoded game knowledge: the cast is read from the
customer's own registry file at runtime (like reference_entities.json for civ).

STATUS: v1 seeds the enforced PERSON table only (the mindmap's stars, where the
generic-noun problem lives). Groups/places (the advisory table) are left to the
LLM for now.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .db import get_connection

# A "(tbd)" cell means the name in that language is not fixed yet — not an alias.
_TBD = "(tbd)"

# Advisory-table typing heuristic (peoples/places/things have no explicit type
# column). Keyword scan on the FR cell; default = place (settlements, spots).
_ADVISORY_GROUP_KW = ("peuple", "gens", "clan", "tribu", "famille", "lignee", "lignée")
_ADVISORY_OBJECT_KW = ("(plat)", "(racine)", "(plante)", "(outil)", "(objet)", "(arme)")


def _advisory_type(fr_cell: str) -> str:
    """Best-effort entity type for an advisory-table entry from its FR text."""
    low = fr_cell.lower()
    if any(k in low for k in _ADVISORY_OBJECT_KW):
        return "object"
    if any(k in low for k in _ADVISORY_GROUP_KW):
        return "group"
    return "place"


def _clean_fr_forms(fr_cell: str) -> list[str]:
    """Split an FR cell into name forms: strip parentheticals, split on '/',
    drop leading articles. First form = canonical, rest = aliases."""
    no_paren = re.sub(r"\s*\([^)]*\)", "", fr_cell).strip()
    forms = []
    for part in no_paren.split("/"):
        cleaned = re.sub(r"^(les|la|le|l')\s+", "", part.strip(), flags=re.IGNORECASE).strip()
        if cleaned:
            forms.append(cleaned)
    return forms


def _zh_aliases(zh_cell: str) -> list[str]:
    """Split a ZH cell into individual aliases (e.g. '高脚屋 / 水寨')."""
    if not zh_cell or zh_cell == _TBD:
        return []
    return [z.strip() for z in zh_cell.split("/") if z.strip() and z.strip() != _TBD]


@dataclass
class SeedEntity:
    """One seeded entity: a canonical name, a type, and its known aliases."""
    canonical_name: str
    entity_type: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class Cast:
    """The parsed cast of a corpus."""
    persons: list[SeedEntity] = field(default_factory=list)
    # Advisory entries (peoples/places/things) — typed group/place/object.
    others: list[SeedEntity] = field(default_factory=list)

    def all(self) -> list[SeedEntity]:
        return list(self.persons) + list(self.others)


def _split_row(line: str) -> list[str] | None:
    """Split a markdown table row into trimmed cells, or None if not a row."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    # drop the leading/trailing pipe, split on the rest
    cells = [c.strip() for c in s.strip("|").split("|")]
    return cells


def parse_noms(path: str) -> Cast:
    """Parse a noms.md registry into a Cast.

    Two tables, each "| key | FR | EN | ZH |" with a header + separator row:
    - "## Personnages (enforced …)" → persons (FR canonical, EN/ZH aliases).
    - "## Peuples, lieux, choses …"  → advisory entries, typed group/place/object
      by keyword (default place); FR may carry variant forms ("a / b") and a
      parenthetical hint; ZH may list several forms.
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()

    persons: list[SeedEntity] = []
    others: list[SeedEntity] = []
    section: str | None = None    # "persons" | "advisory" | None
    header_seen = False           # passed the "| key | FR | EN | ZH |" header

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            low = stripped.lower()
            if low.startswith("## personnages"):
                section = "persons"
            elif low.startswith("## peuples"):
                section = "advisory"
            else:
                section = None
            header_seen = False
            continue
        if section is None:
            continue

        cells = _split_row(line)
        if not cells or len(cells) < 2:
            continue
        # Skip the header row and the |---|---| separator row.
        if cells[0].lower() in ("slug", "clé", "cle"):
            header_seen = True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if not header_seen:
            continue

        # cells = [key, FR, EN, ZH]
        fr = cells[1] if len(cells) > 1 else ""
        en = cells[2] if len(cells) > 2 else ""
        zh = cells[3] if len(cells) > 3 else ""
        if not fr or fr == _TBD:
            continue

        if section == "persons":
            aliases = [x for x in (en, zh) if x and x != _TBD and x != fr]
            persons.append(SeedEntity(canonical_name=fr, entity_type="person", aliases=aliases))
        else:  # advisory
            forms = _clean_fr_forms(fr)
            if not forms:
                continue
            canonical = forms[0]
            aliases = forms[1:] + ([en] if en and en != _TBD else []) + _zh_aliases(zh)
            others.append(SeedEntity(
                canonical_name=canonical,
                entity_type=_advisory_type(fr),
                aliases=[a for a in aliases if a and a != canonical],
            ))

    return Cast(persons=persons, others=others)


def apply_seed(db_path: str, civ_id: int, cast: Cast) -> dict[str, int]:
    """Insert the cast's entities + aliases into the DB for a civ scope.

    Idempotent: an entity already present (same canonical_name + civ_id) is
    reused, not duplicated; aliases are inserted only if new. Returns counts.
    """
    conn = get_connection(db_path)
    entities_added = 0
    aliases_added = 0
    try:
        for ent in cast.all():
            row = conn.execute(
                "SELECT id FROM entity_entities WHERE canonical_name = ? AND civ_id = ?",
                (ent.canonical_name, civ_id),
            ).fetchone()
            if row:
                entity_id = row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, is_active) "
                    "VALUES (?, ?, ?, 1)",
                    (ent.canonical_name, ent.entity_type, civ_id),
                )
                entity_id = cur.lastrowid
                entities_added += 1

            for alias in ent.aliases:
                exists = conn.execute(
                    "SELECT 1 FROM entity_aliases WHERE entity_id = ? AND alias = ?",
                    (entity_id, alias),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
                        (entity_id, alias),
                    )
                    aliases_added += 1
        conn.commit()
    finally:
        conn.close()

    return {"entities_added": entities_added, "aliases_added": aliases_added}
