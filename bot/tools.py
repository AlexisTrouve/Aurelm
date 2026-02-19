"""Python port of the 9 MCP tools from mcp-server/src/tools/*.ts.

All functions take a sqlite3 connection and return a Markdown string.
"""

from __future__ import annotations

import json
import re
import sqlite3

# --------------------------------------------------------------------------- #
# Helpers (ported from mcp-server/src/helpers.ts)
# --------------------------------------------------------------------------- #

FRENCH_STOPWORDS = {
    "le", "la", "les", "de", "du", "des", "un", "une",
    "et", "ou", "en", "au", "aux", "ce", "ces", "son", "sa", "ses",
    "mon", "ma", "mes", "ton", "ta", "tes", "leur", "leurs",
    "qui", "que", "quoi", "dont", "il", "elle", "ils", "elles",
    "je", "tu", "nous", "vous", "on", "se", "ne", "pas", "plus",
    "est", "sont", "a", "ont", "fait", "ete", "avec", "pour",
    "dans", "par", "sur", "sous", "entre", "vers", "chez",
    "mais", "donc", "car", "ni", "si", "peut", "bien", "tout",
    "cette", "cet", "aussi", "comme", "sans", "tres", "peu",
    "encore", "deja", "toujours", "jamais", "ici", "y",
    "avoir", "etre", "faire", "dire", "pouvoir", "vouloir",
    "meme", "autre", "autres", "chaque", "quelques",
}


def truncate(text: str | None, max_len: int = 200) -> str:
    if not text:
        return "(none)"
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def resolve_civ_name(
    conn: sqlite3.Connection, civ_name: str
) -> dict:
    """Fuzzy-match a civilization name. Returns {'civ': {...}} or {'error': '...'}."""
    row = conn.execute(
        "SELECT id, name, player_name FROM civ_civilizations WHERE name = ?",
        (civ_name,),
    ).fetchone()
    if row:
        return {"civ": {"id": row[0], "name": row[1], "player_name": row[2]}}

    rows = conn.execute(
        "SELECT id, name, player_name FROM civ_civilizations WHERE name LIKE ?",
        (f"%{civ_name}%",),
    ).fetchall()
    if len(rows) == 1:
        return {"civ": {"id": rows[0][0], "name": rows[0][1], "player_name": rows[0][2]}}
    if len(rows) > 1:
        matches = ", ".join(r[1] for r in rows)
        return {"error": f'Ambiguous civilization name "{civ_name}". Multiple matches: {matches}. Please be more specific.'}

    all_civs = conn.execute("SELECT name FROM civ_civilizations ORDER BY name").fetchall()
    civ_list = ", ".join(r[0] for r in all_civs) or "none"
    return {"error": f'Civilization "{civ_name}" not found. Available civilizations: {civ_list}'}


def _parse_history(history_json: str | None) -> list[str]:
    if not history_json:
        return []
    try:
        parsed = json.loads(history_json)
        if isinstance(parsed, list):
            return [str(e) for e in parsed if e]  # filter None/empty like _parse_json_list
    except (json.JSONDecodeError, TypeError):
        pass
    return []


# --------------------------------------------------------------------------- #
# Tool 1: listCivs
# --------------------------------------------------------------------------- #

def list_civs(conn: sqlite3.Connection) -> str:
    rows = conn.execute("""
        SELECT c.name, c.player_name,
               (SELECT COUNT(*) FROM turn_turns t WHERE t.civ_id = c.id) AS turn_count,
               (SELECT COUNT(*) FROM entity_entities e WHERE e.civ_id = c.id) AS entity_count
        FROM civ_civilizations c
        ORDER BY c.name
    """).fetchall()

    if not rows:
        return "# Civilizations\n\nNo civilizations registered yet."

    lines = ["# Civilizations", "", "| Name | Player | Turns | Entities |", "|---|---|---|---|"]
    for r in rows:
        name, player, turns, entities = r
        lines.append(f"| {name} | {player or '-'} | {turns} | {entities} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 2: getCivState
# --------------------------------------------------------------------------- #

def get_civ_state(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> str:
    turn_count = conn.execute(
        "SELECT COUNT(*) FROM turn_turns WHERE civ_id = ?", (civ_id,)
    ).fetchone()[0]

    entity_count = conn.execute(
        "SELECT COUNT(*) FROM entity_entities WHERE civ_id = ?", (civ_id,)
    ).fetchone()[0]

    breakdown = conn.execute(
        "SELECT entity_type, COUNT(*) AS count FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY count DESC",
        (civ_id,),
    ).fetchall()

    recent = conn.execute(
        "SELECT turn_number, title, summary, turn_type, game_date_start FROM turn_turns WHERE civ_id = ? ORDER BY turn_number DESC LIMIT 5",
        (civ_id,),
    ).fetchall()

    top_entities = conn.execute("""
        SELECT e.canonical_name, e.entity_type,
               (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
        FROM entity_entities e
        WHERE e.civ_id = ?
        ORDER BY mention_count DESC
        LIMIT 10
    """, (civ_id,)).fetchall()

    lines = [f"# {civ_name}", "", f"**Turns:** {turn_count}", f"**Entities:** {entity_count}", ""]

    if breakdown:
        lines += ["## Entity Breakdown", "", "| Type | Count |", "|---|---|"]
        for row in breakdown:
            lines.append(f"| {row[0]} | {row[1]} |")
        lines.append("")

    if recent:
        lines += ["## Recent Turns", ""]
        for r in recent:
            turn_num, title, summary, turn_type, gd = r
            label = f"Turn {turn_num}"
            if turn_type != "standard":
                label += f" ({turn_type})"
            lines.append(f"- **{label}**: {truncate(summary or title or '(no summary)', 300)}")
        lines.append("")

    if top_entities:
        lines += ["## Top Entities", "", "| Entity | Type | Mentions |", "|---|---|---|"]
        for e in top_entities:
            lines.append(f"| {e[0]} | {e[1]} | {e[2]} |")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 3: getTurnDetail
# --------------------------------------------------------------------------- #

def get_turn_detail(
    conn: sqlite3.Connection, turn_number: int, civ_id: int, civ_name: str
) -> str:
    turn = conn.execute("""
        SELECT t.id, t.turn_number, t.title, t.summary, t.turn_type,
               t.game_date_start, t.game_date_end, c.name AS civ_name
        FROM turn_turns t
        JOIN civ_civilizations c ON t.civ_id = c.id
        WHERE t.turn_number = ? AND t.civ_id = ?
    """, (turn_number, civ_id)).fetchone()

    if not turn:
        turns = conn.execute(
            "SELECT turn_number FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
            (civ_id,),
        ).fetchall()
        available = ", ".join(str(t[0]) for t in turns) or "none"
        return f"# Turn {turn_number} - {civ_name}\n\nTurn not found. Available turns: {available}"

    t_id, t_num, title, summary, turn_type, gd_start, gd_end, cn = turn
    lines = [f"# Turn {t_num}: {title or '(untitled)'} - {cn}", ""]

    if turn_type != "standard":
        lines.append(f"**Type:** {turn_type}")
    if gd_start:
        date_str = gd_start + (f" -- {gd_end}" if gd_end else "")
        lines.append(f"**Game date:** {date_str}")
    if summary:
        lines.append(f"**Summary:** {summary}")
    lines.append("")

    # Segments
    segments = conn.execute(
        "SELECT segment_order, segment_type, content FROM turn_segments WHERE turn_id = ? ORDER BY segment_order",
        (t_id,),
    ).fetchall()

    if segments:
        lines += ["## Segments", ""]
        for s in segments:
            lines.append(f"### [{s[1]}] (segment {s[0]})")
            lines.append(truncate(s[2], 1000))
            lines.append("")

    # Entities mentioned
    entities = conn.execute("""
        SELECT e.canonical_name, e.entity_type, COUNT(*) AS mention_count
        FROM entity_mentions m
        JOIN entity_entities e ON m.entity_id = e.id
        WHERE m.turn_id = ?
        GROUP BY e.id
        ORDER BY mention_count DESC
    """, (t_id,)).fetchall()

    if entities:
        lines += ["## Entities Mentioned", "", "| Entity | Type | Mentions |", "|---|---|---|"]
        for e in entities:
            lines.append(f"| {e[0]} | {e[1]} | {e[2]} |")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 4: searchLore
# --------------------------------------------------------------------------- #

def search_lore(
    conn: sqlite3.Connection,
    query: str,
    civ_id: int | None = None,
    entity_type: str | None = None,
) -> str:
    sql = """
        SELECT DISTINCT e.id, e.canonical_name, e.entity_type, e.description, e.history,
               c.name AS civ_name,
               (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON e.civ_id = c.id
        LEFT JOIN entity_aliases a ON a.entity_id = e.id
        WHERE (e.canonical_name LIKE ? OR e.description LIKE ? OR a.alias LIKE ? OR e.history LIKE ?)
    """
    pattern = f"%{query}%"
    params: list = [pattern, pattern, pattern, pattern]

    if civ_id is not None:
        sql += " AND e.civ_id = ?"
        params.append(civ_id)
    if entity_type:
        sql += " AND e.entity_type = ?"
        params.append(entity_type)

    sql += " ORDER BY mention_count DESC LIMIT 20"
    entities = conn.execute(sql, params).fetchall()

    if not entities:
        return f'# Lore Search: "{query}"\n\nNo entities found matching "{query}".'

    lines = [f'# Lore Search: "{query}"', "", f"**{len(entities)}** result(s) found.", ""]

    for e in entities:
        eid, name, etype, desc, history, cn, mc = e
        lines.append(f"## {name} ({etype})")
        if cn:
            lines.append(f"**Civilization:** {cn}")
        lines.append(f"**Mentions:** {mc}")
        if desc:
            lines.append(f"**Description:** {desc}")

        events = _parse_history(history)
        if events:
            lines += ["", "**Chronologie:**"]
            for ev in events:
                lines.append(f"- {ev}")

        aliases = conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (eid,)
        ).fetchall()
        if aliases:
            lines.append(f"**Aliases:** {', '.join(a[0] for a in aliases)}")

        mentions = conn.execute("""
            SELECT m.mention_text, m.context, t.turn_number
            FROM entity_mentions m
            JOIN turn_turns t ON m.turn_id = t.id
            WHERE m.entity_id = ?
            ORDER BY t.turn_number DESC
            LIMIT 3
        """, (eid,)).fetchall()

        if mentions:
            lines += ["", "**Recent mentions:**"]
            for m in mentions:
                ctx = truncate(m[1], 150) if m[1] else m[0]
                lines.append(f"- Turn {m[2]}: {ctx}")

        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 5: getEntityDetail
# --------------------------------------------------------------------------- #

def get_entity_detail(
    conn: sqlite3.Connection, entity_name: str, civ_id: int | None = None
) -> str:
    sql = """
        SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
               c.name AS civ_name, e.is_active,
               ft.turn_number AS first_turn, lt.turn_number AS last_turn
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON e.civ_id = c.id
        LEFT JOIN turn_turns ft ON e.first_seen_turn = ft.id
        LEFT JOIN turn_turns lt ON e.last_seen_turn = lt.id
        WHERE (e.canonical_name LIKE ? OR e.id IN (
          SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ?
        ))
    """
    pattern = f"%{entity_name}%"
    params: list = [pattern, pattern]

    if civ_id is not None:
        sql += " AND e.civ_id = ?"
        params.append(civ_id)

    sql += " ORDER BY e.canonical_name LIMIT 5"
    entities = conn.execute(sql, params).fetchall()

    if not entities:
        return f'# Entity Detail: "{entity_name}"\n\nNo entity found matching "{entity_name}".'

    lines: list[str] = []
    for e in entities:
        eid, name, etype, desc, history, cn, active, ft, lt = e
        lines.append(f"# {name} ({etype})")
        lines.append("")
        if cn:
            lines.append(f"**Civilization:** {cn}")
        lines.append(f"**Status:** {'active' if active else 'inactive'}")
        if ft is not None:
            lines.append(f"**First seen:** Turn {ft}")
        if lt is not None:
            lines.append(f"**Last seen:** Turn {lt}")
        if desc:
            lines.append(f"**Description:** {desc}")

        events = _parse_history(history)
        if events:
            lines += ["", "## Chronologie", ""]
            for ev in events:
                lines.append(f"- {ev}")

        aliases = conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (eid,)
        ).fetchall()
        if aliases:
            lines.append(f"**Aliases:** {', '.join(a[0] for a in aliases)}")

        # Relations (both directions)
        relations = conn.execute("""
            SELECT 'outgoing' AS direction, t.canonical_name AS other_name, t.entity_type AS other_type,
                   r.relation_type, r.description, tt.turn_number
            FROM entity_relations r
            JOIN entity_entities t ON r.target_entity_id = t.id
            LEFT JOIN turn_turns tt ON r.turn_id = tt.id
            WHERE r.source_entity_id = ? AND r.is_active = 1
            UNION ALL
            SELECT 'incoming' AS direction, s.canonical_name AS other_name, s.entity_type AS other_type,
                   r.relation_type, r.description, tt.turn_number
            FROM entity_relations r
            JOIN entity_entities s ON r.source_entity_id = s.id
            LEFT JOIN turn_turns tt ON r.turn_id = tt.id
            WHERE r.target_entity_id = ? AND r.is_active = 1
        """, (eid, eid)).fetchall()

        if relations:
            lines += ["", "## Relations", "", "| Direction | Entity | Type | Relation | Turn |", "|---|---|---|---|---|"]
            for rel in relations:
                direction, other_name, other_type, rel_type, _desc, turn_num = rel
                arrow = "->" if direction == "outgoing" else "<-"
                turn_str = str(turn_num) if turn_num is not None else "-"
                lines.append(f"| {arrow} | {other_name} | {other_type} | {rel_type} | {turn_str} |")

        # Mentions (up to 20)
        mentions = conn.execute("""
            SELECT m.mention_text, m.context, t.turn_number, s.segment_type
            FROM entity_mentions m
            JOIN turn_turns t ON m.turn_id = t.id
            LEFT JOIN turn_segments s ON m.segment_id = s.id
            WHERE m.entity_id = ?
            ORDER BY t.turn_number DESC
            LIMIT 20
        """, (eid,)).fetchall()

        if mentions:
            lines += ["", "## Mentions", ""]
            for m in mentions:
                seg_type = f" [{m[3]}]" if m[3] else ""
                ctx = truncate(m[1], 200) if m[1] else m[0]
                lines.append(f"- **Turn {m[2]}**{seg_type}: {ctx}")

        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 6: sanityCheck
# --------------------------------------------------------------------------- #

def _extract_search_terms(statement: str) -> list[str]:
    """Extract candidate search terms: unigrams + bigrams + trigrams, minus stopwords."""
    normalized = re.sub(r"[^a-z\u00e0-\u00ff\s'-]", "", statement.lower()).strip()
    words = [w for w in normalized.split() if len(w) > 2 and w not in FRENCH_STOPWORDS]

    terms: set[str] = set()
    for w in words:
        terms.add(w)
    for i in range(len(words) - 1):
        terms.add(f"{words[i]} {words[i + 1]}")
    for i in range(len(words) - 2):
        terms.add(f"{words[i]} {words[i + 1]} {words[i + 2]}")
    return list(terms)


def sanity_check(
    conn: sqlite3.Connection,
    statement: str,
    civ_id: int | None = None,
    civ_name: str | None = None,
) -> str:
    search_terms = _extract_search_terms(statement)

    matched_ids: set[int] = set()
    for term in search_terms:
        pattern = f"%{term}%"

        if civ_id is not None:
            by_name = conn.execute(
                "SELECT e.id FROM entity_entities e WHERE e.canonical_name LIKE ? AND e.civ_id = ?",
                (pattern, civ_id),
            ).fetchall()
            by_alias = conn.execute(
                "SELECT a.entity_id AS id FROM entity_aliases a JOIN entity_entities e ON a.entity_id = e.id WHERE a.alias LIKE ? AND e.civ_id = ?",
                (pattern, civ_id),
            ).fetchall()
        else:
            by_name = conn.execute(
                "SELECT e.id FROM entity_entities e WHERE e.canonical_name LIKE ?",
                (pattern,),
            ).fetchall()
            by_alias = conn.execute(
                "SELECT a.entity_id AS id FROM entity_aliases a WHERE a.alias LIKE ?",
                (pattern,),
            ).fetchall()

        for r in by_name:
            matched_ids.add(r[0])
        for r in by_alias:
            matched_ids.add(r[0])

    # Fetch details per matched entity
    matched_entities = []
    for entity_id in matched_ids:
        entity = conn.execute("""
            SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
                   c.name AS civ_name
            FROM entity_entities e
            LEFT JOIN civ_civilizations c ON e.civ_id = c.id
            WHERE e.id = ?
        """, (entity_id,)).fetchone()
        if not entity:
            continue

        aliases = [r[0] for r in conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (entity_id,)
        ).fetchall()]

        mention_count = conn.execute(
            "SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?", (entity_id,)
        ).fetchone()[0]

        recent = conn.execute("""
            SELECT t.turn_number, m.context
            FROM entity_mentions m
            JOIN turn_turns t ON m.turn_id = t.id
            WHERE m.entity_id = ?
            ORDER BY t.turn_number DESC
            LIMIT 5
        """, (entity_id,)).fetchall()

        matched_entities.append({
            "name": entity[1],
            "type": entity[2],
            "description": entity[3],
            "history": _parse_history(entity[4]),
            "civ_name": entity[5],
            "aliases": aliases,
            "mention_count": mention_count,
            "recent_mentions": [(r[0], r[1] or "(no context)") for r in recent],
        })

    # Entity inventory
    inventory_lines: list[str] = []
    if civ_id is not None:
        inventory = conn.execute(
            "SELECT canonical_name, entity_type FROM entity_entities WHERE civ_id = ? ORDER BY entity_type, canonical_name LIMIT 200",
            (civ_id,),
        ).fetchall()
        if inventory:
            grouped: dict[str, list[str]] = {}
            for row in inventory:
                grouped.setdefault(row[1], []).append(row[0])
            header = "## Entity Inventory" + (f" - {civ_name}" if civ_name else "")
            inventory_lines.append(header)
            inventory_lines.append("")
            for etype, names in grouped.items():
                inventory_lines.append(f"**{etype}** ({len(names)}): {', '.join(names)}")

    # Recent turns
    recent_turns_lines: list[str] = []
    if civ_id is not None:
        recent_turns = conn.execute("""
            SELECT t.turn_number, t.title, t.summary, c.name AS civ_name
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            WHERE t.civ_id = ?
            ORDER BY t.turn_number DESC
            LIMIT 5
        """, (civ_id,)).fetchall()
    else:
        recent_turns = conn.execute("""
            SELECT t.turn_number, t.title, t.summary, c.name AS civ_name
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            ORDER BY t.turn_number DESC
            LIMIT 5
        """).fetchall()

    if recent_turns:
        recent_turns_lines += ["## Recent Turns (temporal context)", ""]
        for t in recent_turns:
            recent_turns_lines.append(
                f"- **Turn {t[0]}** ({t[3]}): {truncate(t[2] or t[1] or '(no summary)', 200)}"
            )

    # Build output
    lines = [
        "# Sanity Check",
        "",
        f'**Statement:** "{statement}"',
        f"**Context:** {civ_name or 'global'}",
        f"**Search terms extracted:** {', '.join(search_terms)}",
        "",
    ]

    if not matched_entities:
        lines += [
            "## Matched Entities: NONE",
            "",
            "No entities in the database match the terms in this statement. "
            "This could mean the statement introduces new lore, or uses terms not yet tracked.",
        ]
    else:
        lines.append(f"## Matched Entities ({len(matched_entities)})")
        lines.append("")
        for e in matched_entities:
            lines.append(f"### {e['name']} ({e['type']})")
            if e["civ_name"]:
                lines.append(f"**Civilization:** {e['civ_name']}")
            if e["description"]:
                lines.append(f"**Description:** {e['description']}")
            if e["aliases"]:
                lines.append(f"**Aliases:** {', '.join(e['aliases'])}")
            lines.append(f"**Mentions:** {e['mention_count']}")

            if e["history"]:
                lines += ["", "**Established history:**"]
                for ev in e["history"]:
                    lines.append(f"- {ev}")

            if e["recent_mentions"]:
                lines += ["", "**Recent references:**"]
                for turn_num, ctx in e["recent_mentions"]:
                    lines.append(f"- Turn {turn_num}: {truncate(ctx, 200)}")
            lines.append("")

    lines.append("")
    if inventory_lines:
        lines += inventory_lines + [""]
    if recent_turns_lines:
        lines += recent_turns_lines + [""]

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 7: timeline
# --------------------------------------------------------------------------- #

def timeline(
    conn: sqlite3.Connection,
    civ_id: int | None = None,
    limit: int = 50,
) -> str:
    if civ_id is not None:
        rows = conn.execute("""
            SELECT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, t.game_date_end, c.name AS civ_name,
                   (SELECT COUNT(DISTINCT m.entity_id) FROM entity_mentions m WHERE m.turn_id = t.id) AS entity_count
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            WHERE t.civ_id = ?
            ORDER BY t.turn_number ASC, c.name LIMIT ?
        """, (civ_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, t.game_date_end, c.name AS civ_name,
                   (SELECT COUNT(DISTINCT m.entity_id) FROM entity_mentions m WHERE m.turn_id = t.id) AS entity_count
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            ORDER BY t.turn_number ASC, c.name LIMIT ?
        """, (limit,)).fetchall()

    if not rows:
        return "# Timeline\n\nNo turns found."

    lines = [
        "# Timeline",
        "",
        "| Turn | Civilization | Type | Summary | Entities |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        turn_num, title, summary, turn_type, gd_start, _gd_end, cn, ec = r
        text = truncate(summary or title or "(no summary)", 80)
        lines.append(f"| {turn_num} | {cn} | {turn_type} | {text} | {ec} |")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 8: compareCivs
# --------------------------------------------------------------------------- #

ASPECT_ENTITY_MAP: dict[str, dict[str, list[str]]] = {
    "military": {
        "types": ["person", "creature", "institution"],
        "keywords": ["guerre", "militaire", "armee", "soldat", "combat", "arme", "defense", "attaque", "bataille", "guerrier"],
    },
    "technology": {
        "types": ["technology", "resource"],
        "keywords": ["technologie", "technique", "decouverte", "invention", "outil", "savoir", "connaissance", "forge"],
    },
    "politics": {
        "types": ["institution", "person"],
        "keywords": ["politique", "gouvernement", "loi", "chef", "roi", "conseil", "caste", "pouvoir", "alliance", "diplomatie"],
    },
    "economy": {
        "types": ["resource", "technology", "place"],
        "keywords": ["economie", "commerce", "ressource", "echange", "marche", "production", "agriculture", "recolte"],
    },
    "culture": {
        "types": ["institution", "event", "place"],
        "keywords": ["culture", "religion", "rituel", "tradition", "art", "musique", "fete", "ceremonie", "croyance", "mythe"],
    },
}


def compare_civs(
    conn: sqlite3.Connection,
    civs: list[dict],
    aspects: list[str] | None = None,
) -> str:
    active_aspects = [a for a in (aspects or []) if a in ASPECT_ENTITY_MAP] or list(ASPECT_ENTITY_MAP.keys())

    relevant_types: set[str] = set()
    relevant_keywords: list[str] = []
    for aspect in active_aspects:
        mapping = ASPECT_ENTITY_MAP[aspect]
        relevant_types.update(mapping["types"])
        relevant_keywords.extend(mapping["keywords"])

    civ_data = []
    for civ in civs:
        cid = civ["id"]
        turn_count = conn.execute(
            "SELECT COUNT(*) FROM turn_turns WHERE civ_id = ?", (cid,)
        ).fetchone()[0]

        breakdown_rows = conn.execute(
            "SELECT entity_type, COUNT(*) FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY COUNT(*) DESC",
            (cid,),
        ).fetchall()
        entity_breakdown = {r[0]: r[1] for r in breakdown_rows}

        # Top entities, optionally filtered
        entity_sql = """
            SELECT e.canonical_name AS name, e.entity_type AS type,
                   (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mentions
            FROM entity_entities e
            WHERE e.civ_id = ?
        """
        entity_params: list = [cid]
        if aspects and relevant_types:
            placeholders = ", ".join("?" for _ in relevant_types)
            entity_sql += f" AND e.entity_type IN ({placeholders})"
            entity_params.extend(relevant_types)
        entity_sql += " ORDER BY mentions DESC LIMIT 10"
        top_entities = conn.execute(entity_sql, entity_params).fetchall()

        # Relevant segments
        relevant_segments: list[str] = []
        if aspects and relevant_keywords:
            for keyword in relevant_keywords[:5]:
                segs = conn.execute("""
                    SELECT s.content, t.turn_number
                    FROM turn_segments s
                    JOIN turn_turns t ON s.turn_id = t.id
                    WHERE t.civ_id = ? AND s.content LIKE ?
                    ORDER BY t.turn_number DESC
                    LIMIT 2
                """, (cid, f"%{keyword}%")).fetchall()
                for seg in segs:
                    relevant_segments.append(f"Turn {seg[1]}: {truncate(seg[0], 150)}")
                if len(relevant_segments) >= 5:
                    break

        civ_data.append({
            "civ": civ,
            "turn_count": turn_count,
            "entity_breakdown": entity_breakdown,
            "top_entities": top_entities,
            "relevant_segments": relevant_segments,
        })

    # Format output
    lines = [
        "# Civilization Comparison",
        "",
        f"**Comparing:** {' vs '.join(c['name'] for c in civs)}",
        f"**Aspects:** {', '.join(active_aspects)}",
        "",
        "## Overview",
        "",
    ]

    headers = ["Metric"] + [d["civ"]["name"] for d in civ_data]
    lines.append(f"| {' | '.join(headers)} |")
    lines.append(f"| {' | '.join('---' for _ in headers)} |")
    lines.append(f"| Turns | {' | '.join(str(d['turn_count']) for d in civ_data)} |")

    all_types: set[str] = set()
    for d in civ_data:
        all_types.update(d["entity_breakdown"].keys())
    for etype in sorted(all_types):
        vals = " | ".join(str(d["entity_breakdown"].get(etype, 0)) for d in civ_data)
        lines.append(f"| {etype} entities | {vals} |")
    lines.append("")

    for data in civ_data:
        civ = data["civ"]
        lines.append(f"## {civ['name']}")
        lines.append("")
        if civ.get("player_name"):
            lines.append(f"**Player:** {civ['player_name']}")

        if data["top_entities"]:
            lines += ["", "**Key entities:**"]
            for e in data["top_entities"]:
                lines.append(f"- {e[0]} ({e[1]}, {e[2]} mentions)")

        if data["relevant_segments"]:
            lines += ["", "**Relevant excerpts:**"]
            for seg in data["relevant_segments"]:
                lines.append(f"> {seg}")

        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 9: searchTurnContent
# --------------------------------------------------------------------------- #

def search_turn_content(
    conn: sqlite3.Connection,
    query: str,
    civ_id: int | None = None,
    segment_type: str | None = None,
) -> str:
    sql = """
        SELECT t.turn_number, c.name AS civ_name, s.segment_type, s.content, t.title
        FROM turn_segments s
        JOIN turn_turns t ON s.turn_id = t.id
        JOIN civ_civilizations c ON t.civ_id = c.id
        WHERE s.content LIKE ?
    """
    params: list = [f"%{query}%"]

    if civ_id is not None:
        sql += " AND t.civ_id = ?"
        params.append(civ_id)
    if segment_type:
        sql += " AND s.segment_type = ?"
        params.append(segment_type)

    sql += " ORDER BY t.turn_number DESC LIMIT 20"
    rows = conn.execute(sql, params).fetchall()

    if not rows:
        return f'# Search: "{query}"\n\nNo matching content found.'

    lines = [f'# Search: "{query}"', "", f"**{len(rows)}** result(s).", ""]
    for r in rows:
        turn_num, cn, seg_type, content, title = r
        lines.append(f"### Turn {turn_num} ({cn}) [{seg_type}]")
        lines.append(truncate(content, 500))
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 10: getStructuredFacts
# --------------------------------------------------------------------------- #

VALID_FACT_TYPES = {"technologies", "resources", "beliefs", "geography"}


def _parse_json_list(raw: str | None) -> list[str]:
    """Parse a JSON array string into a list of strings."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(e) for e in parsed if e]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def get_structured_facts(
    conn: sqlite3.Connection,
    civ_id: int,
    civ_name: str,
    fact_type: str | None = None,
    turn_number: int | None = None,
) -> str:
    types_to_query = (
        [fact_type] if fact_type and fact_type in VALID_FACT_TYPES else sorted(VALID_FACT_TYPES)
    )

    sql = "SELECT turn_number, technologies, resources, beliefs, geography FROM turn_turns WHERE civ_id = ?"
    params: list = [civ_id]
    if turn_number is not None:
        sql += " AND turn_number = ?"
        params.append(int(turn_number))
    sql += " ORDER BY turn_number"

    rows = conn.execute(sql, params).fetchall()

    lines = [f"# Structured Facts - {civ_name}", ""]
    if fact_type and fact_type in VALID_FACT_TYPES:
        lines.append(f"**Filter:** {fact_type}")
    if turn_number is not None:
        lines.append(f"**Turn:** {turn_number}")
    lines.append("")

    found_any = False
    for row in rows:
        t_num = row[0]
        facts_for_turn: dict[str, list[str]] = {}
        col_map = {"technologies": row[1], "resources": row[2], "beliefs": row[3], "geography": row[4]}
        for ft in types_to_query:
            items = _parse_json_list(col_map.get(ft))
            if items:
                facts_for_turn[ft] = items

        if facts_for_turn:
            found_any = True
            lines.append(f"## Turn {t_num}")
            lines.append("")
            for ft, items in facts_for_turn.items():
                lines.append(f"**{ft.capitalize()}:**")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

    if not found_any:
        lines.append("No structured facts found for the given filters.")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 11: getChoiceHistory
# --------------------------------------------------------------------------- #

def get_choice_history(
    conn: sqlite3.Connection,
    civ_id: int,
    civ_name: str,
    turn_number: int | None = None,
) -> str:
    sql = """
        SELECT turn_number, title, summary, choices_proposed, choices_made
        FROM turn_turns
        WHERE civ_id = ? AND (choices_proposed IS NOT NULL OR choices_made IS NOT NULL)
    """
    params: list = [civ_id]
    if turn_number is not None:
        sql += " AND turn_number = ?"
        params.append(int(turn_number))
    sql += " ORDER BY turn_number"

    rows = conn.execute(sql, params).fetchall()

    lines = [f"# Choice History - {civ_name}", ""]

    if not rows:
        lines.append("No choices recorded for this civilization.")
        return "\n".join(lines)

    for row in rows:
        t_num, title, summary, proposed_raw, made_raw = row
        lines.append(f"## Turn {t_num}: {title or '(untitled)'}")
        if summary:
            lines.append(f"*{truncate(summary, 200)}*")
        lines.append("")

        proposed = _parse_json_list(proposed_raw)
        if proposed:
            lines.append("**Choices proposed:**")
            for i, choice in enumerate(proposed, 1):
                lines.append(f"{i}. {choice}")
            lines.append("")

        made = _parse_json_list(made_raw)
        if made:
            lines.append("**Decision:**")
            for decision in made:
                lines.append(f"-> {decision}")
            lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 12: exploreRelations
# --------------------------------------------------------------------------- #

def _resolve_entity(
    conn: sqlite3.Connection, entity_name: str, civ_id: int | None = None
) -> list[dict]:
    """Find entities matching a name or alias."""
    sql = """
        SELECT e.id, e.canonical_name, e.entity_type
        FROM entity_entities e
        WHERE (e.canonical_name LIKE ? OR e.id IN (
            SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ?
        ))
    """
    pattern = f"%{entity_name}%"
    params: list = [pattern, pattern]
    if civ_id is not None:
        sql += " AND e.civ_id = ?"
        params.append(civ_id)
    sql += " ORDER BY e.canonical_name LIMIT 5"
    rows = conn.execute(sql, params).fetchall()
    return [{"id": r[0], "name": r[1], "type": r[2]} for r in rows]


def explore_relations(
    conn: sqlite3.Connection,
    entity_name: str,
    civ_id: int | None = None,
    depth: int = 1,
) -> str:
    entities = _resolve_entity(conn, entity_name, civ_id)
    if not entities:
        return f'# Relations: "{entity_name}"\n\nNo entity found matching "{entity_name}".'

    root = entities[0]
    lines = [f"# Relations: {root['name']} ({root['type']})", ""]

    visited: set[int] = set()
    queue: list[tuple[int, str, int]] = [(root["id"], root["name"], 0)]
    relation_lines: list[str] = []

    while queue:
        eid, ename, current_depth = queue.pop(0)
        if eid in visited:
            continue
        visited.add(eid)

        rels = conn.execute("""
            SELECT 'outgoing' AS direction, t.id, t.canonical_name, t.entity_type,
                   r.relation_type, r.description
            FROM entity_relations r
            JOIN entity_entities t ON r.target_entity_id = t.id
            WHERE r.source_entity_id = ? AND r.is_active = 1
            UNION ALL
            SELECT 'incoming' AS direction, s.id, s.canonical_name, s.entity_type,
                   r.relation_type, r.description
            FROM entity_relations r
            JOIN entity_entities s ON r.source_entity_id = s.id
            WHERE r.target_entity_id = ? AND r.is_active = 1
        """, (eid, eid)).fetchall()

        for rel in rels:
            direction, other_id, other_name, other_type, rel_type, desc = rel
            indent = "  " * current_depth
            if direction == "outgoing":
                arrow = f"{ename} --[{rel_type}]--> {other_name} ({other_type})"
            else:
                arrow = f"{other_name} ({other_type}) --[{rel_type}]--> {ename}"
            detail = f" -- {desc}" if desc else ""
            relation_lines.append(f"{indent}- {arrow}{detail}")

            if current_depth + 1 < depth and other_id not in visited:
                queue.append((other_id, other_name, current_depth + 1))

    if relation_lines:
        lines.append(f"**Depth:** {depth}")
        lines.append(f"**Relations found:** {len(relation_lines)}")
        lines.append("")
        lines.extend(relation_lines)
    else:
        lines.append("No relations found for this entity.")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 13: filterTimeline
# --------------------------------------------------------------------------- #

def filter_timeline(
    conn: sqlite3.Connection,
    civ_id: int | None = None,
    turn_type: str | None = None,
    from_turn: int | None = None,
    to_turn: int | None = None,
    entity_name: str | None = None,
) -> str:
    if entity_name:
        sql = """
            SELECT DISTINCT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, c.name AS civ_name
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            LEFT JOIN entity_mentions m ON m.turn_id = t.id
            LEFT JOIN entity_entities e ON m.entity_id = e.id
            LEFT JOIN entity_aliases a ON a.entity_id = e.id
            WHERE (e.canonical_name LIKE ? OR a.alias LIKE ?)
        """
        pattern = f"%{entity_name}%"
        params: list = [pattern, pattern]
    else:
        sql = """
            SELECT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, c.name AS civ_name
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            WHERE 1=1
        """
        params = []

    if civ_id is not None:
        sql += " AND t.civ_id = ?"
        params.append(civ_id)
    if turn_type:
        sql += " AND t.turn_type = ?"
        params.append(turn_type)
    if from_turn is not None:
        sql += " AND t.turn_number >= ?"
        params.append(int(from_turn))
    if to_turn is not None:
        sql += " AND t.turn_number <= ?"
        params.append(int(to_turn))

    sql += " ORDER BY t.turn_number ASC, c.name LIMIT 100"
    rows = conn.execute(sql, params).fetchall()

    # Build title
    filters = []
    if turn_type:
        filters.append(f"type={turn_type}")
    if from_turn is not None or to_turn is not None:
        f_str = str(from_turn) if from_turn is not None else "?"
        t_str = str(to_turn) if to_turn is not None else "?"
        filters.append(f"turns {f_str}-{t_str}")
    if entity_name:
        filters.append(f"entity={entity_name}")
    filter_str = f" ({', '.join(filters)})" if filters else ""

    lines = [f"# Filtered Timeline{filter_str}", ""]

    if not rows:
        lines.append("No turns match the given filters.")
        return "\n".join(lines)

    lines += [
        f"**{len(rows)}** turn(s) found.",
        "",
        "| Turn | Civilization | Type | Summary |",
        "|---|---|---|---|",
    ]
    for r in rows:
        turn_num, title, summary, t_type, gd_start, cn = r
        text = truncate(summary or title or "(no summary)", 100)
        lines.append(f"| {turn_num} | {cn} | {t_type} | {text} |")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 14: entityActivity
# --------------------------------------------------------------------------- #

def entity_activity(
    conn: sqlite3.Connection,
    entity_name: str,
    civ_id: int | None = None,
) -> str:
    entities = _resolve_entity(conn, entity_name, civ_id)
    if not entities:
        return f'# Entity Activity: "{entity_name}"\n\nNo entity found matching "{entity_name}".'

    entity = entities[0]
    eid = entity["id"]

    rows = conn.execute("""
        SELECT t.turn_number, COUNT(*) AS cnt
        FROM entity_mentions m
        JOIN turn_turns t ON m.turn_id = t.id
        WHERE m.entity_id = ?
        GROUP BY t.turn_number
        ORDER BY t.turn_number
    """, (eid,)).fetchall()

    lines = [f"# Entity Activity: {entity['name']} ({entity['type']})", ""]

    if not rows:
        lines.append("No mentions found.")
        return "\n".join(lines)

    turn_counts = [(r[0], r[1]) for r in rows]
    first_turn = turn_counts[0][0]
    last_turn = turn_counts[-1][0]
    total_mentions = sum(c for _, c in turn_counts)
    peak_turn, peak_count = max(turn_counts, key=lambda x: x[1])

    lines.append(f"**First appearance:** Turn {first_turn}")
    lines.append(f"**Last appearance:** Turn {last_turn}")
    lines.append(f"**Total mentions:** {total_mentions}")
    lines.append(f"**Peak activity:** Turn {peak_turn} ({peak_count} mentions)")
    lines.append("")

    # ASCII sparkline
    max_count = max(c for _, c in turn_counts)
    sparkline_chars = " _.-:=+*#"
    lines.append("## Activity by Turn")
    lines.append("")
    lines.append("```")
    for t_num, cnt in turn_counts:
        bar_idx = min(int(cnt / max_count * (len(sparkline_chars) - 1)), len(sparkline_chars) - 1)
        bar = sparkline_chars[bar_idx] * cnt
        lines.append(f"Turn {t_num:>3}: {bar} ({cnt})")
    lines.append("```")
    lines.append("")

    # Recent contexts
    recent = conn.execute("""
        SELECT m.context, t.turn_number
        FROM entity_mentions m
        JOIN turn_turns t ON m.turn_id = t.id
        WHERE m.entity_id = ?
        ORDER BY t.turn_number DESC
        LIMIT 3
    """, (eid,)).fetchall()

    if recent:
        lines.append("## Recent Mentions")
        lines.append("")
        for r in recent:
            ctx = truncate(r[0], 200) if r[0] else "(no context)"
            lines.append(f"- **Turn {r[1]}:** {ctx}")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# getTechTree
# --------------------------------------------------------------------------- #

TECH_CATEGORIES = {
    "Outils de chasse": ["gourdin", "pieux", "pieu", "arc", "fleche", "lance", "harpon", "chasseur"],
    "Outils de peche": ["filet", "ligne", "hamecon", "peche", "nasse", "poisson"],
    "Agriculture": ["semence", "irrigation", "culture", "plantation", "recolte", "agriculture", "champ"],
    "Artisanat": ["tissage", "poterie", "vannerie", "tannage", "artisan", "metier"],
    "Construction": ["cabane", "palissade", "maison", "construction", "batiment", "architecture"],
    "Navigation": ["radeau", "barque", "bateau", "pirogue", "navigation", "voile"],
    "Feu et lumiere": ["feu", "flambeau", "braise", "torche", "foyer", "fumage"],
    "Musique et rituel": ["rhombe", "pipeau", "tambour", "chant", "rituel", "musique", "voix", "presage"],
    "Materiaux": ["argile", "pierre", "roche", "os", "bois", "pigment"],
}


def _categorize_tech(tech_name: str) -> str:
    """Assign a category to a technology based on keywords."""
    tech_lower = tech_name.lower()
    for cat, keywords in TECH_CATEGORIES.items():
        if any(kw in tech_lower for kw in keywords):
            return cat
    return "Autre"


def get_tech_tree(
    conn: sqlite3.Connection,
    civ_id: int,
    civ_name: str,
    *,
    category: str | None = None,
) -> str:
    """Return the full technology tree for a civilization, organized by category.

    Args:
        conn: Database connection
        civ_id: Civilization ID
        civ_name: Civilization name (for display)
        category: Optional filter by category name
    """
    rows = conn.execute(
        """SELECT turn_number, technologies
           FROM turn_turns
           WHERE civ_id = ? AND technologies IS NOT NULL AND technologies != '[]'
           ORDER BY turn_number""",
        (civ_id,),
    ).fetchall()

    if not rows:
        return f"No technologies found for {civ_name}."

    # Build flat list: (tech_name, turn_number, category)
    # row[0] = turn_number, row[1] = technologies JSON
    all_techs: list[tuple[str, int, str]] = []
    for r in rows:
        techs = _parse_json_list(r[1])
        for t in techs:
            cat = _categorize_tech(t)
            all_techs.append((t, r[0], cat))

    # Filter by category if requested
    if category:
        cat_lower = category.lower()
        filtered = [t for t in all_techs if cat_lower in t[2].lower()]
        if not filtered:
            available = sorted(set(t[2] for t in all_techs))
            return f"No technologies in category '{category}'. Available: {', '.join(available)}"
        all_techs = filtered

    # After parsing, all_techs may still be empty if JSON contained only nulls
    if not all_techs:
        return f"No valid technologies found for {civ_name} (all entries were null/empty)."

    # Group by category
    by_cat: dict[str, list[tuple[str, int]]] = {}
    for tech_name, turn_num, cat in all_techs:
        by_cat.setdefault(cat, []).append((tech_name, turn_num))

    lines = [f"# Tech Tree -- {civ_name}", ""]

    # Summary
    total = len(all_techs)
    first_turn = min(t[1] for t in all_techs)
    last_turn = max(t[1] for t in all_techs)
    lines.append(f"**{total} technologies** acquired from Turn {first_turn} to Turn {last_turn}")
    lines.append(f"**Categories:** {', '.join(sorted(by_cat.keys()))}")
    lines.append("")

    # By category
    for cat in sorted(by_cat.keys()):
        techs = sorted(by_cat[cat], key=lambda x: x[1])
        lines.append(f"## {cat} ({len(techs)})")
        lines.append("")
        for tech_name, turn_num in techs:
            lines.append(f"- **{tech_name}** (Tour {turn_num})")
        lines.append("")

    # Chronological timeline
    lines.append("## Timeline")
    lines.append("")
    by_turn: dict[int, list[str]] = {}
    for tech_name, turn_num, _ in sorted(all_techs, key=lambda x: x[1]):
        by_turn.setdefault(turn_num, []).append(tech_name)
    for turn_num in sorted(by_turn.keys()):
        techs_str = ", ".join(by_turn[turn_num])
        lines.append(f"**Tour {turn_num}** -> {techs_str}")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool definitions for Claude API tool_use
# --------------------------------------------------------------------------- #

TOOL_DEFINITIONS = [
    {
        "name": "listCivs",
        "description": "Liste toutes les civilisations avec nombre de tours et d'entites.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "getCivState",
        "description": "Etat actuel d'une civilisation: tours recents, entites-cles, breakdown par type.",
        "input_schema": {
            "type": "object",
            "properties": {"civName": {"type": "string", "description": "Nom de la civilisation"}},
            "required": ["civName"],
        },
    },
    {
        "name": "getTurnDetail",
        "description": "Detail complet d'un tour: segments, entites mentionnees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civilisation"},
                "turnNumber": {"type": "integer", "description": "Numero du tour"},
            },
            "required": ["civName", "turnNumber"],
        },
    },
    {
        "name": "searchLore",
        "description": "Recherche dans le lore (entites, descriptions, aliases, historique).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texte a rechercher"},
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
                "entityType": {"type": "string", "description": "Filtrer par type d'entite (optionnel)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "getEntityDetail",
        "description": "Fiche complete d'une entite: description, chronologie, relations, mentions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Nom de l'entite"},
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "sanityCheck",
        "description": "Verifie la coherence d'une affirmation contre le lore etabli.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statement": {"type": "string", "description": "L'affirmation a verifier"},
                "civName": {"type": "string", "description": "Contexte civilisation (optionnel)"},
            },
            "required": ["statement"],
        },
    },
    {
        "name": "timeline",
        "description": "Chronologie des tours avec nombre d'entites par tour.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
                "limit": {"type": "integer", "description": "Nombre max de tours (defaut 50)"},
            },
            "required": [],
        },
    },
    {
        "name": "compareCivs",
        "description": "Compare plusieurs civilisations sur un ou plusieurs aspects (military, technology, politics, economy, culture).",
        "input_schema": {
            "type": "object",
            "properties": {
                "civNames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Noms des civilisations a comparer",
                },
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Aspects a comparer (optionnel, defaut: tous)",
                },
            },
            "required": ["civNames"],
        },
    },
    {
        "name": "searchTurnContent",
        "description": "Recherche plein texte dans le contenu des segments de tour.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texte a rechercher"},
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
                "segmentType": {"type": "string", "description": "Filtrer par type de segment (optionnel)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "getStructuredFacts",
        "description": "Faits structures par tour: technologies, ressources, croyances, geographie.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civilisation"},
                "factType": {"type": "string", "description": "Type de fait: technologies, resources, beliefs, geography, ou all (optionnel)"},
                "turnNumber": {"type": "integer", "description": "Numero du tour (optionnel)"},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "getChoiceHistory",
        "description": "Historique des choix proposes et decisions prises par civilisation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civilisation"},
                "turnNumber": {"type": "integer", "description": "Numero du tour (optionnel)"},
            },
            "required": ["civName"],
        },
    },
    {
        "name": "exploreRelations",
        "description": "Explore le graphe de relations d'une entite (controle, appartenance, alliances...).",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Nom de l'entite"},
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
                "depth": {"type": "integer", "description": "Profondeur de navigation (1-3, defaut 1)"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "filterTimeline",
        "description": "Timeline filtree par type de tour, intervalle, ou entite mentionnee.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
                "turnType": {"type": "string", "description": "Type de tour: standard, event, first_contact, crisis (optionnel)"},
                "fromTurn": {"type": "integer", "description": "Tour de depart (optionnel)"},
                "toTurn": {"type": "integer", "description": "Tour de fin (optionnel)"},
                "entityName": {"type": "string", "description": "Filtrer les tours mentionnant cette entite (optionnel)"},
            },
            "required": [],
        },
    },
    {
        "name": "entityActivity",
        "description": "Activite temporelle d'une entite: sparkline des mentions, pic, contexte recent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entityName": {"type": "string", "description": "Nom de l'entite"},
                "civName": {"type": "string", "description": "Filtrer par civilisation (optionnel)"},
            },
            "required": ["entityName"],
        },
    },
    {
        "name": "getTechTree",
        "description": "Arbre technologique complet d'une civilisation, organise par categorie (chasse, peche, construction, etc.) avec timeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "civName": {"type": "string", "description": "Nom de la civilisation"},
                "category": {"type": "string", "description": "Filtrer par categorie (optionnel): Outils de chasse, Outils de peche, Construction, Navigation, etc."},
            },
            "required": ["civName"],
        },
    },
]


_NIL_VALUES = {"<nil>", "nil", "null", "none", "None", "undefined", ""}


def _clean_input(tool_input: dict) -> dict:
    """Sanitize LLM-generated tool inputs: replace nil-like values with None."""
    return {k: (None if isinstance(v, str) and v in _NIL_VALUES else v) for k, v in tool_input.items()}


def dispatch_tool(conn: sqlite3.Connection, tool_name: str, tool_input: dict) -> str:
    """Route a tool call to the appropriate function. Returns Markdown string."""
    tool_input = _clean_input(tool_input)

    def _resolve(name_key: str = "civName") -> dict | None:
        """Resolve a civ name from tool_input, returning the civ dict or None (with error in result)."""
        civ_name = tool_input.get(name_key)
        if not civ_name:
            return None
        result = resolve_civ_name(conn, civ_name)
        if "error" in result:
            return result
        return result["civ"]

    if tool_name == "listCivs":
        return list_civs(conn)

    if tool_name == "getCivState":
        resolved = _resolve()
        if resolved is None:
            return "Error: civName is required."
        if "error" in resolved:
            return resolved["error"]
        return get_civ_state(conn, resolved["id"], resolved["name"])

    if tool_name == "getTurnDetail":
        resolved = _resolve()
        if resolved is None:
            return "Error: civName is required."
        if "error" in resolved:
            return resolved["error"]
        turn_number = tool_input.get("turnNumber")
        if turn_number is None:
            return "Error: turnNumber is required."
        return get_turn_detail(conn, int(turn_number), resolved["id"], resolved["name"])

    if tool_name == "searchLore":
        query = tool_input.get("query", "")
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return search_lore(conn, query, civ_id=civ_id, entity_type=tool_input.get("entityType"))

    if tool_name == "getEntityDetail":
        entity_name = tool_input.get("entityName", "")
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return get_entity_detail(conn, entity_name, civ_id=civ_id)

    if tool_name == "sanityCheck":
        statement = tool_input.get("statement", "")
        civ_id = None
        civ_name_resolved = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
                civ_name_resolved = resolved["name"]
        return sanity_check(conn, statement, civ_id=civ_id, civ_name=civ_name_resolved)

    if tool_name == "timeline":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        limit = tool_input.get("limit", 50)
        return timeline(conn, civ_id=civ_id, limit=int(limit))

    if tool_name == "compareCivs":
        civ_names_raw = tool_input.get("civNames", [])
        # Handle string input: "all" fetches everything, otherwise split by comma
        if isinstance(civ_names_raw, str):
            if civ_names_raw.lower() in ("all", "toutes", "*", ""):
                all_rows = conn.execute("SELECT id, name, player_name FROM civ_civilizations ORDER BY name").fetchall()
                resolved_civs = [{"id": r[0], "name": r[1], "player_name": r[2]} for r in all_rows]
            else:
                civ_names_raw = [n.strip() for n in civ_names_raw.split(",") if n.strip()]
                resolved_civs = []
                for cn in civ_names_raw:
                    result = resolve_civ_name(conn, cn)
                    if "error" in result:
                        return result["error"]
                    resolved_civs.append(result["civ"])
        else:
            resolved_civs = []
            seen_ids: set[int] = set()
            for cn in civ_names_raw:
                result = resolve_civ_name(conn, cn)
                if "error" in result:
                    return result["error"]
                civ = result["civ"]
                if civ["id"] not in seen_ids:
                    seen_ids.add(civ["id"])
                    resolved_civs.append(civ)
        if len(resolved_civs) < 2:
            names = ", ".join(c["name"] for c in resolved_civs) if resolved_civs else "aucune"
            all_civs = conn.execute("SELECT name FROM civ_civilizations ORDER BY name").fetchall()
            civ_list = ", ".join(r[0] for r in all_civs)
            return f"Cannot compare fewer than 2 civilizations. Found: {names}. Available: {civ_list}. Use listCivs to see all civilizations first."
        return compare_civs(conn, resolved_civs, aspects=tool_input.get("aspects"))

    if tool_name == "searchTurnContent":
        query = tool_input.get("query", "")
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return search_turn_content(conn, query, civ_id=civ_id, segment_type=tool_input.get("segmentType"))

    if tool_name == "getStructuredFacts":
        resolved = _resolve()
        if resolved is None:
            return "Error: civName is required."
        if "error" in resolved:
            return resolved["error"]
        return get_structured_facts(
            conn,
            resolved["id"],
            resolved["name"],
            fact_type=tool_input.get("factType"),
            turn_number=tool_input.get("turnNumber"),
        )

    if tool_name == "getChoiceHistory":
        resolved = _resolve()
        if resolved is None:
            return "Error: civName is required."
        if "error" in resolved:
            return resolved["error"]
        return get_choice_history(
            conn,
            resolved["id"],
            resolved["name"],
            turn_number=tool_input.get("turnNumber"),
        )

    if tool_name == "exploreRelations":
        entity_name = tool_input.get("entityName", "")
        if not entity_name:
            return "Error: entityName is required."
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        depth = min(int(tool_input.get("depth", 1)), 3)
        return explore_relations(conn, entity_name, civ_id=civ_id, depth=depth)

    if tool_name == "filterTimeline":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return filter_timeline(
            conn,
            civ_id=civ_id,
            turn_type=tool_input.get("turnType"),
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            entity_name=tool_input.get("entityName"),
        )

    if tool_name == "entityActivity":
        entity_name = tool_input.get("entityName", "")
        if not entity_name:
            return "Error: entityName is required."
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return entity_activity(conn, entity_name, civ_id=civ_id)

    if tool_name == "getTechTree":
        resolved = _resolve()
        if resolved is None:
            return "Error: civName is required."
        if "error" in resolved:
            return resolved["error"]
        return get_tech_tree(
            conn,
            resolved["id"],
            resolved["name"],
            category=tool_input.get("category"),
        )

    return f"Unknown tool: {tool_name}"
