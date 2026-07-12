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

from dataclasses import dataclass, field
from pathlib import Path

from .db import get_connection

# A "(tbd)" cell means the name in that language is not fixed yet — not an alias.
_TBD = "(tbd)"


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

    def all(self) -> list[SeedEntity]:
        return list(self.persons)


def _split_row(line: str) -> list[str] | None:
    """Split a markdown table row into trimmed cells, or None if not a row."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    # drop the leading/trailing pipe, split on the rest
    cells = [c.strip() for c in s.strip("|").split("|")]
    return cells


def parse_noms(path: str) -> Cast:
    """Parse a noms.md registry into a Cast (persons only, from the enforced table).

    The enforced person table has a header row "| slug | FR | EN | ZH |" followed
    by a "|---|---|" separator and one row per character. FR is the canonical
    name; EN/ZH (when not "(tbd)") become aliases.
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()

    persons: list[SeedEntity] = []
    in_enforced = False       # inside the "Personnages (enforced ...)" section
    header_seen = False       # have we passed the "| slug | FR | EN | ZH |" header

    for line in lines:
        stripped = line.strip()
        # Section boundaries: enforced persons section starts at its heading and
        # ends at the next "## " heading (the advisory table).
        if stripped.startswith("## "):
            in_enforced = stripped.lower().startswith("## personnages")
            header_seen = False
            continue
        if not in_enforced:
            continue

        cells = _split_row(line)
        if not cells or len(cells) < 2:
            continue
        # Skip the header row and the |---|---| separator row.
        if cells[0].lower() == "slug":
            header_seen = True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if not header_seen:
            continue

        # cells = [slug, FR, EN, ZH]
        fr = cells[1] if len(cells) > 1 else ""
        if not fr or fr == _TBD:
            continue
        aliases = []
        for extra in cells[2:4]:  # EN, ZH
            if extra and extra != _TBD and extra != fr:
                aliases.append(extra)
        persons.append(SeedEntity(canonical_name=fr, entity_type="person", aliases=aliases))

    return Cast(persons=persons)


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
