"""Wiki generator -- produces MkDocs Material markdown pages from the Aurelm database.

Usage:
    python generate.py --db ../pipeline/test_e2e.db --out docs
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[àâä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[îï]", "i", s)
    s = re.sub(r"[ôö]", "o", s)
    s = re.sub(r"[ùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[œ]", "oe", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# -- Entity filtering ---------------------------------------------------------
# spaCy's general NER picks up noise (YouTube metadata, markdown artifacts).
# We filter entities to keep only those that look like real game content.

NOISE_PATTERNS = re.compile(
    r"^("
    r"https?://|www\.|youtube|spotify"
    r"|.{1,2}$"           # 1-2 char strings
    r"|.*\n.*"            # multiline
    r"|.*[{}\[\]<>].*"   # markdown/code artifacts
    r"|__(.*?)__"         # underline markers
    r"|\*\*(.*?)\*\*$"   # bold-only strings
    r"|\d+$"             # pure numbers
    r")",
    re.IGNORECASE,
)

# Known noise entities from spaCy general model
NOISE_NAMES = {
    "Geiita", "Bartosz Pokrywka", "Carolina Romero", "Rithelgo",
    "Bartosz Pokrywka - Topic", "YouTube",
    "Blanc", "Hier", "Rare", "But", "Observer", "Transporter",
    "Organisation", "Formes", "Halls", "Hall", "Cercle", "Antre",
    "Biens", "Autre", "Autres", "Chef du", "Gardiens de",
    "Jimmys G", "Deadfire", "MIENNE", "TOUTES", "Message",
    "Ravitaillé", "Touché", "Planche", "Libre", "Lootbox", "Farouche",
    # Common French words that spaCy misidentifies as entities
    "Village", "Méthode", "Couche", "Premiers", "Échanges", "Esprits",
    "Lances", "Sculptures", "Tribunal", "Shamans", "Façonneurs",
    "Amélioration", "Conseil", "Acquisitions", "Montés",
    "Posséder", "Ramassez", "médier",
    "Faucon", "Cercles", "Échos", "Équipes", "Cliques",
    "Rubanc", "Sanciel",  # player name, ambiguous short form
}

# Noise patterns in entity names that indicate NER mis-extraction
NOISE_CONTENT = {
    "Choix", "Option", "option libre", "Option libre",
    "Pillar", "Soundtrack", "DETECTIVE", "Topic",
    "Tu es ", "Tu t'", "Et maintenant", "Puis tu",
    "Everybody wants", "The end of",
}


def is_noise_entity(name: str) -> bool:
    """Check if an entity name is likely noise rather than real game content."""
    if name in NOISE_NAMES:
        return True
    if NOISE_PATTERNS.match(name):
        return True
    if name.endswith("**") or name.startswith("**"):
        return True
    if "\n" in name:
        return True
    if any(noise in name for noise in NOISE_CONTENT):
        return True
    # Very long entity names are almost certainly NER noise
    if len(name) > 50:
        return True
    # Names with __ are NER artifacts (e.g. "Autre__")
    if "__" in name:
        return True
    # Names ending/starting with ) or ( are parsing artifacts (e.g. "Capture)")
    if name.endswith(")") or name.startswith("("):
        return True
    # Names that are just punctuation or whitespace fragments
    if not any(c.isalpha() for c in name):
        return True
    # Names starting with common French articles alone (e.g. "Le ", "La ", "Les ")
    # that are too short to be real entities
    if re.match(r"^(Le|La|Les|Un|Une|Des|Du|De)\s*$", name, re.IGNORECASE):
        return True
    # Markdown bold anywhere in the name
    if "**" in name:
        return True
    # Truncated entities ending with a preposition (e.g. "Chef de la", "Les Gardiens de")
    if re.search(r"\b(de|du|des|de la|de l')\s*$", name, re.IGNORECASE):
        return True
    # Entity names that look like sentence fragments (contain verb-like patterns)
    if re.search(r"\b(est|sont|fut|sera|était)\b", name, re.IGNORECASE):
        return True
    # Names starting with indefinite articles/determinants = NER noise
    # (but NOT "Le/La/Les" which are common in proper names like "La Confluence")
    if re.match(r"^(Que|Ces|Cet|Cette|Un|Une|Des)\s", name):
        return True
    # Names containing colon (truncated headers like "Deuxième Révélation : La")
    if ":" in name:
        return True
    # Names starting with "Chef de" (truncated titles)
    if re.match(r"^Chef de\b", name):
        return True
    return False


# -- Page generators -----------------------------------------------------------

def generate_index(conn: sqlite3.Connection) -> str:
    """Generate the wiki homepage."""
    civ_count = conn.execute("SELECT count(*) FROM civ_civilizations").fetchone()[0]
    turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
    mention_count = conn.execute("SELECT count(*) FROM entity_mentions").fetchone()[0]

    civs = conn.execute("SELECT name, player_name FROM civ_civilizations ORDER BY name").fetchall()
    civ_lines = []
    for r in civs:
        line = f"- [{r['name']}](civilizations/{slugify(r['name'])}/index.md)"
        if r["player_name"]:
            line += f" *(joueur: {r['player_name']})*"
        civ_lines.append(line)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "# Aurelm Wiki",
        "",
        "Bienvenue sur le wiki du monde d'Aurelm, genere automatiquement a partir des tours de jeu.",
        "",
        "## Statistiques",
        "",
        "| | |",
        "|---|---|",
        f"| Civilisations | **{civ_count}** |",
        f"| Tours de jeu | **{turn_count}** |",
        f"| Entites uniques | **{entity_count}** |",
        f"| Mentions d'entites | **{mention_count}** |",
        "",
        "## Civilisations",
        "",
        *civ_lines,
        "",
        "## Navigation",
        "",
        "- **[Civilisations](civilizations/index.md)** -- Historique et entites de chaque civilisation",
        "- **[Timeline](global/timeline.md)** -- Chronologie globale des tours de jeu",
        "- **[Entites](global/entities.md)** -- Index de toutes les entites par type",
        "- **[Pipeline](meta/pipeline.md)** -- Statistiques du pipeline ML",
        "",
        "---",
        "",
        f"*Derniere mise a jour : {now}*",
        "",
    ]
    return "\n".join(lines)


def generate_civilizations_index(conn: sqlite3.Connection) -> str:
    """Generate the civilizations list page."""
    civs = conn.execute(
        "SELECT c.*, COUNT(t.id) as turn_count "
        "FROM civ_civilizations c LEFT JOIN turn_turns t ON t.civ_id = c.id "
        "GROUP BY c.id ORDER BY c.name"
    ).fetchall()

    lines = [
        "# Civilisations",
        "",
        "| Civilisation | Joueur | Tours | Entites |",
        "|---|---|---|---|",
    ]
    for c in civs:
        entity_count = conn.execute(
            "SELECT count(*) FROM entity_entities WHERE civ_id = ?", (c["id"],)
        ).fetchone()[0]
        slug = slugify(c["name"])
        lines.append(f"| [{c['name']}]({slug}/index.md) | {c['player_name'] or '-'} | {c['turn_count']} | {entity_count} |")

    lines.append("")
    return "\n".join(lines)


def generate_civ_index(conn: sqlite3.Connection, civ_id: int, civ_name: str, player_name: str | None) -> str:
    """Generate a civilization's overview page."""
    turn_count = conn.execute(
        "SELECT count(*) FROM turn_turns WHERE civ_id = ?", (civ_id,)
    ).fetchone()[0]

    entity_rows = conn.execute(
        "SELECT entity_type, count(*) as c FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY c DESC",
        (civ_id,),
    ).fetchall()

    recent_turns = conn.execute(
        "SELECT turn_number, summary FROM turn_turns WHERE civ_id = ? ORDER BY turn_number DESC LIMIT 5",
        (civ_id,),
    ).fetchall()

    lines = [
        f"# {civ_name}",
        "",
    ]
    if player_name:
        lines.append(f"**Joueur** : {player_name}")
        lines.append("")

    lines.extend([
        f"**Tours de jeu** : {turn_count}",
        "",
        "## Entites par type",
        "",
        "| Type | Nombre |",
        "|---|---|",
    ])
    for r in entity_rows:
        lines.append(f"| {_entity_type_label(r['entity_type'])} | {r['c']} |")

    lines.extend(["", "## Derniers tours", ""])
    for t in reversed(list(recent_turns)):
        summary_preview = _clean_summary(t["summary"] or "")[:120]
        lines.append(f"- **Tour {t['turn_number']}** -- {summary_preview}...")

    lines.extend([
        "",
        "## Pages",
        "",
        "- [Historique complet des tours](turns.md)",
        "- [Index des entites](entities.md)",
        "",
    ])
    return "\n".join(lines)


def generate_civ_turns(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> str:
    """Generate turn-by-turn history for a civilization.

    Renders each turn with:
    1. Summary block (detailed + key events + choices)
    2. Raw messages grouped by author (GM vs player), cleaned
    """
    turns = conn.execute(
        "SELECT * FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
        (civ_id,),
    ).fetchall()

    # Detect GM author(s) by frequency -- GM posts more than players
    gm_authors = _detect_gm_authors(conn)

    lines = [f"# {civ_name} -- Historique des tours", ""]

    for turn in turns:
        turn_id = turn["id"]

        # Use detailed_summary if available, fall back to short summary
        detailed = _clean_summary(turn["detailed_summary"] or "") if turn["detailed_summary"] else ""
        short = _clean_summary(turn["summary"] or "")
        display_summary = detailed or short or "Pas de resume disponible."

        key_events = _parse_json_list(turn["key_events"])
        choices_made = _parse_json_list(turn["choices_made"])

        entities = conn.execute(
            """SELECT DISTINCT e.canonical_name, e.entity_type
               FROM entity_mentions m JOIN entity_entities e ON m.entity_id = e.id
               WHERE m.turn_id = ? ORDER BY e.entity_type, e.canonical_name""",
            (turn_id,),
        ).fetchall()

        entity_tags = ", ".join(
            f"`{_capitalize_entity(e['canonical_name'])}`"
            for e in entities
            if not is_noise_entity(e["canonical_name"])
        )

        lines.extend([
            f"## Tour {turn['turn_number']}",
            "",
            f"> {display_summary[:400]}",
            "",
        ])

        if key_events:
            lines.append("**Evenements cles** :")
            lines.append("")
            for evt in key_events:
                lines.append(f"- {evt}")
            lines.append("")

        if choices_made:
            lines.append("**Choix effectues** :")
            lines.append("")
            for choice in choices_made:
                lines.append(f"- {choice}")
            lines.append("")

        lines.extend([
            f"**Entites** : {entity_tags if entity_tags else 'aucune'}",
            "",
        ])

        # Render raw messages grouped by author (GM / Player)
        raw_ids = _parse_json_list(turn["raw_message_ids"])
        if raw_ids:
            message_groups = _group_messages_by_author(conn, raw_ids, gm_authors)
            for group in message_groups:
                role_label = "Maitre du Jeu" if group["is_gm"] else group["author"]
                lines.append(f"### {role_label}")
                lines.append("")
                content = _clean_segment_content(group["content"])
                if content:
                    # Downgrade ### headers in content to #### to avoid collision with author headers
                    content = re.sub(r"^### ", "#### ", content, flags=re.MULTILINE)
                    lines.append(content)
                    lines.append("")

        lines.extend(["---", ""])

    return "\n".join(lines)


def _build_fused_entities(conn: sqlite3.Connection, civ_id: int) -> list[dict]:
    """Detect and merge duplicate entities within a civilization.

    Builds a graph of "same entity" relationships by checking:
    - Entity A has an alias matching Entity B's canonical_name (or vice versa)
    - Entity A's canonical_name appears as a substring of Entity B's (case-insensitive)

    Returns a list of fused entity dicts with merged stats.
    """
    entities = conn.execute(
        """SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
                  e.first_seen_turn, e.last_seen_turn,
                  (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
           FROM entity_entities e
           WHERE e.civ_id = ?
           ORDER BY e.canonical_name""",
        (civ_id,),
    ).fetchall()

    # Build alias lookup: entity_id -> set of alias strings (lowered)
    alias_lookup: dict[int, set[str]] = {}
    for e in entities:
        eid = e["id"]
        aliases = conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (eid,)
        ).fetchall()
        alias_lookup[eid] = {a["alias"].lower().strip() for a in aliases}

    # Build name lookup: lowered canonical_name -> entity row
    name_to_entity: dict[str, list] = {}
    for e in entities:
        key = e["canonical_name"].lower().strip()
        name_to_entity.setdefault(key, []).append(e)

    # Union-Find for grouping
    parent: dict[int, int] = {e["id"]: e["id"] for e in entities}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Merge entities where alias matches another entity's canonical name
    for e in entities:
        eid = e["id"]
        e_name_lower = e["canonical_name"].lower().strip()
        # Check if any other entity's canonical_name matches one of our aliases
        for alias in alias_lookup.get(eid, set()):
            if alias in name_to_entity:
                for other in name_to_entity[alias]:
                    if other["id"] != eid and other["entity_type"] == e["entity_type"]:
                        union(eid, other["id"])
        # Check if our canonical name matches another entity's alias
        for other in entities:
            if other["id"] == eid or other["entity_type"] != e["entity_type"]:
                continue
            if e_name_lower in alias_lookup.get(other["id"], set()):
                union(eid, other["id"])

    # Known fusion pairs (domain knowledge for this game)
    _KNOWN_FUSIONS = {
        "pupupasu": "cheveux de sang",
        "gingembre sauvage": "morsure-des-ancetres",
        "morsure-des-ancetres": "gingembre sauvage",
    }
    for e in entities:
        e_lower = e["canonical_name"].lower().strip()
        # Normalize accented chars for matching
        e_normalized = slugify(e["canonical_name"])
        for src, tgt in _KNOWN_FUSIONS.items():
            src_slug = slugify(src)
            tgt_slug = slugify(tgt)
            if e_normalized == src_slug:
                for other in entities:
                    if slugify(other["canonical_name"]) == tgt_slug:
                        union(e["id"], other["id"])

    # Group entities by root
    groups: dict[int, list] = {}
    for e in entities:
        root = find(e["id"])
        groups.setdefault(root, []).append(e)

    # Build fused entity list
    fused: list[dict] = []
    for group in groups.values():
        # Filter noise from the group
        clean = [e for e in group if not is_noise_entity(e["canonical_name"])]
        if not clean:
            continue

        # Pick the primary: highest mention count, then longest name
        primary = max(clean, key=lambda e: (e["mention_count"], len(e["canonical_name"])))

        # Merge stats
        total_mentions = sum(e["mention_count"] for e in clean)
        first_turn_ids = [e["first_seen_turn"] for e in clean if e["first_seen_turn"]]
        last_turn_ids = [e["last_seen_turn"] for e in clean if e["last_seen_turn"]]
        all_histories: list[str] = []
        for e in clean:
            all_histories.extend(_parse_json_list(e["history"]))
        # Deduplicate history entries
        seen_history: set[str] = set()
        unique_history: list[str] = []
        for h in all_histories:
            if h not in seen_history:
                seen_history.add(h)
                unique_history.append(h)

        # Pick longest description
        descriptions = [e["description"] for e in clean if e["description"]]
        best_desc = max(descriptions, key=len) if descriptions else None

        # Collect all names as aliases (excluding the primary name)
        all_names = set()
        for e in clean:
            all_names.add(e["canonical_name"])
            for alias in alias_lookup.get(e["id"], set()):
                all_names.add(alias)
        # Also add display-cased versions
        alias_set = {n for n in all_names if n.lower().strip() != primary["canonical_name"].lower().strip()}

        # Collect all entity IDs in the group (for mention queries)
        all_ids = [e["id"] for e in clean]

        fused.append({
            "id": primary["id"],
            "all_ids": all_ids,
            "canonical_name": primary["canonical_name"],
            "entity_type": primary["entity_type"],
            "description": best_desc,
            "history": unique_history,
            "mention_count": total_mentions,
            "first_seen_turn": min(first_turn_ids) if first_turn_ids else None,
            "last_seen_turn": max(last_turn_ids) if last_turn_ids else None,
            "aliases": sorted(alias_set),
        })

    return fused


def _build_id_to_primary(fused_list: list[dict]) -> dict[int, str]:
    """Build a reverse map: entity_id -> primary canonical_name for all fused groups."""
    mapping: dict[int, str] = {}
    for fe in fused_list:
        for eid in fe["all_ids"]:
            mapping[eid] = fe["canonical_name"]
    return mapping


def generate_entity_page(
    conn: sqlite3.Connection,
    entity: dict,
    civ_name: str,
    civ_slug: str,
    id_to_primary: dict[int, str] | None = None,
) -> str:
    """Generate a full markdown page for a single entity."""
    name = _capitalize_entity(entity["canonical_name"])
    etype_label = _entity_type_label(entity["entity_type"])
    first = _turn_link(entity["first_seen_turn"], conn) if entity["first_seen_turn"] else "-"
    last = _turn_link(entity["last_seen_turn"], conn) if entity["last_seen_turn"] else "-"

    lines = [
        f"# {name}",
        "",
        f"*{etype_label}* -- {civ_name}",
        "",
        "| | |",
        "|---|---|",
        f"| Mentions | **{entity['mention_count']}** |",
        f"| Premiere apparition | {first} |",
        f"| Derniere apparition | {last} |",
    ]

    if entity["aliases"]:
        alias_display = ", ".join(_capitalize_entity(a) for a in entity["aliases"])
        lines.append(f"| Alias | {alias_display} |")

    lines.append("")

    # Description
    if entity["description"]:
        lines.extend(["## Description", "", entity["description"], ""])

    # Per-turn summaries (from LLM profiler) as main chronology
    if entity["history"]:
        lines.extend(["## Chronologie", ""])
        for event in entity["history"]:
            # History entries are now "Tour X: summary..." format
            lines.append(f"**{event}**" if event.startswith("Tour") else f"- {event}")
            lines.append("")

    # Raw source passages (collapsible, for reference)
    all_ids = entity["all_ids"]
    placeholders = ",".join("?" * len(all_ids))
    mentions = conn.execute(
        f"""SELECT m.mention_text, m.context, t.turn_number
            FROM entity_mentions m
            JOIN turn_turns t ON m.turn_id = t.id
            WHERE m.entity_id IN ({placeholders})
            ORDER BY t.turn_number, m.id""",
        all_ids,
    ).fetchall()

    if mentions:
        lines.extend([
            "??? note \"Sources -- Passages originaux\"",
            "",
        ])
        _segment_cache: dict[int, list[str]] = {}
        current_turn = None
        seen_contexts: set[str] = set()
        for m in mentions:
            if m["turn_number"] != current_turn:
                current_turn = m["turn_number"]
                lines.append(f"    **Tour {current_turn}**")
                lines.append("")
            ctx = _find_rich_context(
                conn, m["mention_text"], m["turn_number"],
                m["context"], _segment_cache,
            )
            if ctx:
                ctx_key = ctx[:100]
                if ctx_key in seen_contexts:
                    continue
                seen_contexts.add(ctx_key)
                # Indent for admonition content
                for ctx_line in f"> {ctx}".splitlines():
                    lines.append(f"    {ctx_line}")
                lines.append("")

    # Related entities (co-occurring in same turns)
    turn_ids = conn.execute(
        f"""SELECT DISTINCT m.turn_id
            FROM entity_mentions m
            WHERE m.entity_id IN ({placeholders})""",
        all_ids,
    ).fetchall()

    if turn_ids:
        turn_id_list = [t["turn_id"] for t in turn_ids]
        turn_placeholders = ",".join("?" * len(turn_id_list))
        related = conn.execute(
            f"""SELECT e.id, e.canonical_name, e.entity_type, count(*) as co_count
                FROM entity_mentions m
                JOIN entity_entities e ON m.entity_id = e.id
                WHERE m.turn_id IN ({turn_placeholders})
                  AND m.entity_id NOT IN ({placeholders})
                GROUP BY e.id
                ORDER BY co_count DESC
                LIMIT 20""",
            turn_id_list + all_ids,
        ).fetchall()

        # Resolve through fusion map and aggregate co-occurrence counts
        seen_primary: dict[str, dict] = {}
        for r in related:
            if is_noise_entity(r["canonical_name"]):
                continue
            # Resolve to primary name via fusion map
            primary_name = (id_to_primary or {}).get(r["id"], r["canonical_name"])
            if is_noise_entity(primary_name):
                continue
            if primary_name in seen_primary:
                seen_primary[primary_name]["co_count"] += r["co_count"]
            else:
                seen_primary[primary_name] = {
                    "canonical_name": primary_name,
                    "entity_type": r["entity_type"],
                    "co_count": r["co_count"],
                }

        related_sorted = sorted(seen_primary.values(), key=lambda x: x["co_count"], reverse=True)[:15]
        if related_sorted:
            lines.extend(["## Entites liees", ""])
            for r in related_sorted:
                rname = _capitalize_entity(r["canonical_name"])
                rslug = slugify(r["canonical_name"])
                lines.append(
                    f"- [{rname}]({rslug}.md) "
                    f"({_entity_type_label(r['entity_type'])}, "
                    f"{r['co_count']} co-occurrences)"
                )
            lines.append("")

    return "\n".join(lines)


def generate_civ_entities(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> tuple[str, list[dict]]:
    """Generate clickable entity index for a civilization.

    Returns (index_page_content, list_of_fused_entity_dicts) so the caller
    can write individual entity pages.
    """
    civ_slug = slugify(civ_name)
    fused = _build_fused_entities(conn, civ_id)

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for e in fused:
        by_type.setdefault(e["entity_type"], []).append(e)

    lines = [f"# {civ_name} -- Entites", ""]

    type_order = ["person", "place", "technology", "institution", "civilization",
                  "caste", "resource", "creature", "event"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for etype in sorted_types:
        entities = sorted(by_type[etype], key=lambda e: e["canonical_name"].lower())
        if not entities:
            continue

        lines.extend([f"## {_entity_type_label(etype)}", ""])

        for e in entities:
            name = _capitalize_entity(e["canonical_name"])
            eslug = slugify(e["canonical_name"])
            first = _turn_link(e["first_seen_turn"], conn) if e["first_seen_turn"] else ""
            last = _turn_link(e["last_seen_turn"], conn) if e["last_seen_turn"] else ""

            # Build entry line
            turn_info = ""
            if first and last and first != last:
                turn_info = f", {first} - {last}"
            elif first:
                turn_info = f", {first}"

            alias_info = ""
            if e["aliases"]:
                alias_display = ", ".join(_capitalize_entity(a) for a in e["aliases"][:3])
                alias_info = f" | *alias: {alias_display}*"

            lines.append(
                f"- [**{name}**](entities/{eslug}.md) "
                f"-- {e['mention_count']} mentions{turn_info}{alias_info}"
            )

        lines.append("")

    return "\n".join(lines), fused


def generate_global_timeline(conn: sqlite3.Connection) -> str:
    """Generate global timeline across all civilizations."""
    turns = conn.execute(
        """SELECT t.turn_number, t.summary, t.turn_type, c.name as civ_name
           FROM turn_turns t JOIN civ_civilizations c ON t.civ_id = c.id
           ORDER BY t.turn_number""",
    ).fetchall()

    lines = [
        "# Timeline Globale",
        "",
        "| Tour | Civilisation | Type | Resume |",
        "|---|---|---|---|",
    ]
    for t in turns:
        summary = _clean_summary(t["summary"] or "")[:150]
        civ_slug = slugify(t["civ_name"])
        lines.append(
            f"| {t['turn_number']} | "
            f"[{t['civ_name']}](../civilizations/{civ_slug}/index.md) | "
            f"{t['turn_type']} | "
            f"{summary} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_global_entities(conn: sqlite3.Connection, all_fused: dict[int, list[dict]] | None = None) -> str:
    """Generate global entity index across all civilizations.

    Links each entity to its dedicated page. Uses fused entities if provided.
    """
    # Build a flat list of all fused entities across civs
    global_entities: list[dict] = []
    if all_fused:
        for civ_id, fused_list in all_fused.items():
            civ_row = conn.execute(
                "SELECT name FROM civ_civilizations WHERE id = ?", (civ_id,)
            ).fetchone()
            civ_name = civ_row["name"] if civ_row else "Global"
            civ_slug = slugify(civ_name)
            for e in fused_list:
                global_entities.append({**e, "civ_name": civ_name, "civ_slug": civ_slug})
    else:
        # Fallback: query directly (no fusion)
        rows = conn.execute(
            """SELECT e.id, e.canonical_name, e.entity_type, e.description,
                      c.name as civ_name,
                      (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
               FROM entity_entities e
               LEFT JOIN civ_civilizations c ON e.civ_id = c.id
               ORDER BY e.canonical_name"""
        ).fetchall()
        for e in rows:
            if is_noise_entity(e["canonical_name"]):
                continue
            global_entities.append({
                "canonical_name": e["canonical_name"],
                "entity_type": e["entity_type"],
                "mention_count": e["mention_count"],
                "description": e["description"],
                "civ_name": e["civ_name"] or "Global",
                "civ_slug": slugify(e["civ_name"]) if e["civ_name"] else "",
                "aliases": [],
            })

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for e in global_entities:
        by_type.setdefault(e["entity_type"], []).append(e)

    lines = ["# Index des Entites", ""]

    type_order = ["person", "place", "technology", "institution", "civilization",
                  "caste", "resource", "creature", "event"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for etype in sorted_types:
        entities = sorted(by_type[etype], key=lambda e: e["canonical_name"].lower())
        if not entities:
            continue

        lines.extend([f"## {_entity_type_label(etype)}", ""])

        for e in entities:
            name = _capitalize_entity(e["canonical_name"])
            civ = e["civ_name"]
            civ_slug = e["civ_slug"]
            eslug = slugify(e["canonical_name"])

            # Build turn range
            first = _turn_link(e.get("first_seen_turn"), conn) if e.get("first_seen_turn") else ""
            last = _turn_link(e.get("last_seen_turn"), conn) if e.get("last_seen_turn") else ""
            turn_info = ""
            if first and last and first != last:
                turn_info = f", {first} - {last}"
            elif first:
                turn_info = f", {first}"

            alias_str = ""
            if e.get("aliases"):
                alias_names = ", ".join(_capitalize_entity(a) for a in e["aliases"][:3])
                alias_str = f" | *alias: {alias_names}*"

            if civ_slug:
                link = f"../civilizations/{civ_slug}/entities/{eslug}.md"
                lines.append(
                    f"- [**{name}**]({link}) -- {civ}, {e['mention_count']} mentions{turn_info}{alias_str}"
                )
            else:
                lines.append(
                    f"- **{name}** -- {civ}, {e['mention_count']} mentions{turn_info}{alias_str}"
                )

            lines.append("")

    return "\n".join(lines)


def generate_pipeline_stats(conn: sqlite3.Connection) -> str:
    """Generate pipeline run statistics page."""
    runs = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC"
    ).fetchall()

    msg_count = conn.execute("SELECT count(*) FROM turn_raw_messages").fetchone()[0]
    turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
    mention_count = conn.execute("SELECT count(*) FROM entity_mentions").fetchone()[0]
    seg_count = conn.execute("SELECT count(*) FROM turn_segments").fetchone()[0]

    lines = [
        "# Pipeline ML",
        "",
        "## Etat de la base de donnees",
        "",
        "| Metrique | Valeur |",
        "|---|---|",
        f"| Messages bruts | {msg_count} |",
        f"| Tours de jeu | {turn_count} |",
        f"| Segments | {seg_count} |",
        f"| Entites uniques | {entity_count} |",
        f"| Mentions d'entites | {mention_count} |",
        "",
        "## Historique des runs",
        "",
        "| Run | Statut | Debut | Fin | Messages | Tours | Entites |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        status_icon = {"completed": "OK", "failed": "FAIL", "running": "..."}.get(r["status"], r["status"])
        lines.append(
            f"| {r['id']} | {status_icon} | "
            f"{r['started_at'] or '-'} | "
            f"{r['completed_at'] or '-'} | "
            f"{r['messages_processed'] or 0} | "
            f"{r['turns_created'] or 0} | "
            f"{r['entities_extracted'] or 0} |"
        )
    lines.append("")
    return "\n".join(lines)


# -- Helpers -------------------------------------------------------------------

def _entity_type_label(etype: str) -> str:
    """French label for entity types."""
    labels = {
        "person": "Personnages",
        "place": "Lieux",
        "technology": "Technologies",
        "institution": "Institutions",
        "civilization": "Civilisations",
        "caste": "Castes",
        "resource": "Ressources",
        "creature": "Creatures",
        "event": "Evenements",
    }
    return labels.get(etype, etype.capitalize())


def _clean_summary(summary: str) -> str:
    """Clean up a summary for display -- remove YouTube artifacts and markdown noise."""
    lines = summary.strip().splitlines()
    cleaned = []
    skip_youtube = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("https://") or stripped.startswith("http://"):
            skip_youtube = True
            continue
        if skip_youtube and (not stripped or stripped in ("YouTube",)):
            continue
        if skip_youtube:
            skip_youtube = False
            if len(stripped) < 60 and not stripped.endswith("."):
                continue
        cleaned.append(line)
    result = " ".join(l.strip() for l in cleaned if l.strip())
    result = re.sub(r"^\*\*[^*]+\*\*\s*", "", result)
    return result.strip()


# Patterns for segment content cleaning
_RE_YOUTUBE_URL = re.compile(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+")
_RE_YOUTUBE_META = re.compile(
    r"^\d+\s+.*(?:OST|Soundtrack|Remix|Topic|YouTube).*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_MODIFIE = re.compile(r"\s*\(modifi[eé]\)")
_RE_TIMESTAMP_LINE = re.compile(r"^\s*\[\s*\d{2}:\d{2}\s*\]\s*$", re.MULTILINE)
_RE_TIMESTAMP_INLINE = re.compile(r"\[\s*\d{2}:\d{2}\s*\]\s*")


def _clean_segment_content(content: str) -> str:
    """Clean segment content for wiki display.

    Removes YouTube URLs/metadata, (modifie) markers, timestamps, and duplicate paragraphs.
    """
    text = _RE_YOUTUBE_URL.sub("", content)
    text = _RE_YOUTUBE_META.sub("", text)
    text = _RE_MODIFIE.sub("", text)
    text = _RE_TIMESTAMP_LINE.sub("", text)
    text = _RE_TIMESTAMP_INLINE.sub("", text)

    # Deduplicate paragraphs
    paragraphs = text.split("\n\n")
    seen: set[str] = set()
    unique = []
    for para in paragraphs:
        normalized = para.strip()
        if not normalized:
            continue
        key = re.sub(r"\s+", " ", normalized).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    text = "\n\n".join(unique)

    # Clean residual noise lines
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in (",", "", "YouTube", "youtube"):
            continue
        if len(stripped) < 3 and not stripped.endswith("."):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _parse_json_list(json_str: str | None) -> list[str]:
    """Safely parse a JSON string expected to be a list of strings."""
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return [str(item) for item in data if item]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _capitalize_entity(name: str) -> str:
    """Capitalize first letter of entity name for display."""
    if not name:
        return name
    return name[0].upper() + name[1:]


def _clean_author_name(name: str) -> str:
    """Normalize author names -- strip trailing ) from parsing artifacts."""
    return name.rstrip(")")


def _detect_gm_authors(conn: sqlite3.Connection) -> set[str]:
    """Detect GM authors by message frequency -- GM posts the most."""
    rows = conn.execute(
        "SELECT author_name, count(*) as c FROM turn_raw_messages GROUP BY author_name ORDER BY c DESC"
    ).fetchall()
    if not rows:
        return set()
    # The most frequent author is the GM; also include variants with trailing )
    gm_name = _clean_author_name(rows[0]["author_name"])
    return {r["author_name"] for r in rows if _clean_author_name(r["author_name"]) == gm_name}


def _group_messages_by_author(
    conn: sqlite3.Connection,
    raw_ids: list[str],
    gm_authors: set[str],
) -> list[dict]:
    """Group consecutive raw messages by author role (GM vs player).

    Returns list of dicts: {author, is_gm, content}
    """
    groups: list[dict] = []
    for msg_id in raw_ids:
        row = conn.execute(
            "SELECT author_name, content FROM turn_raw_messages WHERE id = ?",
            (int(msg_id),),
        ).fetchone()
        if not row:
            continue

        author = _clean_author_name(row["author_name"])
        is_gm = row["author_name"] in gm_authors

        # Merge with previous group if same role
        if groups and groups[-1]["is_gm"] == is_gm:
            groups[-1]["content"] += "\n\n" + row["content"]
        else:
            groups.append({
                "author": author,
                "is_gm": is_gm,
                "content": row["content"],
            })

    return groups


def _find_rich_context(
    conn: sqlite3.Connection,
    mention_text: str,
    turn_number: int,
    fallback_context: str | None,
    cache: dict[int, list[str]],
    window: int = 800,
) -> str:
    """Find a rich context excerpt for a mention by searching turn segments.

    Looks for mention_text in the turn's segments and returns a window of text
    around it. Falls back to the stored context field if no segment match.
    """
    if turn_number not in cache:
        segments = conn.execute(
            """SELECT s.content FROM turn_segments s
               JOIN turn_turns t ON s.turn_id = t.id
               WHERE t.turn_number = ?
               ORDER BY s.segment_order""",
            (turn_number,),
        ).fetchall()
        cache[turn_number] = [s["content"] for s in segments]

    # Search for mention in segments (case-insensitive)
    mention_lower = mention_text.lower()
    for seg_content in cache[turn_number]:
        pos = seg_content.lower().find(mention_lower)
        if pos != -1:
            # Extract window around the mention
            half = window // 2
            start = max(0, pos - half)
            end = min(len(seg_content), pos + len(mention_text) + half)
            excerpt = seg_content[start:end].strip()
            excerpt = _clean_segment_content(excerpt)
            if not excerpt:
                continue
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(seg_content) else ""
            return f"{prefix}{excerpt}{suffix}"

    # Fallback to stored context
    if fallback_context:
        ctx = _clean_segment_content(fallback_context.strip())
        if ctx:
            return f"...{ctx}..."
    return ""


def _turn_link(turn_id: int | None, conn: sqlite3.Connection) -> str:
    """Create a turn reference string."""
    if not turn_id:
        return "-"
    row = conn.execute(
        "SELECT turn_number FROM turn_turns WHERE id = ?", (turn_id,)
    ).fetchone()
    return f"Tour {row['turn_number']}" if row else "-"


# -- Main generation -----------------------------------------------------------

def generate_wiki(
    db_path: str,
    output_dir: str,
    progress_callback=None,
    run_id: int | None = None,
) -> dict:
    """Generate all wiki pages from the database. Returns stats.

    Args:
        db_path: Path to SQLite database
        output_dir: Output directory for markdown files
        progress_callback: Optional callback(current, total, unit_type) for progress tracking
        run_id: Optional pipeline run ID for DB progress tracking
    """
    out = Path(output_dir)
    conn = get_connection(db_path)
    stats = {"pages_generated": 0, "entity_pages": 0}

    # Estimate total pages for progress tracking
    civ_count = conn.execute("SELECT count(*) FROM civ_civilizations").fetchone()[0]
    # Rough estimate: 5 base pages + 3 per civ + entity pages
    # We'll refine as we go
    estimated_base_pages = 5 + (3 * civ_count)
    total_pages = estimated_base_pages  # Will be updated with actual entity count
    current_page = 0

    try:
        _write_page(out / "index.md", generate_index(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "civilizations" / "index.md", generate_civilizations_index(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        # Collect fused entities per civ for global index
        all_fused: dict[int, list[dict]] = {}

        civs = conn.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()

        # Update total_pages estimate with actual entity count
        entity_count = conn.execute("SELECT count(*) FROM entity_entities WHERE is_active = 1").fetchone()[0]
        total_pages = estimated_base_pages + entity_count

        for civ in civs:
            civ_slug = slugify(civ["name"])
            civ_dir = out / "civilizations" / civ_slug

            _write_page(civ_dir / "index.md",
                        generate_civ_index(conn, civ["id"], civ["name"], civ["player_name"]))
            stats["pages_generated"] += 1
            current_page += 1
            if progress_callback:
                progress_callback(current_page, total_pages, "page")

            _write_page(civ_dir / "turns.md",
                        generate_civ_turns(conn, civ["id"], civ["name"]))
            stats["pages_generated"] += 1
            current_page += 1
            if progress_callback:
                progress_callback(current_page, total_pages, "page")

            # generate_civ_entities now returns (page_content, fused_list)
            entities_content, fused_list = generate_civ_entities(conn, civ["id"], civ["name"])
            _write_page(civ_dir / "entities.md", entities_content)
            all_fused[civ["id"]] = fused_list
            stats["pages_generated"] += 1
            current_page += 1
            if progress_callback:
                progress_callback(current_page, total_pages, "page")

            # Write individual entity pages
            entity_dir = civ_dir / "entities"
            id_to_primary = _build_id_to_primary(fused_list)
            for entity in fused_list:
                eslug = slugify(entity["canonical_name"])
                page_content = generate_entity_page(
                    conn, entity, civ["name"], civ_slug, id_to_primary
                )
                _write_page(entity_dir / f"{eslug}.md", page_content)
                stats["entity_pages"] += 1
                current_page += 1
                if progress_callback:
                    progress_callback(current_page, total_pages, "page")

        _write_page(out / "global" / "timeline.md", generate_global_timeline(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "global" / "entities.md", generate_global_entities(conn, all_fused))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "meta" / "pipeline.md", generate_pipeline_stats(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        nav = _build_nav(civs)
        stats["nav_entries"] = nav

    finally:
        conn.close()

    return stats


def _write_page(path: Path, content: str) -> None:
    """Write a markdown page, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_nav(civs: list) -> list:
    """Build the nav structure for mkdocs.yml."""
    civ_nav = []
    for civ in civs:
        slug = slugify(civ["name"])
        civ_nav.append({
            civ["name"]: [
                {"Apercu": f"civilizations/{slug}/index.md"},
                {"Tours": f"civilizations/{slug}/turns.md"},
                {"Entites": f"civilizations/{slug}/entities.md"},
            ]
        })

    return [
        {"Accueil": "index.md"},
        {"Civilisations": [
            {"Index": "civilizations/index.md"},
            *civ_nav,
        ]},
        {"Global": [
            {"Timeline": "global/timeline.md"},
            {"Entites": "global/entities.md"},
        ]},
        {"Meta": [
            {"Pipeline": "meta/pipeline.md"},
        ]},
    ]


def update_mkdocs_yml(wiki_dir: str, nav: list) -> None:
    """Update the mkdocs.yml nav section."""
    import yaml

    yml_path = Path(wiki_dir) / "mkdocs.yml"
    if not yml_path.exists():
        return

    with open(yml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["nav"] = nav

    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Aurelm wiki from database")
    parser.add_argument("--db", required=True, help="Path to the SQLite database")
    parser.add_argument("--out", default="docs", help="Output directory for markdown files")
    parser.add_argument("--wiki-dir", default=None, help="Wiki root dir (for mkdocs.yml update)")
    args = parser.parse_args()

    print(f"Generating wiki from {args.db} -> {args.out}")
    stats = generate_wiki(args.db, args.out)
    print(f"Generated {stats['pages_generated']} pages + {stats.get('entity_pages', 0)} entity pages")

    if args.wiki_dir and stats.get("nav_entries"):
        try:
            update_mkdocs_yml(args.wiki_dir, stats["nav_entries"])
            print("Updated mkdocs.yml nav")
        except ImportError:
            print("PyYAML not available -- skipping mkdocs.yml update")


if __name__ == "__main__":
    main()
