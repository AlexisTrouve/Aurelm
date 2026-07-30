"""Python port of the 9 MCP tools from mcp-server/src/tools/*.ts.

All functions take a sqlite3 connection and return a Markdown string.
"""

from __future__ import annotations

import json
import re
import sqlite3

from .map_seeding import discover, discovered_set, propose_spawn_positions

# --------------------------------------------------------------------------- #
# Helpers (ported from mcp-server/src/helpers.ts)
# --------------------------------------------------------------------------- #

def _escape_like(value: str) -> str:
    """Escape SQL LIKE special characters (% and _) so they match literally.

    Use with `LIKE ? ESCAPE '!'` in the query.
    """
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def _fuzzy_like_pattern(query: str) -> str:
    """Build a fuzzy LIKE pattern: hyphens/spaces interchangeable, optional trailing plural.

    'Ailes Grises' matches 'Ailes-Grises', 'ailes grises', 'Ailes-Grises' etc.
    Each space or hyphen becomes '%' (wildcard) to bridge the gap.
    """
    escaped = _escape_like(query)
    # Replace spaces and hyphens with '%' wildcard so both match
    import re
    fuzzy = re.sub(r'[\s\-]+', '%', escaped)
    return f"%{fuzzy}%"


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
# Standard filter helper
# --------------------------------------------------------------------------- #

def _turn_range_conditions(
    from_turn: int | None,
    to_turn: int | None,
    last_n_turns: int | None,
    conn: sqlite3.Connection,
    turn_alias: str = "t",
) -> tuple[list[str], list]:
    """Return (sql_conditions, params) for turn number range filtering.

    lastNTurns takes precedence over fromTurn/toTurn when provided.
    Computes effective_from = max_turn - last_n_turns + 1 so "last 5 turns"
    means the 5 most recent turns in the DB.
    """
    conditions: list[str] = []
    params: list = []

    if last_n_turns is not None:
        max_turn = conn.execute("SELECT MAX(turn_number) FROM turn_turns").fetchone()[0] or 0
        effective_from = max(1, max_turn - last_n_turns + 1)
        conditions.append(f"{turn_alias}.turn_number >= ?")
        params.append(effective_from)
    else:
        if from_turn is not None:
            conditions.append(f"{turn_alias}.turn_number >= ?")
            params.append(from_turn)
        if to_turn is not None:
            conditions.append(f"{turn_alias}.turn_number <= ?")
            params.append(to_turn)

    return conditions, params


# --------------------------------------------------------------------------- #
# Tool 1: listCivs
# --------------------------------------------------------------------------- #

def list_civs(conn: sqlite3.Connection) -> str:
    rows = conn.execute("""
        SELECT c.name, c.player_name,
               (SELECT COUNT(*) FROM turn_turns t WHERE t.civ_id = c.id) AS turn_count,
               (SELECT COUNT(*) FROM entity_entities e WHERE e.civ_id = c.id AND e.disabled = 0) AS entity_count
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
        "SELECT COUNT(*) FROM entity_entities WHERE civ_id = ? AND disabled = 0", (civ_id,)
    ).fetchone()[0]

    breakdown = conn.execute(
        "SELECT entity_type, COUNT(*) AS count FROM entity_entities WHERE civ_id = ? AND disabled = 0 GROUP BY entity_type ORDER BY count DESC",
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
        WHERE e.civ_id = ? AND e.disabled = 0
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
    conn: sqlite3.Connection,
    turn_number: int,
    civ_id: int,
    civ_name: str,
    show_segments: bool = False,
    show_entities: bool = False,
    show_notes: bool = False,
) -> str:
    turn = conn.execute("""
        SELECT t.id, t.turn_number, t.title, t.summary, t.turn_type,
               t.game_date_start, t.game_date_end, c.name AS civ_name,
               t.key_events, t.choices_proposed, t.choices_made,
               t.novelty_summary, t.player_strategy, t.strategy_tags
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

    t_id, t_num, title, summary, turn_type, gd_start, gd_end, cn, key_events_raw, proposed_raw, made_raw, novelty_summary, player_strategy, strategy_tags = turn
    lines = [f"# Turn {t_num}: {title or '(untitled)'} - {cn}", ""]

    if turn_type != "standard":
        lines.append(f"**Type:** {turn_type}")
    if gd_start:
        date_str = gd_start + (f" -- {gd_end}" if gd_end else "")
        lines.append(f"**Game date:** {date_str}")
    if summary:
        lines.append(f"**Summary:** {summary}")
    lines.append("")

    # Preanalysis — novelty + player strategy
    if novelty_summary:
        lines += [f"**Novelty:** {novelty_summary}", ""]
    if player_strategy:
        tags_str = ""
        if strategy_tags:
            tags = _parse_json_list(strategy_tags)
            if tags:
                tags_str = f" [{', '.join(tags)}]"
        lines += [f"**Player strategy:** {player_strategy}{tags_str}", ""]

    key_events = _parse_json_list(key_events_raw)
    if key_events:
        lines += ["## Key Events", ""]
        for ev in key_events:
            lines.append(f"- {ev}")
        lines.append("")

    proposed = _parse_json_list(proposed_raw)
    if proposed:
        lines += ["## Choices Proposed", ""]
        for i, ch in enumerate(proposed, 1):
            lines.append(f"{i}. {ch}")
        lines.append("")

    made = _parse_json_list(made_raw)
    if made:
        lines += ["## Decision", ""]
        for d in made:
            lines.append(f"-> {d}")
        lines.append("")

    # Segments — opt-in via show_segments
    if show_segments:
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

    # Entities mentioned — opt-in via show_entities
    if show_entities:
        entities = conn.execute("""
            SELECT e.canonical_name, e.entity_type, COUNT(*) AS mention_count
            FROM entity_mentions m
            JOIN entity_entities e ON m.entity_id = e.id
            WHERE m.turn_id = ? AND e.disabled = 0
            GROUP BY e.id
            ORDER BY mention_count DESC
        """, (t_id,)).fetchall()

        if entities:
            lines += ["## Entities Mentioned", "", "| Entity | Type | Mentions |", "|---|---|---|"]
            for e in entities:
                lines.append(f"| {e[0]} | {e[1]} | {e[2]} |")

    # Notes GM — show_notes or pinned-only
    all_notes = _get_notes_for(conn, turn_id=t_id)
    if show_notes:
        lines += _format_notes_section(all_notes)
    else:
        # Always show pinned notes even without show_notes
        pinned = [n for n in all_notes if n.get("pinned")]
        lines += _format_notes_section(pinned)

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 4: searchLore
# --------------------------------------------------------------------------- #

def _truncation_notice(limit: int, what: str = "resultats", total: int | None = None) -> str:
    """Tell the agent, in the output itself, that the list is INCOMPLETE.

    WHY this exists: every list tool caps with a bare LIMIT. Without a notice the agent
    receives a silently truncated slice, believes it holds everything, and answers
    "voici toutes les entites militaires" from a subset -- confidently wrong, with no
    way for the GM to notice. Silence here does not lose data, it manufactures false
    certainty.

    WHY the total, and not just "there are more": measured on the live agent. Told only
    that more existed, asked "combien y en a-t-il en tout ?", it answered "41 entites,
    Garde 00 a 39" -- a count and a range it had never seen, stated as fact. Knowing the
    cut exists is not enough; without the number the model fills the gap by inference.
    """
    shown = (f"{limit} {what} affiches sur {total} au total"
             if total is not None else f"{limit} {what} affiches, il y en a d'autres")
    return (f"\n\n> **Liste tronquee** : {shown}. N'EXTRAPOLE PAS le contenu manquant. "
            f"Affine la recherche (civName / tag / lastNTurns / entityType) "
            f"ou augmente `limit`.")


def search_lore(
    conn: sqlite3.Connection,
    query: str = "",
    civ_id: int | None = None,
    entity_type: str | None = None,
    tag: str | None = None,
    from_turn: int | None = None,
    to_turn: int | None = None,
    last_n_turns: int | None = None,
    limit: int = 20,
) -> str:
    """Search entities by name/description/alias.

    With tag= (and empty query), behaves like getEntitiesByTag.
    Turn range filters (fromTurn/toTurn/lastNTurns) filter by first_seen_turn.
    """
    # Build WHERE conditions incrementally
    conditions = ["e.disabled = 0"]
    params: list = []

    # Text search (optional when tag is provided)
    # Fuzzy: hyphens/spaces interchangeable so "Ailes Grises" matches "Ailes-Grises"
    if query:
        pattern = _fuzzy_like_pattern(query)
        conditions.append(
            "(e.canonical_name LIKE ? ESCAPE '!' OR e.description LIKE ? ESCAPE '!'"
            " OR a.alias LIKE ? ESCAPE '!')"
        )
        # Note: removed history LIKE — too noisy, description covers it
        params.extend([pattern, pattern, pattern])

    if civ_id is not None:
        conditions.append("e.civ_id = ?")
        params.append(civ_id)
    if entity_type:
        conditions.append("e.entity_type = ?")
        params.append(entity_type)
    if tag:
        # JSON array contains match
        conditions.append("e.tags LIKE ?")
        params.append(f'%"{tag}"%')

    # Turn range: filter by first_seen_turn join
    turn_conds, turn_params = _turn_range_conditions(from_turn, to_turn, last_n_turns, conn, turn_alias="ft")
    if turn_conds:
        conditions.append("ft.turn_number IS NOT NULL")  # ensure join is not null
        conditions.extend(turn_conds)
        params.extend(turn_params)

    where_sql = " AND ".join(conditions)

    # Need LEFT JOIN on turn if filtering by turn range
    turn_join = ""
    if turn_conds:
        turn_join = "LEFT JOIN turn_turns ft ON ft.id = e.first_seen_turn"

    sql = f"""
        SELECT DISTINCT e.id, e.canonical_name, e.entity_type, e.description, e.history,
               c.name AS civ_name,
               (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON e.civ_id = c.id
        LEFT JOIN entity_aliases a ON a.entity_id = e.id
        {turn_join}
        WHERE {where_sql}
        ORDER BY mention_count DESC LIMIT ?
    """
    # Real total for the truncation notice: without it the agent, asked "combien en
    # tout ?", invented a count from the visible slice (measured live: "41 entites").
    count_sql = f"""
        SELECT COUNT(DISTINCT e.id)
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON e.civ_id = c.id
        LEFT JOIN entity_aliases a ON a.entity_id = e.id
        {turn_join}
        WHERE {where_sql}
    """
    total_matches = conn.execute(count_sql, list(params)).fetchone()[0]
    params.append(limit + 1)
    entities = conn.execute(sql, params).fetchall()
    truncated = len(entities) > limit
    entities = entities[:limit]

    if not entities:
        return f'# Lore Search: "{query}"\n\nNo entities found matching "{query}".'

    lines = [f'# Lore Search: "{query}"', "", f"**{len(entities)}** result(s) found.", ""]

    for e in entities:
        eid, name, etype, desc, history, cn, mc = e
        lines.append(f"## {name} ({etype})")
        if cn:
            lines.append(f"**Civilization:** {cn} | **Mentions:** {mc}")
        else:
            lines.append(f"**Mentions:** {mc}")

        # Description tronquee -- searchLore donne un apercu, pas le detail complet
        if desc:
            lines.append(f"**Description:** {truncate(desc, 200)}")

        # Aliases (compact, une ligne)
        aliases = conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (eid,)
        ).fetchall()
        if aliases:
            lines.append(f"**Aliases:** {', '.join(a[0] for a in aliases)}")

        # Pas de chronologie complete ni de mentions -- utiliser getEntityDetail pour ca
        lines.append("")

    # Hint pour l'agent : pointer vers les tools de detail
    lines.append("---")
    lines.append("*Pour plus de details sur une entite, utilise `getEntityDetail`. "
                  "Pour les faits structures, utilise `getStructuredFacts`.*")

    if truncated:
        lines.append(_truncation_notice(limit, "entites", total_matches))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 5: getEntityDetail
# --------------------------------------------------------------------------- #

def get_entity_detail(
    conn: sqlite3.Connection,
    entity_name: str,
    civ_id: int | None = None,
    include_relations: bool = False,
    include_activity: bool = False,
    show_mentions: bool = False,
    show_facts: bool = False,
    show_notes: bool = False,
) -> str:
    """Full entity profile.

    include_relations=True: add relation graph (replaces exploreRelations).
    include_activity=True: add per-turn activity sparkline (replaces entityActivity).
    show_mentions: include last 20 mentions (opt-in).
    show_facts: include chronology/history (opt-in).
    show_notes: include GM notes (opt-in; pinned notes always shown).
    """
    sql = """
        SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
               c.name AS civ_name, e.is_active,
               ft.turn_number AS first_turn, lt.turn_number AS last_turn,
               e.tags
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON e.civ_id = c.id
        LEFT JOIN turn_turns ft ON e.first_seen_turn = ft.id
        LEFT JOIN turn_turns lt ON e.last_seen_turn = lt.id
        WHERE e.disabled = 0
          AND (e.canonical_name LIKE ? ESCAPE '!' OR e.id IN (
          SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ? ESCAPE '!'
        ))
    """
    pattern = f"%{_escape_like(entity_name)}%"
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
        eid, name, etype, desc, history, cn, active, ft, lt, tags_json = e
        lines.append(f"# {name} ({etype})")
        lines.append("")
        if cn:
            lines.append(f"**Civilization:** {cn}")
        lines.append(f"**Status:** {'active' if active else 'inactive'}")
        if ft is not None:
            lines.append(f"**First seen:** Turn {ft}")
        if lt is not None:
            lines.append(f"**Last seen:** Turn {lt}")
        # Domain tags — helps agent understand narrative role without extra calls
        entity_tags = _parse_json_list(tags_json or "[]")
        if entity_tags:
            lines.append(f"**Tags:** {', '.join(entity_tags)}")
        if desc:
            lines.append(f"**Description:** {desc}")

        # Chronology — opt-in via show_facts
        if show_facts:
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

        # Relations (both directions) — opt-in via include_relations
        if include_relations:
            rels = conn.execute("""
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

            if rels:
                # The description carries the WHY of the link ("allied after the
                # Confluence traded clay"). It used to be selected and thrown away,
                # leaving the agent with "A -allied_with-> B" and no idea why.
                lines += ["", "## Relations", "",
                          "| Direction | Entity | Type | Relation | Détail | Turn |",
                          "|---|---|---|---|---|---|"]
                for rel in rels:
                    rel_dir, other_name, other_type, rel_type, desc, turn_num = rel
                    arrow = "->" if rel_dir == "outgoing" else "<-"
                    turn_str = str(turn_num) if turn_num is not None else "-"
                    detail = truncate((desc or "").replace("|", "/").replace("\n", " "), 120) or "-"
                    lines.append(
                        f"| {arrow} | {other_name} | {other_type} | {rel_type} | {detail} | {turn_str} |")
            else:
                lines += ["", "## Relations", "", "_Aucune relation trouvée._"]

        # Activity sparkline — opt-in via include_activity
        if include_activity:
            act_rows = conn.execute("""
                SELECT t.turn_number, COUNT(*) AS cnt
                FROM entity_mentions m
                JOIN turn_turns t ON m.turn_id = t.id
                WHERE m.entity_id = ?
                GROUP BY t.turn_number
                ORDER BY t.turn_number
            """, (eid,)).fetchall()

            if act_rows:
                turn_counts = [(r[0], r[1]) for r in act_rows]
                total_mentions = sum(c for _, c in turn_counts)
                peak_turn, peak_count = max(turn_counts, key=lambda x: x[1])
                max_count = max(c for _, c in turn_counts)
                sparkline_chars = " _.-:=+*#"
                lines += ["", "## Activity", ""]
                lines.append(f"**Total mentions:** {total_mentions} | **Peak:** Turn {peak_turn} ({peak_count})")
                lines.append("")
                lines.append("```")
                for t_num, cnt in turn_counts:
                    bar_idx = min(int(cnt / max_count * (len(sparkline_chars) - 1)), len(sparkline_chars) - 1)
                    bar = sparkline_chars[bar_idx] * cnt
                    lines.append(f"T{t_num:>3}: {bar} ({cnt})")
                lines.append("```")

        # Mentions (up to 20) — opt-in via show_mentions
        if show_mentions:
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

        # Notes GM — show_notes or pinned-only
        all_notes = _get_notes_for(conn, entity_id=eid)
        if show_notes:
            lines += _format_notes_section(all_notes)
        else:
            pinned = [n for n in all_notes if n.get("pinned")]
            lines += _format_notes_section(pinned)

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
                "SELECT e.id FROM entity_entities e WHERE e.canonical_name LIKE ? AND e.civ_id = ? AND e.disabled = 0",
                (pattern, civ_id),
            ).fetchall()
            by_alias = conn.execute(
                "SELECT a.entity_id AS id FROM entity_aliases a JOIN entity_entities e ON a.entity_id = e.id WHERE a.alias LIKE ? AND e.civ_id = ? AND e.disabled = 0",
                (pattern, civ_id),
            ).fetchall()
        else:
            by_name = conn.execute(
                "SELECT e.id FROM entity_entities e WHERE e.canonical_name LIKE ? AND e.disabled = 0",
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
            "SELECT canonical_name, entity_type FROM entity_entities WHERE civ_id = ? AND disabled = 0 ORDER BY entity_type, canonical_name LIMIT 200",
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

    # Verdict heuristique basé sur le taux de termes matchés.
    # Ne remplace pas l'interprétation de l'agent — indique juste si des preuves existent.
    matched_terms = sum(
        1 for term in search_terms
        if any(
            term.lower() in (e["name"] + " " + " ".join(e["aliases"])).lower()
            for e in matched_entities
        )
    )
    total_terms = len(search_terms)
    if not matched_entities:
        verdict = "⚠️ NO DATA — aucune entité correspondante en base"
    elif matched_terms == total_terms:
        verdict = "📋 PREUVES TROUVÉES — tous les termes matchent ; interpréter l'historique ci-dessous"
    else:
        verdict = f"📋 PREUVES PARTIELLES — {matched_terms}/{total_terms} termes matchés ; données incomplètes ou terminologie différente"

    # Build output
    lines = [
        "# Sanity Check",
        "",
        f'**Statement:** "{statement}"',
        f"**Context:** {civ_name or 'global'}",
        f"**Search terms extracted:** {', '.join(search_terms)}",
        f"**Verdict:** {verdict}",
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
    turn_type: str | None = None,
    from_turn: int | None = None,
    to_turn: int | None = None,
    last_n_turns: int | None = None,
    entity_name: str | None = None,
) -> str:
    """Chronological turn list with optional filters.

    Absorbs filterTimeline: supports turnType, fromTurn/toTurn/lastNTurns, entityName.
    """
    if entity_name:
        # Entity-filtered query: join through mentions
        sql = """
            SELECT DISTINCT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, t.game_date_end, c.name AS civ_name,
                   (SELECT COUNT(DISTINCT m2.entity_id) FROM entity_mentions m2 WHERE m2.turn_id = t.id) AS entity_count
            FROM turn_turns t
            JOIN civ_civilizations c ON t.civ_id = c.id
            LEFT JOIN entity_mentions m ON m.turn_id = t.id
            LEFT JOIN entity_entities e ON m.entity_id = e.id
            LEFT JOIN entity_aliases a ON a.entity_id = e.id
            WHERE (e.canonical_name LIKE ? ESCAPE '!' OR a.alias LIKE ? ESCAPE '!')
              AND (e.disabled IS NULL OR e.disabled = 0)
        """
        pattern = f"%{_escape_like(entity_name)}%"
        params: list = [pattern, pattern]
    else:
        sql = """
            SELECT t.turn_number, t.title, t.summary, t.turn_type,
                   t.game_date_start, t.game_date_end, c.name AS civ_name,
                   (SELECT COUNT(DISTINCT m.entity_id) FROM entity_mentions m WHERE m.turn_id = t.id) AS entity_count
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

    # Standard turn range filter
    turn_conds, turn_params = _turn_range_conditions(from_turn, to_turn, last_n_turns, conn, turn_alias="t")
    for cond in turn_conds:
        sql += f" AND {cond}"
    params.extend(turn_params)

    sql += " ORDER BY t.turn_number ASC, c.name LIMIT ?"
    params.append(limit + 1)

    rows = conn.execute(sql, params).fetchall()
    truncated = len(rows) > limit
    rows = rows[:limit]

    if not rows:
        return "# Timeline\n\nNo turns found."

    # Build title with active filters
    filter_parts = []
    if turn_type:
        filter_parts.append(f"type={turn_type}")
    if entity_name:
        filter_parts.append(f"entity={entity_name}")
    if last_n_turns is not None:
        filter_parts.append(f"last {last_n_turns} turns")
    elif from_turn is not None or to_turn is not None:
        f_str = str(from_turn) if from_turn is not None else "?"
        t_str = str(to_turn) if to_turn is not None else "?"
        filter_parts.append(f"turns {f_str}-{t_str}")
    filter_str = f" ({', '.join(filter_parts)})" if filter_parts else ""

    lines = [
        f"# Timeline{filter_str}",
        "",
        "| Turn | Civilization | Type | Summary | Entities |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        turn_num, title, summary, t_type, _gd_start, _gd_end, cn, ec = r
        text = truncate(summary or title or "(no summary)", 80)
        lines.append(f"| {turn_num} | {cn} | {t_type} | {text} | {ec} |")

    if truncated:
        lines.append(_truncation_notice(limit, "tours"))
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
    # diplomacy + religion are first-class domains in ENTITY_TAG_VOCAB (diplomatique,
    # religieux). Folding them into politics/culture meant the GM could not compare civs
    # on either one directly -- e.g. "qui a le plus d'alliances ?" got drowned in the
    # whole politics bucket. Kept as their own aspects, narrower keyword sets.
    "diplomacy": {
        "types": ["institution", "person", "civilization"],
        "keywords": ["diplomatie", "alliance", "traite", "ambassade", "delegation", "guerre", "paix", "conflit", "relation", "envoye"],
    },
    "religion": {
        "types": ["belief", "institution", "person"],
        "keywords": ["religion", "culte", "rituel", "croyance", "dieu", "divin", "sacre", "temple", "pretre", "oracle", "mythe", "esprit"],
    },
}


def compare_civs(
    conn: sqlite3.Connection,
    civs: list[dict],
    aspects: list[str] | None = None,
) -> str:
    if aspects:
        active_aspects = [a for a in aspects if a in ASPECT_ENTITY_MAP]
        if not active_aspects:
            valid = ", ".join(sorted(ASPECT_ENTITY_MAP.keys()))
            return f"Error: invalid aspect(s) {aspects!r}. Valid aspects: {valid}"
    else:
        active_aspects = list(ASPECT_ENTITY_MAP.keys())

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
            "SELECT entity_type, COUNT(*) FROM entity_entities WHERE civ_id = ? AND disabled = 0 GROUP BY entity_type ORDER BY COUNT(*) DESC",
            (cid,),
        ).fetchall()
        entity_breakdown = {r[0]: r[1] for r in breakdown_rows}

        # Top entities, optionally filtered
        entity_sql = """
            SELECT e.canonical_name AS name, e.entity_type AS type,
                   (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mentions
            FROM entity_entities e
            WHERE e.civ_id = ? AND e.disabled = 0
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
    from_turn: int | None = None,
    to_turn: int | None = None,
    last_n_turns: int | None = None,
    limit: int = 20,
) -> str:
    sql = """
        SELECT t.turn_number, c.name AS civ_name, s.segment_type, s.content, t.title
        FROM turn_segments s
        JOIN turn_turns t ON s.turn_id = t.id
        JOIN civ_civilizations c ON t.civ_id = c.id
        WHERE s.content LIKE ? ESCAPE '!'
    """
    params: list = [f"%{_escape_like(query)}%"]

    if civ_id is not None:
        sql += " AND t.civ_id = ?"
        params.append(civ_id)
    if segment_type:
        sql += " AND s.segment_type = ?"
        params.append(segment_type)

    turn_conds, turn_params = _turn_range_conditions(from_turn, to_turn, last_n_turns, conn, turn_alias="t")
    for cond in turn_conds:
        sql += f" AND {cond}"
    params.extend(turn_params)

    sql += " ORDER BY t.turn_number DESC LIMIT ?"
    params.append(limit + 1)
    rows = conn.execute(sql, params).fetchall()
    truncated = len(rows) > limit
    rows = rows[:limit]

    if not rows:
        return f'# Search: "{query}"\n\nNo matching content found.'

    lines = [f'# Search: "{query}"', "", f"**{len(rows)}** result(s).", ""]
    for r in rows:
        turn_num, cn, seg_type, content, title = r
        lines.append(f"### Turn {turn_num} ({cn}) [{seg_type}]")
        lines.append(truncate(content, 500))
        lines.append("")

    if truncated:
        lines.append(_truncation_notice(limit, "extraits"))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool 10: getStructuredFacts
# --------------------------------------------------------------------------- #

VALID_FACT_TYPES = {"technologies", "resources", "beliefs", "geography", "choices", "techtree"}


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
    from_turn: int | None = None,
    to_turn: int | None = None,
    last_n_turns: int | None = None,
    limit: int = 25,
) -> str:
    """Structured facts per turn.

    fact_type=choices delegates to get_choice_history (narrative bifurcations).
    fact_type=techtree delegates to get_tech_tree (categorized tech tree).
    fact_type=all skips choices and techtree (use explicitly for those).

    limit caps how many fact-bearing turns are emitted. WHY: on a real game (hundreds
    of turns) an uncapped 'all' dump floods the agent's context; capped + a truncation
    notice keeps it honest (see _truncation_notice) rather than silently partial.
    """
    if fact_type and fact_type not in VALID_FACT_TYPES and fact_type != "all":
        valid = ", ".join(sorted(VALID_FACT_TYPES) + ["all"])
        return f"# Structured Facts - {civ_name}\n\nError: invalid factType '{fact_type}'. Valid types: {valid}"

    # Delegate special fact types
    if fact_type == "choices":
        return get_choice_history(conn, civ_id, civ_name)
    if fact_type == "techtree":
        return get_tech_tree(conn, civ_id, civ_name)

    # Standard fact types (technologies, resources, beliefs, geography)
    db_fact_types = {"technologies", "resources", "beliefs", "geography"}
    types_to_query = [fact_type] if (fact_type and fact_type in db_fact_types) else sorted(db_fact_types)

    sql = "SELECT turn_number, technologies, resources, beliefs, geography FROM turn_turns WHERE civ_id = ?"
    params: list = [civ_id]

    turn_conds, turn_params = _turn_range_conditions(from_turn, to_turn, last_n_turns, conn, turn_alias="turn_turns")
    # Note: no alias in this query, use column directly
    if last_n_turns is not None:
        max_turn = conn.execute("SELECT MAX(turn_number) FROM turn_turns").fetchone()[0] or 0
        effective_from = max(1, max_turn - last_n_turns + 1)
        sql += " AND turn_number >= ?"
        params.append(effective_from)
    else:
        if from_turn is not None:
            sql += " AND turn_number >= ?"
            params.append(from_turn)
        if to_turn is not None:
            sql += " AND turn_number <= ?"
            params.append(to_turn)

    sql += " ORDER BY turn_number"
    rows = conn.execute(sql, params).fetchall()

    lines = [f"# Structured Facts - {civ_name}", ""]
    if fact_type and fact_type in (VALID_FACT_TYPES - {"choices", "techtree"}):
        lines.append(f"**Filter:** {fact_type}")
    lines.append("")

    # Collect fact-bearing turns FIRST so we can cap the emitted set and still report
    # the TRUE total. Emitting inside the loop made an honest total impossible.
    turns_with_facts: list[tuple[int, dict[str, list[str]]]] = []
    for row in rows:
        t_num = row[0]
        facts_for_turn: dict[str, list[str]] = {}
        col_map = {"technologies": row[1], "resources": row[2], "beliefs": row[3], "geography": row[4]}
        for ft in types_to_query:
            items = _parse_json_list(col_map.get(ft))
            if items:
                facts_for_turn[ft] = items
        if facts_for_turn:
            turns_with_facts.append((t_num, facts_for_turn))

    if not turns_with_facts:
        lines.append("No structured facts found for the given filters.")
        return "\n".join(lines)

    total = len(turns_with_facts)
    for t_num, facts_for_turn in turns_with_facts[:limit]:
        lines.append(f"## Turn {t_num}")
        lines.append("")
        for ft, items in facts_for_turn.items():
            lines.append(f"**{ft.capitalize()}:**")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    if total > limit:
        lines.append(_truncation_notice(limit, "tours", total))

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
        WHERE e.disabled = 0
          AND (e.canonical_name LIKE ? OR e.id IN (
            SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ?
        ))
    """
    pattern = f"%{_escape_like(entity_name)}%"
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
            WHERE (e.canonical_name LIKE ? ESCAPE '!' OR a.alias LIKE ? ESCAPE '!')
              AND (e.disabled IS NULL OR e.disabled = 0)
        """
        pattern = f"%{_escape_like(entity_name)}%"
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

# Tool schemas live in tool_definitions.py — edit there to tune descriptions.
from .tool_definitions import TOOL_DEFINITIONS  # noqa: F401  (re-exported)



_NIL_VALUES = {"<nil>", "nil", "null", "none", "None", "undefined"}


def list_subjects(
    conn: sqlite3.Connection,
    civ_id: int | None = None,
    status: str = "open",
    direction: str | None = None,
    tag: str | None = None,
    from_turn: int | None = None,
    to_turn: int | None = None,
    last_n_turns: int | None = None,
    limit: int = 50,
) -> str:
    """List subjects (MJ↔PJ open threads) with optional filters.

    Returns a Markdown table with subject id, title, category, direction,
    status, source turn, and tags.
    """
    import json as _json

    where: list[str] = []
    params: list = []

    if status and status != "all":
        where.append("s.status = ?")
        params.append(status)
    if civ_id is not None:
        where.append("s.civ_id = ?")
        params.append(civ_id)
    if direction:
        where.append("s.direction = ?")
        params.append(direction)
    if tag:
        # JSON array contains match: tags column stores ["militaire","..."]
        where.append('s.tags LIKE ?')
        params.append(f'%"{tag}"%')

    # Turn range filter on source turn
    turn_conds, turn_params = _turn_range_conditions(from_turn, to_turn, last_n_turns, conn, turn_alias="t")
    for cond in turn_conds:
        where.append(cond)
    params.extend(turn_params)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = conn.execute(
        f"""
        SELECT s.id, s.title, s.category, s.direction, s.status, s.tags,
               t.turn_number, c.name AS civ_name
        FROM subject_subjects s
        JOIN turn_turns t ON t.id = s.source_turn_id
        JOIN civ_civilizations c ON c.id = s.civ_id
        {where_sql}
        ORDER BY t.turn_number DESC, s.id DESC
        LIMIT ?
        """,
        params + [limit + 1],
    ).fetchall()
    truncated = len(rows) > limit
    rows = rows[:limit]
    total_subjects = conn.execute(
        "SELECT COUNT(*) FROM subject_subjects s "
        "JOIN turn_turns t ON t.id = s.source_turn_id "
        "JOIN civ_civilizations c ON c.id = s.civ_id " + where_sql,
        params,
    ).fetchone()[0]

    if not rows:
        label = f"statut={status}" + (f", tag={tag}" if tag else "")
        return f"Aucun sujet trouvé ({label})."

    dir_label = {"mj_to_pj": "MJ→PJ", "pj_to_mj": "PJ→MJ"}
    cat_label = {"choice": "Choix", "question": "Question", "initiative": "Initiative", "request": "Demande"}
    status_label = {"open": "🔴 Ouvert", "resolved": "✅ Résolu", "superseded": "Dépassé", "abandoned": "Abandonné"}

    lines = ["## Sujets\n"]
    lines.append("| # | Tour | Civ | Direction | Catégorie | Statut | Tags | Titre |")
    lines.append("|---|------|-----|-----------|-----------|--------|------|-------|")

    for row in rows:
        sid, title, category, direc, stat, tags_json, turn_num, civ_name = row
        tags = _json.loads(tags_json or "[]")
        tags_str = ", ".join(tags) if tags else "—"
        lines.append(
            f"| {sid} | T{turn_num} | {civ_name} "
            f"| {dir_label.get(direc, direc)} "
            f"| {cat_label.get(category, category)} "
            f"| {status_label.get(stat, stat)} "
            f"| {tags_str} "
            f"| {title} |"
        )

    total = len(rows)
    lines.append(f"\n_{total} sujet(s). Utiliser `getSubjectDetail(subjectId)` pour le détail d'un sujet._")
    if truncated:
        lines.append(_truncation_notice(limit, "sujets", total_subjects))
    return "\n".join(lines)


def get_subject_detail(
    conn: sqlite3.Connection,
    subject_id: int,
    show_options: bool = False,
    show_resolutions: bool = False,
    show_notes: bool = False,
) -> str:
    """Return full detail for a single subject: description, options, resolutions.

    Sections are opt-in to control verbosity. Pinned notes always shown.
    """
    import json as _json

    row = conn.execute(
        """
        SELECT s.id, s.title, s.description, s.category, s.direction, s.status,
               s.source_quote, s.tags, s.created_at,
               t.turn_number, c.name AS civ_name
        FROM subject_subjects s
        JOIN turn_turns t ON t.id = s.source_turn_id
        JOIN civ_civilizations c ON c.id = s.civ_id
        WHERE s.id = ?
        """,
        (subject_id,),
    ).fetchone()

    if not row:
        return f"Sujet #{subject_id} introuvable."

    sid, title, description, category, direction, status, source_quote, tags_json, created_at, turn_num, civ_name = row
    tags = _json.loads(tags_json or "[]")

    dir_label = {"mj_to_pj": "MJ→PJ (GM propose au joueur)", "pj_to_mj": "PJ→MJ (initiative du joueur)"}
    cat_label = {"choice": "Choix", "question": "Question", "initiative": "Initiative", "request": "Demande"}
    status_label = {"open": "🔴 Ouvert", "resolved": "✅ Résolu", "superseded": "Dépassé", "abandoned": "Abandonné"}

    lines = [
        f"## Sujet #{sid} — {title}",
        f"**Civ** : {civ_name} | **Tour** : T{turn_num} | **Direction** : {dir_label.get(direction, direction)}",
        f"**Catégorie** : {cat_label.get(category, category)} | **Statut** : {status_label.get(status, status)}",
    ]
    if tags:
        lines.append(f"**Tags** : {', '.join(tags)}")
    lines.append("")

    if description:
        lines.append(f"**Description** : {description}\n")

    if source_quote:
        lines.append(f"> _{source_quote}_\n")

    # Options — opt-in via show_options
    if show_options:
        options = conn.execute(
            "SELECT option_number, label, description, is_libre FROM subject_options WHERE subject_id = ? ORDER BY option_number",
            (subject_id,),
        ).fetchall()
        if options:
            lines.append("### Options proposées")
            for opt_num, label, opt_desc, is_libre in options:
                libre_tag = " *(libre)*" if is_libre else ""
                lines.append(f"{opt_num}. **{label}**{libre_tag}" + (f" — {opt_desc}" if opt_desc else ""))
            lines.append("")

    # Resolutions — opt-in via show_resolutions
    if show_resolutions:
        resolutions = conn.execute(
            """
            SELECT r.resolution_text, r.confidence, r.is_libre,
                   t.turn_number,
                   o.label AS chosen_option
            FROM subject_resolutions r
            JOIN turn_turns t ON t.id = r.resolved_by_turn_id
            LEFT JOIN subject_options o ON o.id = r.chosen_option_id
            WHERE r.subject_id = ?
            ORDER BY r.confidence DESC
            LIMIT 5
            """,
            (subject_id,),
        ).fetchall()
        if resolutions:
            lines.append("### Résolutions")
            for res_text, conf, is_libre, res_turn, chosen_opt in resolutions:
                conf_pct = f"{int(conf * 100)}%"
                opt_info = f" (option : {chosen_opt})" if chosen_opt else (" (libre)" if is_libre else "")
                lines.append(f"- T{res_turn} [{conf_pct}]{opt_info} : {truncate(res_text, 200)}")

    # Notes GM — show_notes or pinned-only
    all_notes = _get_notes_for(conn, subject_id=sid)
    if show_notes:
        lines += _format_notes_section(all_notes)
    else:
        pinned = [n for n in all_notes if n.get("pinned")]
        lines += _format_notes_section(pinned)

    return "\n".join(lines)


def get_entities_by_tag(
    conn: sqlite3.Connection,
    tag: str,
    civ_id: int | None = None,
    entity_type: str | None = None,
) -> str:
    """List all entities with a given domain tag (stored as JSON array in entity_entities.tags)."""
    import json as _json

    where = ['e.disabled = 0', 'e.tags LIKE ?']
    params: list = [f'%"{tag}"%']

    if civ_id is not None:
        where.append("e.civ_id = ?")
        params.append(civ_id)
    if entity_type:
        where.append("e.entity_type = ?")
        params.append(entity_type)

    rows = conn.execute(
        f"""
        SELECT e.id, e.canonical_name, e.entity_type, e.description,
               c.name AS civ_name,
               (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
        FROM entity_entities e
        LEFT JOIN civ_civilizations c ON c.id = e.civ_id
        WHERE {' AND '.join(where)}
        ORDER BY mention_count DESC
        LIMIT 50
        """,
        params,
    ).fetchall()

    if not rows:
        return f"Aucune entité trouvée avec le tag '{tag}'."

    lines = [f"## Entités — tag : {tag}\n"]
    lines.append("| Nom | Type | Civ | Mentions | Description |")
    lines.append("|-----|------|-----|----------|-------------|")

    for eid, name, etype, desc, civ_name, mentions in rows:
        desc_short = truncate(desc, 80) if desc else "—"
        civ_display = civ_name or "—"
        lines.append(f"| {name} | {etype} | {civ_display} | {mentions} | {desc_short} |")

    lines.append(f"\n_{len(rows)} entité(s) avec tag '{tag}'._")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Agent memory (self-authored from GM feedback) — write side
# --------------------------------------------------------------------------- #

def save_memory(
    conn: sqlite3.Connection,
    mem_key: str,
    content: str,
    description: str = "",
    civ_id: int | None = None,
    mem_type: str = "fact",
    keywords: str = "",
    source_turn: int | None = None,
) -> str:
    """Upsert an agent memory keyed by (mem_key, civ_id).

    WHY upsert: a memory is something the agent MAINTAINS — re-saving the same key
    (e.g. correcting a ruling) must UPDATE the row, not stack duplicates that would
    both surface at recall. `civ_id IS ?` matches the NULL (global) scope too.

    ``source_turn`` (a turn_id) anchors a fact "as of turn N": it is surfaced at
    recall so the agent reasons about whether newer pipeline data supersedes it.
    """
    mem_key = (mem_key or "").strip()
    content = (content or "").strip()
    if not mem_key or not content:
        return "Error: key and content are required."
    mem_type = mem_type if mem_type in ("fact", "preference") else "fact"

    existing = conn.execute(
        "SELECT id FROM agent_memory WHERE mem_key = ? AND civ_id IS ?",
        (mem_key, civ_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE agent_memory SET content = ?, description = ?, keywords = ?, "
            "mem_type = ?, source_turn = ?, active = 1, updated_at = datetime('now') WHERE id = ?",
            (content, description, keywords, mem_type, source_turn, existing[0]),
        )
        conn.commit()
        return f"Mémoire mise à jour : {mem_key}"

    conn.execute(
        "INSERT INTO agent_memory (mem_key, description, content, civ_id, keywords, mem_type, source_turn) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mem_key, description, content, civ_id, keywords, mem_type, source_turn),
    )
    conn.commit()
    return f"Mémoire enregistrée : {mem_key}"


#: Bound the number of links per memory so recall stays cheap.
_MAX_MEMORY_LINKS = 8


def _set_memory_links(
    conn: sqlite3.Connection,
    memory_id: int,
    specs: list,
    civ_id: int | None = None,
) -> None:
    """Replace a memory's links to database articles.

    ``specs`` are what the model writes: ``"entity:Argile Vivante"``, ``"turn:12"``,
    ``"subject:18"``. Entities resolve by canonical name then alias (the model knows
    names, not ids); turns resolve by (civ, turn_number) since turn numbers are per-civ;
    subjects are already numeric ids in the GM's vocabulary. Unresolvable specs are
    skipped rather than stored as dangling rows.
    """
    try:
        conn.execute("DELETE FROM agent_memory_links WHERE memory_id = ?", (memory_id,))
    except sqlite3.OperationalError:
        return  # table absent (pre-migration-040)

    for spec in specs[:_MAX_MEMORY_LINKS]:
        text = str(spec or "").strip()
        if ":" not in text:
            continue
        kind, _, value = text.partition(":")
        kind, value = kind.strip().lower(), value.strip()
        if not value:
            continue

        entity_id = subject_id = turn_id = None
        if kind == "entity":
            row = conn.execute(
                "SELECT id FROM entity_entities WHERE canonical_name = ? AND is_active = 1",
                (value,),
            ).fetchone() or conn.execute(
                "SELECT e.id FROM entity_entities e LEFT JOIN entity_aliases a ON a.entity_id = e.id "
                "WHERE (e.canonical_name LIKE ? OR a.alias LIKE ?) AND e.is_active = 1 LIMIT 1",
                (f"%{value}%", f"%{value}%"),
            ).fetchone()
            if row:
                entity_id = row[0]
        elif kind == "turn":
            try:
                row = conn.execute(
                    "SELECT id FROM turn_turns WHERE civ_id IS ? AND turn_number = ?",
                    (civ_id, int(value)),
                ).fetchone()
                if row:
                    turn_id = row[0]
            except (TypeError, ValueError):
                continue
        elif kind == "subject":
            try:
                row = conn.execute(
                    "SELECT id FROM subject_subjects WHERE id = ?", (int(value),)
                ).fetchone()
                if row:
                    subject_id = row[0]
            except (TypeError, ValueError):
                continue

        if entity_id is None and subject_id is None and turn_id is None:
            continue
        conn.execute(
            "INSERT INTO agent_memory_links (memory_id, entity_id, subject_id, turn_id) "
            "VALUES (?, ?, ?, ?)",
            (memory_id, entity_id, subject_id, turn_id),
        )
    conn.commit()


def discover_memory(
    conn: sqlite3.Connection,
    keys: list[str] | None = None,
    civ_id: int | None = None,
    mem_type: str | None = None,
    include_inactive: bool = False,
) -> str:
    """Read side of the agent's own memory — inventory, or full entries by key.

    WHY: recall is push-only (relevance-gated), so a memory it doesn't surface is
    invisible to the agent — it can neither answer "what do I already know?" nor look
    up the key of a memory it wants to correct. This is the pull counterpart.

    - without ``keys`` -> a COMPACT inventory (key, description, scope, anchor) with
      NO content, so listing everything stays cheap in tokens.
    - with ``keys``    -> the full entries for exactly those keys; keys that don't
      exist are reported explicitly rather than silently dropped.
    """
    where = []
    params: list = []
    if not include_inactive:
        where.append("m.active = 1")
    if civ_id is not None:
        where.append("m.civ_id = ?")
        params.append(civ_id)
    if mem_type:
        where.append("m.mem_type = ?")
        params.append(mem_type)
    if keys:
        where.append(f"m.mem_key IN ({','.join('?' * len(keys))})")
        params.extend(keys)

    sql = (
        "SELECT m.mem_key, m.description, m.content, m.mem_type, m.active, "
        "       c.name AS civ_name, t.turn_number "
        "FROM agent_memory m "
        "LEFT JOIN civ_civilizations c ON c.id = m.civ_id "
        "LEFT JOIN turn_turns t ON t.id = m.source_turn "
        + (" WHERE " + " AND ".join(where) if where else "")
        + " ORDER BY m.active DESC, m.updated_at DESC"
    )
    rows = conn.execute(sql, params).fetchall()

    def _scope(civ_name, turn_number, active) -> str:
        bits = [civ_name or "global"]
        if turn_number is not None:
            bits.append(f"dès T{turn_number}")
        if not active:
            bits.append("oubliée")
        return " · ".join(bits)

    if keys:
        found = {r[0] for r in rows}
        missing = [k for k in keys if k not in found]
        if not rows:
            return f"Aucune mémoire pour : {', '.join(f'`{k}`' for k in keys)}."
        out = [f"## Mémoire de l'agent — {len(rows)} entrée(s)", ""]
        for mem_key, description, content, m_type, active, civ_name, turn_number in rows:
            kind = "préférence" if m_type == "preference" else "fait"
            out.append(f"### `{mem_key}` ({kind} · {_scope(civ_name, turn_number, active)})")
            if description:
                out.append(f"**{description}**")
            out.append(content or "")
            out.append("")
        if missing:
            out.append(f"Introuvable(s) : {', '.join(f'`{k}`' for k in missing)}.")
        return "\n".join(out)

    if not rows:
        return "Aucune mémoire enregistrée."

    out = [f"## Mémoire de l'agent — inventaire ({len(rows)})", ""]
    for mem_key, description, _content, m_type, active, civ_name, turn_number in rows:
        kind = "préférence" if m_type == "preference" else "fait"
        label = description or "(sans description)"
        out.append(f"- `{mem_key}` — {label} · {kind} · {_scope(civ_name, turn_number, active)}")
    out.append("")
    out.append("Utilise `discoverMemory(keys=[...])` pour lire le contenu de ces mémoires.")
    return "\n".join(out)


def forget_memory(conn: sqlite3.Connection, mem_key: str, civ_id: int | None = None) -> str:
    """Deactivate an agent memory (kept for the review trail, not recalled)."""
    mem_key = (mem_key or "").strip()
    row = conn.execute(
        "SELECT id FROM agent_memory WHERE mem_key = ? AND civ_id IS ? AND active = 1",
        (mem_key, civ_id),
    ).fetchone()
    if not row:
        return f"Aucune mémoire active nommée '{mem_key}'."
    conn.execute(
        "UPDATE agent_memory SET active = 0, updated_at = datetime('now') WHERE id = ?",
        (row[0],),
    )
    conn.commit()
    return f"Mémoire oubliée : {mem_key}"


def _get_notes_for(
    conn: sqlite3.Connection,
    entity_id: int | None = None,
    subject_id: int | None = None,
    turn_id: int | None = None,
    civ_id: int | None = None,
    note_type: str = "gm",
) -> list[dict]:
    """Return notes attached to the given entity/subject/turn/civ.

    note_type filters by type ('gm' default, 'agent' for system prompt notes).
    """
    conditions, params = [], []
    if entity_id is not None:
        conditions.append("entity_id = ?")
        params.append(entity_id)
    if subject_id is not None:
        conditions.append("subject_id = ?")
        params.append(subject_id)
    if turn_id is not None:
        conditions.append("turn_id = ?")
        params.append(turn_id)
    if civ_id is not None:
        conditions.append("civ_id = ?")
        params.append(civ_id)
    if not conditions:
        return []
    where = " OR ".join(conditions)
    try:
        rows = conn.execute(
            f"""SELECT id, title, content, created_at,
                       COALESCE(pinned, 0) AS pinned
                FROM notes
                WHERE ({where})
                  AND COALESCE(note_type, 'gm') = ?
                ORDER BY pinned DESC, created_at DESC""",
            [*params, note_type],
        ).fetchall()
    except Exception:
        return []  # notes table may not exist on older DBs
    return [
        {"id": r[0], "title": r[1], "content": r[2], "created_at": r[3], "pinned": r[4]}
        for r in rows
    ]


def _format_notes_section(notes: list[dict]) -> list[str]:
    """Format notes as Markdown lines to append to any tool response.

    Pinned notes are prefixed with [IMPORTANT].
    """
    if not notes:
        return []
    lines = ["", "## Notes GM", ""]
    for n in notes:
        title = n["title"] or "(sans titre)"
        prefix = "[IMPORTANT] " if n.get("pinned") else ""
        lines.append(f"### {prefix}{title}")
        if n["content"]:
            lines.append(n["content"])
        lines.append(f"_Ajouté le {n['created_at'][:10]}_")
        lines.append("")
    return lines


def get_notes(
    conn: sqlite3.Connection,
    entity_name: str | None = None,
    subject_id: int | None = None,
    turn_number: int | None = None,
    civ_id: int | None = None,
) -> str:
    """Return all notes attached to an entity, subject, or turn."""
    lines: list[str] = []

    if entity_name:
        entities = _resolve_entity(conn, entity_name, civ_id)
        for ent in entities:
            notes = _get_notes_for(conn, entity_id=ent["id"])
            lines.append(f"# Notes — {ent['name']} ({ent['type']})")
            lines += _format_notes_section(notes) if notes else ["", "_Aucune note._"]
            lines.append("")

    if subject_id is not None:
        notes = _get_notes_for(conn, subject_id=subject_id)
        lines.append(f"# Notes — Sujet #{subject_id}")
        lines += _format_notes_section(notes) if notes else ["", "_Aucune note._"]

    if turn_number is not None:
        # Resolve turn_id
        where = "WHERE turn_number = ?"
        params: list = [turn_number]
        if civ_id is not None:
            where += " AND civ_id = ?"
            params.append(civ_id)
        turn_row = conn.execute(
            f"SELECT id, civ_id FROM turn_turns {where} LIMIT 1", params
        ).fetchone()
        if turn_row:
            notes = _get_notes_for(conn, turn_id=turn_row[0])
            lines.append(f"# Notes — Tour {turn_number}")
            lines += _format_notes_section(notes) if notes else ["", "_Aucune note._"]
        else:
            lines.append(f"Tour {turn_number} introuvable.")

    # Civ-level notes (when civName is provided but no entity/subject/turn)
    if civ_id is not None and not entity_name and subject_id is None and turn_number is None:
        notes = _get_notes_for(conn, civ_id=civ_id)
        civ_name = conn.execute(
            "SELECT name FROM civ_civilizations WHERE id = ?", [civ_id]
        ).fetchone()
        label = civ_name[0] if civ_name else f"Civ #{civ_id}"
        lines.append(f"# Notes — {label}")
        lines += _format_notes_section(notes) if notes else ["", "_Aucune note._"]

    if not lines:
        return "Préciser entityName, subjectId, turnNumber ou civName."

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool: getFavorites
# --------------------------------------------------------------------------- #

def get_favorites(
    conn: sqlite3.Connection,
    item_type: str | None = None,      # 'entity' | 'subject' | 'turn' | None = all
    civ_id: int | None = None,
    tag: str | None = None,
    status: str | None = None,         # subjects only: open|resolved|abandoned|superseded
    limit: int = 20,
) -> str:
    """Return GM-favorited entities, subjects, and/or turns as Markdown.

    Point d'entrée prioritaire pour localiser rapidement les éléments importants
    marqués par le MJ. Supporte le filtre par type, civ, tag domaine et statut sujet.
    """
    lines: list[str] = ["# Favoris du MJ\n"]
    types_to_query = [item_type] if item_type else ["entity", "subject", "turn"]
    found_any = False

    for t in types_to_query:
        rows = _query_favorites_type(conn, t, civ_id=civ_id, tag=tag, status=status, limit=limit)
        if rows:
            found_any = True
            lines.append(f"## {t.capitalize()}s ({len(rows)})\n")
            lines.extend(rows)
            lines.append("")

    if not found_any:
        return "Aucun favori enregistré." if not item_type else f"Aucun favori de type '{item_type}'."

    return "\n".join(lines)


def _query_favorites_type(
    conn: sqlite3.Connection,
    item_type: str,
    civ_id: int | None,
    tag: str | None,
    status: str | None,
    limit: int,
) -> list[str]:
    """Build per-type rows for get_favorites."""
    rows: list[str] = []

    if item_type == "entity":
        sql = """
            SELECT e.canonical_name, e.entity_type, e.description, c.name AS civ_name, e.tags
            FROM user_favorites f
            JOIN entity_entities e ON f.entity_id = e.id
            LEFT JOIN civ_civilizations c ON e.civ_id = c.id
            WHERE f.type = 'entity' AND (e.disabled IS NULL OR e.disabled = 0)
        """
        params: list = []
        if civ_id is not None:
            sql += " AND e.civ_id = ?"
            params.append(civ_id)
        if tag:
            sql += " AND e.tags LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " LIMIT ?"
        params.append(limit)

        for r in conn.execute(sql, params).fetchall():
            name, etype, desc, civ_name, _ = r
            line = f"- **{name}** ({etype})"
            if civ_name:
                line += f" — {civ_name}"
            if desc:
                line += f"\n  {truncate(desc, 120)}"
            rows.append(line)

    elif item_type == "subject":
        sql = """
            SELECT s.id, s.title, s.direction, s.status, s.category, c.name AS civ_name, s.tags
            FROM user_favorites f
            JOIN subject_subjects s ON f.subject_id = s.id
            LEFT JOIN civ_civilizations c ON s.civ_id = c.id
            WHERE f.type = 'subject'
        """
        params = []
        if civ_id is not None:
            sql += " AND s.civ_id = ?"
            params.append(civ_id)
        if status:
            sql += " AND s.status = ?"
            params.append(status)
        if tag:
            sql += " AND s.tags LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " LIMIT ?"
        params.append(limit)

        for r in conn.execute(sql, params).fetchall():
            sid, title, direction, stat, category, civ_name, _ = r
            direction_label = "MJ→PJ" if direction == "mj_to_pj" else "PJ→MJ"
            stat_emoji = {"open": "🔴", "resolved": "✅", "abandoned": "❌"}.get(stat, "⬜")
            line = f"- **{title}** [{direction_label}] {stat_emoji} {stat}"
            if civ_name:
                line += f" — {civ_name}"
            line += f" (sujet #{sid})"
            rows.append(line)

    elif item_type == "turn":
        sql = """
            SELECT t.id, t.turn_number, t.title, t.turn_type, c.name AS civ_name, t.summary
            FROM user_favorites f
            JOIN turn_turns t ON f.turn_id = t.id
            LEFT JOIN civ_civilizations c ON t.civ_id = c.id
            WHERE f.type = 'turn'
        """
        params = []
        if civ_id is not None:
            sql += " AND t.civ_id = ?"
            params.append(civ_id)
        sql += " ORDER BY t.turn_number LIMIT ?"
        params.append(limit)

        for r in conn.execute(sql, params).fetchall():
            _, turn_num, title, turn_type, civ_name, summary = r
            label = title or f"Tour {turn_num}"
            line = f"- **Tour {turn_num}** — {label} ({turn_type})"
            if civ_name:
                line += f" [{civ_name}]"
            if summary:
                line += f"\n  {truncate(summary, 120)}"
            rows.append(line)

    return rows


# --------------------------------------------------------------------------- #
# Sub-agent: deepExplore
# --------------------------------------------------------------------------- #

# Tools allowed for the sub-agent — read-only exploration subset
_DEEP_EXPLORE_TOOLS = {
    "searchLore", "getEntityDetail", "getSubjectDetail",
    "timeline", "getTurnDetail", "searchTurnContent",
    "listSubjects", "getNotes", "listCivs",
}

_DEEP_EXPLORE_SYSTEM = """\
Tu es un sous-agent de recherche pour Aurelm. Ta mission est de repondre a une question \
en utilisant les outils de la base de donnees du JDR. Enchaine les recherches necessaires \
(searchLore -> getEntityDetail, timeline -> getTurnDetail, etc.) pour construire une \
reponse complete et sourcee. Cite toujours les tours et entites sources. Reponds en francais.

IMPORTANT: Tu as un nombre limite d'appels outils. Sois efficace -- ne demande que ce qui \
est strictement necessaire. Des que tu as assez d'info, reponds immediatement sans \
faire d'appels supplementaires. Privilegle searchLore (apercu) avant getEntityDetail (detail)."""


def _estimate_tokens(messages: list) -> int:
    """Rough token estimate for the sub-agent conversation (~4 chars per token)."""
    total = 0
    for msg in messages:
        if isinstance(msg.get("content"), str):
            total += len(msg["content"]) // 4
        elif isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict):
                    # tool_result or text block
                    text = block.get("content") or block.get("text") or ""
                    total += len(text) // 4
                elif hasattr(block, "text"):
                    total += len(block.text) // 4
    return total


# Budget tokens max pour le sous-agent (au-dela, on injecte un message de conclusion)
_DEEP_EXPLORE_TOKEN_BUDGET = 60_000


def _collected_findings(messages: list) -> str:
    """What the sub-agent actually gathered, for when it will not write a conclusion.

    WHY: returning a bare "no answer" throws away real research the GM paid for (in
    time and tokens). An unpolished digest of the tool results is far more useful than
    nothing, and it makes the failure visible instead of silent.
    """
    chunks = [m.get("content") or "" for m in messages if m.get("role") == "tool"]
    chunks = [c.strip() for c in chunks if c.strip()]
    if not chunks:
        return "(Pas de reponse du sous-agent.)"
    body = "\n\n".join(chunks[-6:])
    header = ("(Le sous-agent n'a pas redige de conclusion - voici ce qu'il a "
              "collecte, brut.)\n\n")
    return (header + body)[:6000]


# --------------------------------------------------------------------------- #
# Tool: getCivRelations
# --------------------------------------------------------------------------- #

def get_civ_relations(
    conn: sqlite3.Connection,
    civ_name: str,
) -> str:
    """Return the inter-civ relationship profile for a given civilization.

    Shows the civ's unilateral opinion of each other civ it has encountered
    (opinion + narrative description + treaties), plus the inverse view where
    available (how other civs see it).
    """
    result = resolve_civ_name(conn, civ_name)
    if "error" in result:
        return result["error"]
    civ = result["civ"]
    civ_id = civ["id"]

    rows = conn.execute(
        """SELECT r.opinion, r.description, r.treaties,
                  ca.name AS source_name, cb.name AS target_name,
                  r.source_civ_id, r.target_civ_id,
                  t.turn_number AS last_turn
           FROM civ_relations r
           JOIN civ_civilizations ca ON ca.id = r.source_civ_id
           JOIN civ_civilizations cb ON cb.id = r.target_civ_id
           LEFT JOIN turn_turns t ON t.id = r.last_turn_id
           WHERE r.source_civ_id = ? OR r.target_civ_id = ?
           ORDER BY r.updated_at DESC""",
        (civ_id, civ_id),
    ).fetchall()

    # Also count raw mentions per pair for context richness indicator
    mention_counts = {}
    mc_rows = conn.execute(
        """SELECT target_civ_id, COUNT(*) as cnt
           FROM civ_mentions WHERE source_civ_id = ?
           GROUP BY target_civ_id""",
        (civ_id,),
    ).fetchall()
    for mc in mc_rows:
        mention_counts[mc["target_civ_id"]] = mc["cnt"]

    if not rows:
        # Check if there are raw mentions at all (not yet profiled)
        raw = conn.execute(
            "SELECT COUNT(*) FROM civ_mentions WHERE source_civ_id = ?", (civ_id,)
        ).fetchone()[0]
        if raw:
            return (
                f"# Relations de {civ['name']}\n\n"
                f"{raw} mention(s) inter-civ détectée(s) mais le profiling n'a pas encore été lancé.\n"
                "Relancez le pipeline avec `--use-llm` pour générer les profils."
            )
        return f"# Relations de {civ['name']}\n\nAucune relation inter-civ enregistrée."

    _opinion_labels = {
        "allied":     "🤝 Allié",
        "friendly":   "😊 Favorable",
        "neutral":    "😐 Neutre",
        "suspicious": "👁️ Méfiant",
        "hostile":    "💀 Hostile",
        "unknown":    "❓ Inconnu",
    }

    outgoing = [r for r in rows if r["source_civ_id"] == civ_id]
    incoming = [r for r in rows if r["target_civ_id"] == civ_id]

    lines = [f"# Relations de {civ['name']}", ""]

    if outgoing:
        lines.append(f"## Vision de {civ['name']} envers les autres\n")
        for r in outgoing:
            label = _opinion_labels.get(r["opinion"], r["opinion"])
            mc = mention_counts.get(r["target_civ_id"], 0)
            lines.append(f"### {r['target_name']} — {label}")
            if mc:
                lines.append(f"*{mc} mention(s) dans les tours*")
            if r["description"]:
                lines.append(r["description"])
            if r["treaties"]:
                try:
                    treaties = json.loads(r["treaties"])
                    if treaties:
                        lines.append("\n**Accords/Traités :**")
                        for t in treaties:
                            lines.append(f"- {t}")
                except (json.JSONDecodeError, TypeError):
                    pass
            if r["last_turn"]:
                lines.append(f"\n*Dernière mise à jour : Tour {r['last_turn']}*")
            lines.append("")

    if incoming:
        lines.append(f"## Regard des autres civs sur {civ['name']}\n")
        for r in incoming:
            label = _opinion_labels.get(r["opinion"], r["opinion"])
            lines.append(f"### {r['source_name']} → {label}")
            if r["description"]:
                desc = r["description"]
                lines.append(desc[:300] + "..." if len(desc) > 300 else desc)
            lines.append("")

    return "\n".join(lines)


def deep_explore(
    conn: sqlite3.Connection,
    question: str,
    context: str | None = None,
    db_path: str | None = None,
    llm_client=None,
    model: str = "claude-opus-4-8",
    proxy: str | None = None,
) -> str:
    """Sub-agent that chains multiple tool calls to answer a complex question.

    No round limit — runs until it finishes or the ~60k token budget is exhausted.
    Uses the etheryale proxy (OpenAI Chat Completions) via `llm_client` (a SYNC
    OpenAI client — this runs inside a worker thread). No client → single
    searchLore fallback.
    """
    # Sub-agent tool subset, in OpenAI function format (the proxy translates for Claude).
    from .tool_definitions import TOOL_DEFINITIONS
    sub_tools = [
        {"type": "function", "function": {
            "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
        }}
        for t in TOOL_DEFINITIONS
        if t["name"] in _DEEP_EXPLORE_TOOLS
    ]

    user_msg = question
    if context:
        user_msg = f"{question}\n\nContexte: {context}"

    if llm_client is None:
        return "(deepExplore sans backend LLM -- reponse directe)\n\n" + dispatch_tool(
            conn, "searchLore", {"query": question}
        )

    messages = [
        {"role": "system", "content": _DEEP_EXPLORE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
    budget_warning_sent = False
    conclude_attempts = 0

    while True:
        # Budget check before each call — force a conclusion when near the limit.
        if _estimate_tokens(messages) > _DEEP_EXPLORE_TOKEN_BUDGET and not budget_warning_sent:
            messages.append({"role": "system", "content":
                "[SYSTEME] Budget tokens presque epuise. Conclus ta recherche "
                "MAINTENANT avec les infos collectees. Ne lance plus d'outils."})
            budget_warning_sent = True

        resp = llm_client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=messages,
            tools=sub_tools,
        )
        msg = resp.choices[0].message

        # Past the budget warning the model often answers with ANOTHER tool call and no
        # prose. Falling through to the return below would discard every result gathered
        # so far -- and that happens exactly when the research was long. Nudge it once
        # for a written conclusion, then fall back to the findings themselves.
        if msg.tool_calls and budget_warning_sent and not msg.content:
            if conclude_attempts < 1:
                conclude_attempts += 1
                messages.append({"role": "system", "content":
                    "[SYSTEME] Plus aucun outil. Redige MAINTENANT ta conclusion en texte, "
                    "a partir des resultats deja collectes."})
                continue
            return _collected_findings(messages)

        if msg.tool_calls and not budget_warning_sent:
            messages.append({
                "role": "assistant",
                "content": msg.content or None,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                tool_conn = sqlite3.connect(db_path) if db_path else conn
                try:
                    tool_conn.execute("PRAGMA foreign_keys = ON")
                    result = dispatch_tool(tool_conn, tc.function.name, json.loads(tc.function.arguments or "{}"))
                except Exception as exc:
                    result = f"Error: {exc}"
                finally:
                    if db_path and tool_conn is not conn:
                        tool_conn.close()
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue

        return msg.content or _collected_findings(messages)


# --------------------------------------------------------------------------- #
# Map system tools (migration 031)
# --------------------------------------------------------------------------- #

def resolve_map_name(conn: sqlite3.Connection, name: str) -> dict | None:
    """Fuzzy-match a map name. Returns {'id': int, 'name': str} or None if not found."""
    row = conn.execute("SELECT id, name FROM map_maps WHERE name = ?", (name,)).fetchone()
    if row:
        return {"id": row[0], "name": row[1]}
    rows = conn.execute(
        "SELECT id, name FROM map_maps WHERE name LIKE ?", (f"%{name}%",)
    ).fetchall()
    if len(rows) == 1:
        return {"id": rows[0][0], "name": rows[0][1]}
    return None


def get_maps(conn: sqlite3.Connection) -> str:
    """List all maps with indented hierarchy (root maps first, children indented)."""
    rows = conn.execute(
        """SELECT id, name, grid_type, grid_cols, grid_rows, parent_map_id
           FROM map_maps ORDER BY parent_map_id NULLS FIRST, name"""
    ).fetchall()
    if not rows:
        return "Aucune carte enregistrée."

    # Build parent→children index
    children: dict[int | None, list] = {}
    for r in rows:
        parent = r[5]
        children.setdefault(parent, []).append(r)

    lines = ["# Cartes\n"]

    def _render(parent_id: int | None, indent: str) -> None:
        for r in children.get(parent_id, []):
            lines.append(
                f"{indent}- **{r[1]}** (id={r[0]}, {r[2]}, {r[3]}×{r[4]})"
            )
            _render(r[0], indent + "  ")

    _render(None, "")
    return "\n".join(lines)


def get_map_overview(
    conn: sqlite3.Connection, map_id: int, map_name: str
) -> str:
    """Semantic SUMMARY of a map — not a cell dump.

    A real ingested world is thousands of provinces; a 200-row table is useless to an
    LLM. Instead we aggregate: size/scale, dominant terrains and biomes, resources and
    notable features present, the civs and their footprint, named places, and recent
    chronicle events. Geometry stays hidden; the summary is what a GM needs at a glance.
    """
    mrow = conn.execute(
        "SELECT grid_type, grid_cols, grid_rows, metadata FROM map_maps WHERE id = ?",
        (map_id,)).fetchone()
    grid_type, cols, grows, meta_json = (mrow or ("hex", 0, 0, None))
    mmeta = json.loads(meta_json) if meta_json else {}
    total = conn.execute(
        "SELECT COUNT(*) FROM map_cells WHERE map_id = ?", (map_id,)).fetchone()[0]

    lines = [f"# Carte : {map_name}", f"{grid_type} {cols}×{grows} — {total} provinces"]
    if mmeta.get("cell_km"):
        scale = f"Échelle : {mmeta['cell_km']} km/province"
        if mmeta.get("seed") is not None:
            scale += f" · seed {mmeta['seed']}"
        lines.append(scale)
    if total == 0:
        lines.append("\n*(aucune cellule)*")
        return "\n".join(lines)

    terr = conn.execute(
        "SELECT terrain_type, COUNT(*) c FROM map_cells WHERE map_id = ? "
        "GROUP BY terrain_type ORDER BY c DESC", (map_id,)).fetchall()
    lines += ["", "## Terrains"] + [f"- {t} : {c}" for t, c in terr[:12]]

    # Aggregate the semantic metadata (biomes + the point-budget element set) in one
    # pass: elements by family (deposit/landmark/constraint) for the big picture, and
    # by display_name for the notable ones present.
    biomes: dict = {}
    elem_family: dict = {}
    elem_name: dict = {}
    for (mj,) in conn.execute(
        "SELECT metadata FROM map_cells WHERE map_id = ? AND metadata IS NOT NULL", (map_id,)):
        m = json.loads(mj)
        if m.get("biome"):
            biomes[m["biome"]] = biomes.get(m["biome"], 0) + 1
        for e in (m.get("elements") or []):
            fam = e.get("family")
            if fam:
                elem_family[fam] = elem_family.get(fam, 0) + 1
            nm = e.get("display_name") or e.get("name")
            if nm:
                elem_name[nm] = elem_name.get(nm, 0) + 1

    def _top(d, n):
        return sorted(d.items(), key=lambda kv: -kv[1])[:n]

    if biomes:
        lines += ["", "## Biomes"] + [f"- {b} : {c}" for b, c in _top(biomes, 12)]
    if elem_family:
        lines += ["", "## Éléments (par famille)"] + [f"- {k} : {v}" for k, v in _top(elem_family, 10)]
    if elem_name:
        lines += ["", "## Éléments notables"] + [f"- {k} ({v})" for k, v in _top(elem_name, 20)]

    civs = conn.execute(
        "SELECT c.name, COUNT(*) n FROM map_cells mc "
        "JOIN civ_civilizations c ON c.id = mc.controlling_civ_id "
        "WHERE mc.map_id = ? GROUP BY c.id ORDER BY n DESC", (map_id,)).fetchall()
    if civs:
        lines += ["", "## Civilisations présentes"] + [f"- {n} : {cnt} province(s)" for n, cnt in civs]

    named = conn.execute(
        "SELECT label FROM map_cells WHERE map_id = ? AND label IS NOT NULL "
        "ORDER BY r, q LIMIT 20", (map_id,)).fetchall()
    if named:
        lines += ["", "## Lieux nommés"] + [f"- {lbl[0]}" for lbl in named]

    events = conn.execute(
        "SELECT event_type, description, created_at FROM map_cell_events "
        "WHERE map_id = ? ORDER BY created_at DESC, id DESC LIMIT 8", (map_id,)).fetchall()
    if events:
        lines += ["", "## Événements récents"]
        lines += [f"- [{t}] {d}  _{ca[:10]}_" for t, d, ca in events]

    return "\n".join(lines)


def get_cell(conn: sqlite3.Connection, map_id: int, q: int, r: int) -> str:
    """Detail of a single cell + last 3 events."""
    cell = conn.execute(
        """SELECT mc.terrain_type, mc.label, mc.metadata,
                  c.name AS civ_name, e.canonical_name AS entity_name,
                  cm.name AS child_map_name
           FROM map_cells mc
           LEFT JOIN civ_civilizations c ON c.id = mc.controlling_civ_id
           LEFT JOIN entity_entities e ON e.id = mc.entity_id
           LEFT JOIN map_maps cm ON cm.id = mc.child_map_id
           WHERE mc.map_id = ? AND mc.q = ? AND mc.r = ?""",
        (map_id, q, r),
    ).fetchone()

    if not cell:
        return f"Cellule ({q},{r}) non trouvée dans cette carte."

    lines = [
        f"# Cellule ({q},{r})\n",
        f"**Terrain** : {cell[0]}",
        f"**Label** : {cell[1] or '(none)'}",
        f"**Civ contrôlante** : {cell[3] or '(aucune)'}",
        f"**Entité liée** : {cell[4] or '(aucune)'}",
        f"**Carte enfant** : {cell[5] or '(aucune)'}",
    ]
    if cell[2]:
        lines.append(f"**Metadata** : {truncate(cell[2], 200)}")

    events = conn.execute(
        """SELECT event_type, description, created_at
           FROM map_cell_events WHERE map_id=? AND q=? AND r=?
           ORDER BY created_at DESC LIMIT 3""",
        (map_id, q, r),
    ).fetchall()
    lines.append("\n## Derniers événements")
    for ev in events:
        lines.append(f"- [{ev[0]}] {ev[1]}  _{ev[2][:10]}_")
    if not events:
        lines.append("*(aucun événement)*")

    return "\n".join(lines)


def get_cell_history(
    conn: sqlite3.Connection, map_id: int, q: int, r: int, limit: int = 20
) -> str:
    """Full event history for a cell."""
    events = conn.execute(
        """SELECT mce.event_type, mce.description, mce.created_at,
                  t.turn_number
           FROM map_cell_events mce
           LEFT JOIN turn_turns t ON t.id = mce.turn_id
           WHERE mce.map_id=? AND mce.q=? AND mce.r=?
           ORDER BY mce.created_at DESC
           LIMIT ?""",
        (map_id, q, r, limit),
    ).fetchall()

    if not events:
        return f"Aucun événement pour la cellule ({q},{r})."

    lines = [f"# Historique cellule ({q},{r})\n"]
    for ev in events:
        turn_str = f" (tour {ev[3]})" if ev[3] else ""
        lines.append(f"- [{ev[0]}]{turn_str} {ev[1]}  _{ev[2][:10]}_")
    return "\n".join(lines)


def get_territory(
    conn: sqlite3.Connection, civ_id: int, civ_name: str
) -> str:
    """All cells controlled by a civ, grouped by map."""
    rows = conn.execute(
        """SELECT m.name, mc.q, mc.r, mc.terrain_type, mc.label
           FROM map_cells mc
           JOIN map_maps m ON m.id = mc.map_id
           WHERE mc.controlling_civ_id = ?
           ORDER BY m.name, mc.r, mc.q""",
        (civ_id,),
    ).fetchall()

    if not rows:
        return f"**{civ_name}** ne contrôle aucune cellule sur les cartes."

    lines = [f"# Territoire — {civ_name}\n"]
    current_map = None
    for r in rows:
        if r[0] != current_map:
            current_map = r[0]
            lines.append(f"\n## {current_map}")
        label = f" — {r[4]}" if r[4] else ""
        lines.append(f"- ({r[1]},{r[2]}) {r[3]}{label}")
    return "\n".join(lines)


def find_entity_on_map(conn: sqlite3.Connection, entity_name: str) -> str:
    """Search for an entity on maps via entity_id or entity_aliases."""
    # Try direct name match + alias match to get entity ids
    entity_rows = conn.execute(
        """SELECT DISTINCT e.id, e.canonical_name
           FROM entity_entities e
           LEFT JOIN entity_aliases ea ON ea.entity_id = e.id
           WHERE e.canonical_name LIKE ? OR ea.alias LIKE ?
             AND e.disabled = 0""",
        (f"%{entity_name}%", f"%{entity_name}%"),
    ).fetchall()

    if not entity_rows:
        return f"Entité « {entity_name} » introuvable."

    entity_ids = [r[0] for r in entity_rows]
    placeholders = ",".join("?" * len(entity_ids))
    cells = conn.execute(
        f"""SELECT m.name, mc.q, mc.r, mc.terrain_type, mc.label, e.canonical_name
            FROM map_cells mc
            JOIN map_maps m ON m.id = mc.map_id
            JOIN entity_entities e ON e.id = mc.entity_id
            WHERE mc.entity_id IN ({placeholders})
            ORDER BY m.name""",
        entity_ids,
    ).fetchall()

    if not cells:
        names = ", ".join(r[1] for r in entity_rows)
        return f"Entité(s) trouvée(s) ({names}) mais non placée(s) sur une carte."

    lines = [f"# Localisation — {entity_name}\n"]
    for c in cells:
        label = f" — {c[4]}" if c[4] else ""
        lines.append(f"- **{c[0]}** ({c[1]},{c[2]}) {c[3]}{label}  [{c[5]}]")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tool: groundCivTerrain — structured local terrain around a civ (grounding)
# --------------------------------------------------------------------------- #

def _describe_province(terrain: str, meta: dict, max_hidden: int | None = None) -> str:
    """One readable line per province, from the ingested Theomen metadata.

    This is the GM-facing grounding: terrain + biome + elevation, water regime, the
    point-budget element SET (deposits/landmarks/constraints with signed points),
    dominant resource potential, and whether the province is a notable place. Only
    what's present is shown.

    max_hidden (feature-discover gating): elements carry a `hidden_level` (0=surface,
    >0=must prospect). None = show every element (omniscient callers: find_nearest,
    events…). An int = show only elements at or below that prospecting depth; deeper
    ones are counted as "à prospecter", never named — the civ knows something is there,
    not what. Aurelm doesn't model tech-level; the consumer (Demiurgos) passes the
    civ's current prospecting depth per its tech.
    """
    parts: list[str] = [terrain]
    if meta.get("biome"):
        parts.append(f"biome {meta['biome']}")
    if meta.get("elevation_m") is not None:
        parts.append(f"{meta['elevation_m']:.0f} m")
    if meta.get("temperature_c") is not None:
        parts.append(f"{meta['temperature_c']:.0f}°C")
    seg = [", ".join(parts)]

    w = meta.get("water", {})
    if w.get("is_river"):
        km2 = w.get("river_catchment_km2")
        seg.append(f"fleuve (bassin {km2:,} km²)".replace(",", " ") if km2 else "fleuve")
    if w.get("is_lake"):
        seg.append(f"lac {w.get('lake_depth_m', '')} m".strip())
    if w.get("is_ocean"):
        seg.append("océan")

    els = meta.get("elements") or []
    if els:
        # The point-budget SET that composes this province (Theomen v2 — replaces the
        # old single deposit + single feature). Facts + labels only, never prose
        # (Theomen ships none); the signed points show boon vs hazard so the GM reads
        # "Uranium (+5), Contamination (−2), Steep Slopes (−2)" and writes the scene.
        # Feature-discover gating: split visible (hidden_level<=max_hidden) from the
        # deeper elements that require prospecting (only counted, never named).
        if max_hidden is None:
            shown, hidden_count = els, 0
        else:
            shown = [e for e in els if (e.get("hidden_level") or 0) <= max_hidden]
            hidden_count = len(els) - len(shown)

        def _tag(e: dict) -> str:
            nm = e.get("display_name") or e.get("name", "?")
            p = e.get("points")
            return f"{nm} ({p:+d})" if isinstance(p, int) and p else nm
        if shown:
            seg.append("éléments : " + ", ".join(_tag(e) for e in shown))
        if hidden_count:
            n = "1 élément à prospecter" if hidden_count == 1 else f"{hidden_count} éléments à prospecter"
            seg.append(n)
    pot = meta.get("resource_potential")
    if pot:
        seg.append(f"potentiel {', '.join(pot)}")

    b = meta.get("budget_score")
    if isinstance(b, int) and b >= 5:
        seg.append("lieu notable")
    return " ; ".join(seg)


def ground_civ_terrain(conn: sqlite3.Connection, civ_id: int, civ_name: str,
                       radius: int = 2, fog: bool = True,
                       max_hidden_level: int = 0) -> str:
    """Structured local terrain around a civ's seat(s) — the Demiurgos GM grounding.

    Finds where the civ is placed (controlling_civ_id), then walks the ring of
    provinces within `radius` (Chebyshev) that exist on the ingested map. One cell =
    one 20 km province, so this is empire/region-scale geography, never local terrain.
    Crops have hard edges: neighbours outside the ingested window simply don't appear.

    fog (default True): the master omniscience switch. True = reveal only provinces the
    civ has DISCOVERED (spatial fog — a neolithic civ at turn 0 knows its cradle) AND
    gate each shown province's CONTENTS by prospecting depth (feature-discover). The
    seat is always shown; undiscovered in-radius provinces are counted, not described.
    fog=False = GM omniscience (all provinces, all contents).

    max_hidden_level (default 0 = surface only, used only when fog=True): the civ's
    prospecting depth. Elements with a higher hidden_level are counted as "à prospecter"
    but never named — the civ senses something without knowing what. Aurelm has no
    tech model; Demiurgos passes the depth its tech unlocks.
    """
    seats = conn.execute(
        "SELECT m.id, m.name, mc.q, mc.r FROM map_cells mc "
        "JOIN map_maps m ON m.id = mc.map_id "
        "WHERE mc.controlling_civ_id = ? ORDER BY m.name, mc.r, mc.q",
        (civ_id,),
    ).fetchall()
    if not seats:
        return (f"**{civ_name}** n'a pas de position sur une carte. "
                "Place-la d'abord (proposeSpawnPositions / foundSettlement).")

    # fog is the omniscience master: off → see every province AND every element.
    describe_max = None if not fog else max_hidden_level
    lines = [f"# Terrain local — {civ_name}", ""]
    for map_id, map_name, sq, sr in seats:
        known = discovered_set(conn, map_id, civ_id) if fog else None
        lines.append(f"## {map_name} — voisinage du siège")
        rows = conn.execute(
            "SELECT q, r, terrain_type, metadata FROM map_cells "
            "WHERE map_id = ? AND q BETWEEN ? AND ? AND r BETWEEN ? AND ? "
            "ORDER BY r, q",
            (map_id, sq - radius, sq + radius, sr - radius, sr + radius),
        ).fetchall()
        unknown = 0
        for q, r, terrain, meta_json in rows:
            dist = max(abs(q - sq), abs(r - sr))
            # Fog: the seat is always known; other provinces only if discovered.
            if fog and dist != 0 and (q, r) not in known:
                unknown += 1
                continue
            meta = json.loads(meta_json) if meta_json else {}
            if dist == 0:
                head = "**(siège)**"
            else:
                prov = "province" if dist == 1 else "provinces"  # never (q,r) (§design)
                head = f"{_direction(sq, sr, q, r)} à {dist} {prov}"
            lines.append(f"- {head} : {_describe_province(terrain, meta, max_hidden=describe_max)}")
        if unknown:
            prov = "province" if unknown == 1 else "provinces"
            lines.append(f"- _{unknown} {prov} voisine(s) encore inexplorée(s)._")
        lines.append("")
    return "\n".join(lines).rstrip()


def discover_around(conn: sqlite3.Connection, civ_id: int, civ_name: str,
                    map_name: str, around, radius: int = 1) -> str:
    """A civ explores: mark the disk of provinces around an anchor as discovered.

    `around` is a semantic place (feature/entity/spawn) or empty → the civ's seat. This
    is how fog lifts over time (the GM/turn drives exploration). Echoes the newly-seen
    provinces as facts. A WRITE (turn-atomic).
    """
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved

    origin = None
    if around and str(around).strip():
        try:
            origin = _resolve_anchor(conn, map_id, map_name, around)
        except ValueError:
            origin = None
    if origin is None:
        origin = _civ_seat(conn, map_id, civ_id)
    if origin is None:
        return (f"{civ_name} n'a pas de point de départ sur {map_name} — "
                "fonde une cité ou nomme un lieu à explorer.")

    oq, orr = origin
    before = discovered_set(conn, map_id, civ_id)
    discover(conn, map_id, civ_id,
             [(oq + dq, orr + dr) for dq in range(-radius, radius + 1)
              for dr in range(-radius, radius + 1)])
    _maybe_commit(conn)
    new = discovered_set(conn, map_id, civ_id) - before
    if not new:
        return f"{civ_name} explore mais ne découvre rien de nouveau (déjà connu)."

    lines = [f"✓ {civ_name} explore et découvre {len(new)} nouvelle(s) province(s) :"]
    for q, r in sorted(new, key=lambda c: (c[1], c[0])):
        row = conn.execute(
            "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
            (map_id, q, r)).fetchone()
        meta = json.loads(row[1]) if row and row[1] else {}
        lines.append(f"- {_direction(oq, orr, q, r)} : "
                     f"{_describe_province(row[0] if row else '?', meta)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Turn transactionality — atomicity with Demiurgos's shadow-DB turn (option A)
# --------------------------------------------------------------------------- #
#
# WHY: Demiurgos runs a turn on a shadow copy of ITS DB, committed only at end-of-turn.
# Aurelm is a separate DB written in-process DURING the turn. Without this, a
# foundSettlement mid-turn survives even if the turn rolls back -> orphan canon.
#
# HOW: within a turn, map writes accumulate in the connection's open SQLite
# transaction but do NOT commit (they ARE visible to subsequent reads/writes on the
# SAME connection, so dependent actions and the echo work). commit_turn commits the
# lot; abort_turn rolls it back, so nothing orphans.
#
# CONNECTION CONTRACT (agreed with Demiurgos, in-process Python): the caller holds ONE
# Aurelm connection per turn, in the turn's thread, and routes EVERY call of the turn
# (reads and writes) through it. begin_turn/commit_turn/abort_turn are importable
# callables (orchestration, not LLM tools). Tools accept the passed connection and
# never open their own; writes never auto-commit inside a turn.
#
# Keyed by id(conn): sqlite3.Connection is not weakref-able, so no WeakSet. Demiurgos's
# turn-runner always commits/aborts in lockstep, so the id is cleaned every turn (a
# stale id would only linger if a turn were abandoned without commit_turn/abort_turn).
_TURN_CONNS: set[int] = set()


def _in_turn(conn: sqlite3.Connection) -> bool:
    return id(conn) in _TURN_CONNS


def _maybe_commit(conn: sqlite3.Connection) -> None:
    """Commit now, UNLESS a turn is open — then defer to commit_turn/abort_turn."""
    if not _in_turn(conn):
        conn.commit()


def begin_turn(conn: sqlite3.Connection) -> str:
    _TURN_CONNS.add(id(conn))
    return "Tour ouvert — les écritures carte sont différées jusqu'à commitTurn/abortTurn."


def commit_turn(conn: sqlite3.Connection) -> str:
    conn.commit()
    _TURN_CONNS.discard(id(conn))
    return "Tour validé — écritures carte appliquées au canon."


def abort_turn(conn: sqlite3.Connection) -> str:
    conn.rollback()
    _TURN_CONNS.discard(id(conn))
    return "Tour annulé — écritures carte jetées (aucun orphelin)."


# --------------------------------------------------------------------------- #
# Tool: foundSettlement — the WRITE socle (semantic target, validate, log, feedback)
# --------------------------------------------------------------------------- #

def _direction(q: int, r: int, nq: int, nr: int) -> str:
    """Cardinal from (q,r) to a neighbour. +x = East, +y = South (r grows downward).

    WHY: the LLM must never juggle (q,r) — a neighbourhood is described in relative
    directions it can actually reason with ("iron 1 province NE").
    """
    dx, dy = nq - q, nr - r
    ns = "S" if dy > 0 else ("N" if dy < 0 else "")
    ew = "E" if dx > 0 else ("O" if dx < 0 else "")
    return (ns + ew) or "ici"


def _resolve_anchor(conn: sqlite3.Connection, map_id: int, map_name: str, at) -> tuple[int, int]:
    """Resolve a SEMANTIC target to a cell — never a raw (q,r) from the LLM.

    Accepts: a spawn rank ("spawn 1" / "#2" / "3") → the Nth proposeSpawnPositions
    candidate; or a name → a province carrying that feature / label / mapped entity.
    Raises ValueError with an actionable message if it can't be resolved.
    """
    s = str(at).strip()
    m = re.match(r"^(?:spawn\s*)?#?\s*(\d+)$", s, re.I)
    if m:
        rank = int(m.group(1))
        cands = propose_spawn_positions(conn, map_name, n=rank)
        if 1 <= rank <= len(cands):
            c = cands[rank - 1]
            return c["q"], c["r"]
        raise ValueError(f"il n'y a pas de {rank}e proposition de spawn")

    low = s.lower()
    for q, r, label, meta_json in conn.execute(
        "SELECT q, r, label, metadata FROM map_cells WHERE map_id = ?", (map_id,)
    ).fetchall():
        if label and label.lower() == low:
            return q, r
        meta = json.loads(meta_json) if meta_json else {}
        for e in (meta.get("elements") or []):  # any element on the cell can anchor it
            if low in (str(e.get("name", "")).lower(), str(e.get("display_name", "")).lower()):
                return q, r
    erow = conn.execute(
        "SELECT mc.q, mc.r FROM map_cells mc JOIN entity_entities e ON e.id = mc.entity_id "
        "WHERE mc.map_id = ? AND (e.canonical_name = ? OR e.canonical_name LIKE ?) LIMIT 1",
        (map_id, s, f"%{s}%"),
    ).fetchone()
    if erow:
        return erow[0], erow[1]
    raise ValueError(
        f"ancrage « {at} » introuvable sur {map_name} — nomme une feature/entité, "
        "ou une proposition de spawn (« spawn 1 »)"
    )


def _sole_map(conn: sqlite3.Connection, map_name: str) -> tuple[int, str] | None:
    """Resolve a map by name, or fall back to the only map if the game has one."""
    if map_name:
        row = conn.execute(
            "SELECT id, name FROM map_maps WHERE name = ? OR name LIKE ? LIMIT 1",
            (map_name, f"%{map_name}%")).fetchone()
        return (row[0], row[1]) if row else None
    rows = conn.execute("SELECT id, name FROM map_maps").fetchall()
    return (rows[0][0], rows[0][1]) if len(rows) == 1 else None


def found_settlement(conn: sqlite3.Connection, civ_id: int, civ_name: str,
                     map_name: str, at, settlement_name: str | None = None) -> str:
    """Found a civ's settlement on a province — the WRITE template.

    validate (no city in the ocean) → apply (controlling_civ_id + label) → log a
    `settlement` event (auditable/undoable) → return the new local state (the LLM
    can't see the map, so the write echoes back what it did). Target is SEMANTIC
    (`at`): a spawn proposal or a named feature/entity, never a raw (q,r).
    """
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return (f"Carte « {map_name} » introuvable." if map_name
                else "Précise mapName : plusieurs cartes existent.")
    map_id, map_name = resolved

    try:
        q, r = _resolve_anchor(conn, map_id, map_name, at)
    except ValueError as e:
        return f"Fondation impossible : {e}."

    cell = conn.execute(
        "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()
    terrain, meta_json = cell
    meta = json.loads(meta_json) if meta_json else {}
    if terrain == "ocean" or meta.get("water", {}).get("is_ocean"):
        return (f"Fondation impossible : « {at} » est en pleine mer. "
                "Une cité se fonde sur la terre ferme.")

    label = settlement_name or f"Cité de {civ_name}"
    conn.execute(
        "UPDATE map_cells SET controlling_civ_id = ?, label = ? "
        "WHERE map_id = ? AND q = ? AND r = ?", (civ_id, label, map_id, q, r))
    conn.execute(
        "INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
        "VALUES (?, ?, ?, ?, 'settlement')",
        (map_id, q, r, f"Fondation de {label} par {civ_name}."))
    discover(conn, map_id, civ_id, [(q, r), *_neighbours8(q, r)])  # fog: knows its cradle
    _maybe_commit(conn)

    out = [f"✓ **{label}** fondée par {civ_name} sur {map_name}.",
           f"Province : {_describe_province(terrain, meta)}", "", "Voisinage :"]
    ring = conn.execute(
        "SELECT q, r, terrain_type, metadata FROM map_cells "
        "WHERE map_id = ? AND q BETWEEN ? AND ? AND r BETWEEN ? AND ? "
        "AND NOT (q = ? AND r = ?) ORDER BY r, q",
        (map_id, q - 1, q + 1, r - 1, r + 1, q, r)).fetchall()
    for nq, nr, nt, nm in ring:
        out.append(f"- {_direction(q, r, nq, nr)} : "
                   f"{_describe_province(nt, json.loads(nm) if nm else {})}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Tools: findNearest / whatIsBetween — semantic spatial queries (geometry hidden)
# --------------------------------------------------------------------------- #

def _civ_seat(conn: sqlite3.Connection, map_id: int, civ_id: int) -> tuple[int, int] | None:
    """A civ's primary province on a map (top-left of what it controls)."""
    row = conn.execute(
        "SELECT q, r FROM map_cells WHERE map_id = ? AND controlling_civ_id = ? "
        "ORDER BY r, q LIMIT 1", (map_id, civ_id)).fetchone()
    return (row[0], row[1]) if row else None


def _origin_from(conn: sqlite3.Connection, map_id: int, map_name: str, frm: str):
    """Resolve a semantic origin to (cell, label, civ_id).

    civ_id is the resolved civ when the origin IS a placed civ (so the caller can fog
    the search to that civ's discovered provinces), else None (a bare feature/entity
    origin has no fog perspective → the caller searches omnisciently).
    """
    resolved = resolve_civ_name(conn, frm)
    if "error" not in resolved:
        seat = _civ_seat(conn, map_id, resolved["civ"]["id"])
        if seat:
            return seat, resolved["civ"]["name"], resolved["civ"]["id"]
    try:
        return _resolve_anchor(conn, map_id, map_name, frm), frm, None
    except ValueError:
        return None, frm, None


def _cell_matches(terrain: str, meta: dict, what: str) -> bool:
    """Does a province match a free-form 'what' (terrain / biome / water / resource)?"""
    if what in (terrain.lower(), str(meta.get("biome", "")).lower()):
        return True
    w = meta.get("water", {})
    if what in ("river", "fleuve", "rivière") and w.get("is_river"):
        return True
    if what in ("lake", "lac") and w.get("is_lake"):
        return True
    if what in ("ocean", "mer", "océan") and w.get("is_ocean"):
        return True
    for e in (meta.get("elements") or []):  # match an element by name/category/family
        if what in (str(e.get("name", "")).lower(), str(e.get("display_name", "")).lower(),
                    str(e.get("category", "")).lower(), str(e.get("family", "")).lower()):
            return True
    return what in [str(p).lower() for p in (meta.get("resource_potential") or [])]


def find_nearest(conn: sqlite3.Connection, map_id: int, map_name: str,
                 origin: tuple[int, int], origin_label: str, what: str, n: int = 3,
                 discovered: set | None = None) -> str:
    """Nearest provinces matching `what`, from a semantic origin — direction + distance,
    never (q,r). The geometry (Chebyshev distance, ranking) stays here.

    discovered (fog): when a set is passed, only provinces the origin civ has DISCOVERED
    are searchable — a civ can't "find the nearest iron" in land it has never scouted.
    None = omniscient (a bare feature origin, or fog explicitly off)."""
    oq, orr = origin
    wl = what.strip().lower()
    matches = []
    for q, r, terrain, meta_json in conn.execute(
        "SELECT q, r, terrain_type, metadata FROM map_cells WHERE map_id = ?", (map_id,)
    ).fetchall():
        if q == oq and r == orr:
            continue
        if discovered is not None and (q, r) not in discovered:
            continue  # fog: undiscovered province is not searchable
        meta = json.loads(meta_json) if meta_json else {}
        if _cell_matches(terrain, meta, wl):
            matches.append((max(abs(q - oq), abs(r - orr)), q, r, terrain, meta))
    if not matches:
        scope = "" if discovered is None else " (dans le territoire exploré)"
        return f"Rien correspondant à « {what} » sur {map_name} près de {origin_label}{scope}."
    matches.sort(key=lambda m: (m[0], m[1], m[2]))
    lines = [f"# « {what} » le plus proche — depuis {origin_label}", ""]
    for dist, q, r, terrain, meta in matches[:n]:
        prov = "province" if dist == 1 else "provinces"
        lines.append(f"- {_direction(oq, orr, q, r)} à {dist} {prov} : "
                     f"{_describe_province(terrain, meta)}")
    return "\n".join(lines)


def _line(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    """Bresenham line between two grid cells (inclusive of both ends)."""
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx - dy
    x, y, pts = x0, y0, []
    while True:
        pts.append((x, y))
        if (x, y) == (x1, y1):
            return pts
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def what_is_between(conn: sqlite3.Connection, map_id: int, a: tuple[int, int],
                    b: tuple[int, int], a_label: str, b_label: str,
                    known: set | None = None) -> str:
    """The provinces (and barriers) on the line between two civs' seats.

    known (fog): when a set is passed, only provinces EITHER civ has discovered are
    described; the rest are marked unexplored (and never count as barriers — you can't
    report a mountain range nobody has scouted). None = omniscient (fog off)."""
    pts = _line(a, b)
    between = pts[1:-1]
    if not between:
        return f"{a_label} et {b_label} sont adjacentes — rien entre elles."
    lines = [f"# Entre {a_label} et {b_label}",
             f"Distance : {len(pts) - 1} provinces.", ""]
    barriers = []
    unknown = 0
    for q, r in between:
        row = conn.execute(
            "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
            (map_id, q, r)).fetchone()
        if not row:
            continue
        if known is not None and (q, r) not in known:
            unknown += 1
            continue  # fog: don't describe or barrier-check unscouted ground
        terrain, meta_json = row
        meta = json.loads(meta_json) if meta_json else {}
        lines.append(f"- {_describe_province(terrain, meta)}")
        if terrain in ("mountain", "ocean") or meta.get("water", {}).get("is_ocean"):
            barriers.append(terrain)
    if unknown:
        prov = "province" if unknown == 1 else "provinces"
        lines.append(f"- _{unknown} {prov} inexplorée(s) sur le chemin._")
    if barriers:
        lines += ["", f"⚠️ Barrière(s) sur le chemin : {', '.join(sorted(set(barriers)))}."]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tools: recordEvent / annotate — generic narrative writes (reuse the socle)
# --------------------------------------------------------------------------- #

# The chronicle's event vocabulary (migration 031: map_cell_events.event_type).
_EVENT_KINDS = {"settlement", "battle", "discovery", "diplomatic",
                "migration", "disaster", "note"}


def record_event(conn: sqlite3.Connection, map_name: str, kind: str, at,
                 description: str, civ_name: str | None = None) -> str:
    """Log a narrative event on a province — the generic write (battle, discovery…).

    Same discipline as foundSettlement: semantic anchor → validate the event kind →
    log to map_cell_events → echo the province. No state change beyond the chronicle.
    """
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name
                else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved
    k = (kind or "").strip().lower()
    if k not in _EVENT_KINDS:
        return (f"Type d'événement inconnu « {kind} ». "
                f"Valides : {', '.join(sorted(_EVENT_KINDS))}.")
    if not (description or "").strip():
        return "Error: description requise."
    try:
        q, r = _resolve_anchor(conn, map_id, map_name, at)
    except ValueError as e:
        return f"Événement impossible : {e}."

    desc = description if not civ_name else f"{description} ({civ_name})"
    conn.execute(
        "INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
        "VALUES (?, ?, ?, ?, ?)", (map_id, q, r, desc, k))
    _maybe_commit(conn)
    row = conn.execute(
        "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()
    meta = json.loads(row[1]) if row[1] else {}
    return (f"✓ Événement [{k}] sur {map_name} : {desc}\n"
            f"Province : {_describe_province(row[0], meta)}")


def annotate(conn: sqlite3.Connection, map_name: str, at,
             label: str | None = None, note: str | None = None) -> str:
    """Set a GM label and/or attach a note to a province (semantic anchor)."""
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name
                else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved
    if not (label or note):
        return "Error: fournis un label et/ou une note."
    try:
        q, r = _resolve_anchor(conn, map_id, map_name, at)
    except ValueError as e:
        return f"Annotation impossible : {e}."

    if label:
        conn.execute("UPDATE map_cells SET label = ? WHERE map_id = ? AND q = ? AND r = ?",
                     (label, map_id, q, r))
    if note:
        conn.execute(
            "INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
            "VALUES (?, ?, ?, ?, 'note')", (map_id, q, r, note))
    _maybe_commit(conn)
    done = ", ".join(p for p in (f"label « {label} »" if label else "",
                                 "note ajoutée" if note else "") if p)
    row = conn.execute(
        "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()
    meta = json.loads(row[1]) if row[1] else {}
    return f"✓ Province annotée ({done}) : {_describe_province(row[0], meta)}"


# --------------------------------------------------------------------------- #
# Tools: expandTerritory / moveEntity — richer narrative writes
# --------------------------------------------------------------------------- #

_CARDINALS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "o": (-1, 0), "w": (-1, 0),
              "ne": (1, -1), "no": (-1, -1), "nw": (-1, -1), "se": (1, 1),
              "so": (-1, 1), "sw": (-1, 1)}


def _neighbours8(q: int, r: int):
    for dr in (-1, 0, 1):
        for dq in (-1, 0, 1):
            if dq or dr:
                yield q + dq, r + dr


def _direction_vector(conn: sqlite3.Connection, map_id: int, map_name: str,
                      toward: str, owned: set) -> tuple[float, float] | None:
    """A bias direction for expansion: a cardinal, or toward a civ/feature's cell."""
    s = (toward or "").strip().lower()
    if s in _CARDINALS:
        return _CARDINALS[s]
    # else: a civ or a named anchor → vector from the owned centroid to its cell.
    target = None
    resolved = resolve_civ_name(conn, toward)
    if "error" not in resolved:
        target = _civ_seat(conn, map_id, resolved["civ"]["id"])
    if target is None:
        try:
            target = _resolve_anchor(conn, map_id, map_name, toward)
        except ValueError:
            return None
    cq = sum(q for q, _ in owned) / len(owned)
    cr = sum(r for _, r in owned) / len(owned)
    return (target[0] - cq, target[1] - cr)


def _aligned(step: tuple[int, int], dvec: tuple[float, float] | None) -> float:
    """Dot product of a claim step with the bias direction (0 if no bias)."""
    if dvec is None:
        return 0.0
    import math
    sn = math.hypot(*step) or 1.0
    dn = math.hypot(*dvec) or 1.0
    return (step[0] * dvec[0] + step[1] * dvec[1]) / (sn * dn)


def expand_territory(conn: sqlite3.Connection, civ_id: int, civ_name: str,
                     map_name: str, toward: str, amount: int = 1) -> str:
    """Claim `amount` unclaimed LAND provinces on the civ's frontier, biased `toward`.

    Greedy frontier growth: each round claims the adjacent unclaimed land province best
    aligned with the direction. Never claims ocean or another civ's land. Logs a
    `migration` event per claim, echoes what was taken.
    """
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved

    owned = {(q, r) for q, r in conn.execute(
        "SELECT q, r FROM map_cells WHERE map_id = ? AND controlling_civ_id = ?",
        (map_id, civ_id)).fetchall()}
    if not owned:
        return f"{civ_name} n'a pas de territoire sur {map_name} — fonde une cité d'abord."

    dvec = _direction_vector(conn, map_id, map_name, toward, owned)
    claimed: list[tuple[int, int, str]] = []
    for _ in range(max(1, amount)):
        best = None
        for oq, orr in owned:
            for nq, nr in _neighbours8(oq, orr):
                if (nq, nr) in owned:
                    continue
                cell = conn.execute(
                    "SELECT terrain_type, controlling_civ_id, metadata FROM map_cells "
                    "WHERE map_id = ? AND q = ? AND r = ?", (map_id, nq, nr)).fetchone()
                if not cell or cell[1] is not None:
                    continue  # off-map or already owned by someone
                meta = json.loads(cell[2]) if cell[2] else {}
                if cell[0] == "ocean" or meta.get("water", {}).get("is_ocean"):
                    continue
                score = _aligned((nq - oq, nr - orr), dvec)
                if best is None or score > best[0]:
                    best = (score, nq, nr, oq, orr, cell[0])
        if best is None:
            break
        _, cq, cr, oq, orr, terrain = best
        conn.execute("UPDATE map_cells SET controlling_civ_id = ? "
                     "WHERE map_id = ? AND q = ? AND r = ?", (civ_id, map_id, cq, cr))
        conn.execute("INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
                     "VALUES (?, ?, ?, ?, 'migration')",
                     (map_id, cq, cr, f"{civ_name} étend son territoire ({terrain})."))
        owned.add((cq, cr))
        claimed.append((oq, orr, terrain, cq, cr))
    for _oq, _orr, _t, cq, cr in claimed:
        discover(conn, map_id, civ_id, [(cq, cr), *_neighbours8(cq, cr)])  # sees its new frontier
    _maybe_commit(conn)

    if not claimed:
        return f"{civ_name} ne peut pas s'étendre (frontière bloquée par la mer ou d'autres civs)."
    lines = [f"✓ {civ_name} annexe {len(claimed)} province(s) sur {map_name}"
             + (f" vers {toward}" if toward else "") + " :"]
    for oq, orr, terrain, cq, cr in claimed:
        lines.append(f"- {_direction(oq, orr, cq, cr)} : {terrain}")
    lines.append(f"Territoire total : {len(owned)} provinces.")
    return "\n".join(lines)


def move_entity(conn: sqlite3.Connection, map_name: str, entity_name: str, to) -> str:
    """Move an entity's pawn to a province (one pawn per entity per map)."""
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved

    erow = conn.execute(
        "SELECT DISTINCT e.id, e.canonical_name FROM entity_entities e "
        "LEFT JOIN entity_aliases ea ON ea.entity_id = e.id "
        "WHERE e.canonical_name = ? OR e.canonical_name LIKE ? OR ea.alias LIKE ? LIMIT 1",
        (entity_name, f"%{entity_name}%", f"%{entity_name}%")).fetchone()
    if not erow:
        return f"Entité « {entity_name} » introuvable."
    entity_id, ename = erow
    try:
        q, r = _resolve_anchor(conn, map_id, map_name, to)
    except ValueError as e:
        return f"Déplacement impossible : {e}."

    conn.execute(
        "INSERT INTO map_entity_pawns (map_id, entity_id, q, r) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(map_id, entity_id) DO UPDATE SET q = excluded.q, r = excluded.r",
        (map_id, entity_id, q, r))
    conn.execute("INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
                 "VALUES (?, ?, ?, ?, 'migration')", (map_id, q, r, f"{ename} se déplace ici."))
    _maybe_commit(conn)
    row = conn.execute(
        "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()
    meta = json.loads(row[1]) if row and row[1] else {}
    return f"✓ {ename} déplacé sur {map_name} : {_describe_province(row[0], meta) if row else '?'}"


def cede_territory(conn: sqlite3.Connection, from_civ_id: int, from_name: str,
                   to_civ_id: int, to_name: str, map_name: str, at, amount: int = 1) -> str:
    """One civ cedes provinces to another (diplomacy / conquest settlement).

    Mirror of expandTerritory, but a TRANSFER not a claim. `at` is a semantic anchor to
    a province the CEDING civ controls; amount>1 extends the cession over adjacent
    ceding-owned provinces (a contiguous parcel). Validates ownership, flips control,
    logs a `diplomatic` event per province, and the RECIPIENT discovers what it gained.
    A WRITE (turn-atomic). Semantic anchor only — never (q,r).
    """
    resolved = _sole_map(conn, map_name)
    if not resolved:
        return ("Précise mapName." if not map_name else f"Carte « {map_name} » introuvable.")
    map_id, map_name = resolved
    if from_civ_id == to_civ_id:
        return "Une civ ne peut pas se céder du territoire à elle-même."
    try:
        q, r = _resolve_anchor(conn, map_id, map_name, at)
    except ValueError as e:
        return f"Cession impossible : {e}."

    owner = conn.execute(
        "SELECT controlling_civ_id FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()
    if not owner or owner[0] != from_civ_id:
        return (f"{from_name} ne contrôle pas la province « {at} » — "
                "on ne peut céder que son propre territoire.")

    # BFS over the ceding civ's own provinces from the anchor → a contiguous parcel.
    from_owned = {(cq, cr) for cq, cr in conn.execute(
        "SELECT q, r FROM map_cells WHERE map_id = ? AND controlling_civ_id = ?",
        (map_id, from_civ_id)).fetchall()}
    ceded: list[tuple[int, int]] = []
    frontier, seen = [(q, r)], {(q, r)}
    while frontier and len(ceded) < max(1, amount):
        cq, cr = frontier.pop(0)
        if (cq, cr) not in from_owned:
            continue
        ceded.append((cq, cr))
        for nq, nr in _neighbours8(cq, cr):
            if (nq, nr) in from_owned and (nq, nr) not in seen:
                seen.add((nq, nr))
                frontier.append((nq, nr))

    for cq, cr in ceded:
        conn.execute("UPDATE map_cells SET controlling_civ_id = ? "
                     "WHERE map_id = ? AND q = ? AND r = ?", (to_civ_id, map_id, cq, cr))
        conn.execute("INSERT INTO map_cell_events (map_id, q, r, description, event_type) "
                     "VALUES (?, ?, ?, ?, 'diplomatic')",
                     (map_id, cq, cr, f"{from_name} cède cette province à {to_name}."))
        discover(conn, map_id, to_civ_id, [(cq, cr), *_neighbours8(cq, cr)])  # the recipient sees it
    _maybe_commit(conn)

    remaining = len(from_owned) - len(ceded)
    return (f"✓ {from_name} cède {len(ceded)} province(s) à {to_name} sur {map_name}.\n"
            f"{from_name} : {remaining} province(s) restante(s).")


def _clean_input(tool_input: dict) -> dict:
    """Sanitize LLM-generated tool inputs: replace nil-like values with None."""
    return {k: (None if isinstance(v, str) and v in _NIL_VALUES else v) for k, v in tool_input.items()}


def dispatch_tool(
    conn: sqlite3.Connection,
    tool_name: str,
    tool_input: dict,
    *,
    db_path: str | None = None,
    llm_client=None,
    model: str = "claude-opus-4-8",
    proxy: str | None = None,
) -> str:
    """Route a tool call to the appropriate function. Returns Markdown string.

    Extra kwargs (db_path, llm_client, model, proxy) are only needed for deepExplore
    (the sub-agent makes its own LLM call through the etheryale proxy).
    """
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
        return get_turn_detail(
            conn, int(turn_number), resolved["id"], resolved["name"],
            show_segments=bool(tool_input.get("showSegments")),
            show_entities=bool(tool_input.get("showEntities")),
            show_notes=bool(tool_input.get("showNotes")),
        )

    if tool_name == "searchLore":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return search_lore(
            conn,
            query=tool_input.get("query") or "",
            civ_id=civ_id,
            entity_type=tool_input.get("entityType"),
            tag=tool_input.get("tag"),
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            last_n_turns=tool_input.get("lastNTurns"),
            limit=int(tool_input.get("limit") or 20),
        )

    if tool_name == "getEntityDetail":
        entity_name = tool_input.get("entityName", "")
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        # Multi-hop: getEntityDetail absorbed exploreRelations when the tool surface was
        # consolidated, but the absorption dropped `depth` -- so "trace A -> B -> C" was
        # unreachable even though explore_relations was still sitting in dispatch.
        # relationDepth > 1 routes to it, keeping ONE entity tool instead of two.
        try:
            rel_depth = int(tool_input.get("relationDepth") or 1)
        except (TypeError, ValueError):
            rel_depth = 1
        if rel_depth > 1:
            if not entity_name:
                return "Error: entityName is required."
            return explore_relations(conn, entity_name, civ_id=civ_id, depth=min(rel_depth, 3))

        return get_entity_detail(
            conn,
            entity_name,
            civ_id=civ_id,
            include_relations=bool(tool_input.get("relations")),
            include_activity=bool(tool_input.get("activity") or tool_input.get("showTimeline")),
            show_mentions=bool(tool_input.get("showMentions")),
            show_facts=bool(tool_input.get("showFacts")),
            show_notes=bool(tool_input.get("showNotes")),
        )

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
        return timeline(
            conn,
            civ_id=civ_id,
            limit=int(tool_input.get("limit") or 50),
            turn_type=tool_input.get("turnType"),
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            last_n_turns=tool_input.get("lastNTurns"),
            entity_name=tool_input.get("entityName"),
        )

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
            not_found: list[str] = []
            for cn in civ_names_raw:
                result = resolve_civ_name(conn, cn)
                if "error" in result:
                    # Don't abort — skip unfound civs and warn at the end
                    not_found.append(cn)
                    continue
                civ = result["civ"]
                if civ["id"] not in seen_ids:
                    seen_ids.add(civ["id"])
                    resolved_civs.append(civ)

        if len(resolved_civs) < 2:
            names = ", ".join(c["name"] for c in resolved_civs) if resolved_civs else "aucune"
            all_civs = conn.execute("SELECT name FROM civ_civilizations ORDER BY name").fetchall()
            civ_list = ", ".join(r[0] for r in all_civs)
            missing = f" (not found: {', '.join(not_found)})" if not_found else ""
            return (
                f"Cannot compare fewer than 2 civilizations. Found: {names}{missing}. "
                f"Available: {civ_list}. Use listCivs to see all civilizations first."
            )

        # Run comparison — prepend warning for any unresolved civs
        result_text = compare_civs(conn, resolved_civs, aspects=tool_input.get("aspects"))
        if not_found:
            warning = (
                f"> ⚠️ Civilizations not found (excluded from comparison): "
                f"{', '.join(not_found)}\n\n"
            )
            result_text = warning + result_text
        return result_text

    if tool_name == "searchTurnContent":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return search_turn_content(
            conn,
            query=tool_input.get("query", ""),
            civ_id=civ_id,
            segment_type=tool_input.get("segmentType"),
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            last_n_turns=tool_input.get("lastNTurns"),
            limit=int(tool_input.get("limit") or 20),
        )

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
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            last_n_turns=tool_input.get("lastNTurns"),
            limit=int(tool_input.get("limit") or 25),
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

    if tool_name == "listSubjects":
        resolved = _resolve()
        civ_id = resolved["id"] if resolved and "error" not in resolved else None
        return list_subjects(
            conn,
            civ_id=civ_id,
            status=tool_input.get("status") or "open",
            direction=tool_input.get("direction"),
            tag=tool_input.get("tag"),
            from_turn=tool_input.get("fromTurn"),
            to_turn=tool_input.get("toTurn"),
            last_n_turns=tool_input.get("lastNTurns"),
            limit=int(tool_input.get("limit") or 50),
        )

    if tool_name == "getNotes":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        subject_id_raw = tool_input.get("subjectId")
        turn_number_raw = tool_input.get("turnNumber")
        return get_notes(
            conn,
            entity_name=tool_input.get("entityName"),
            subject_id=int(subject_id_raw) if subject_id_raw is not None else None,
            turn_number=int(turn_number_raw) if turn_number_raw is not None else None,
            civ_id=civ_id,
        )

    if tool_name == "getSubjectDetail":
        subject_id = tool_input.get("subjectId")
        if subject_id is None:
            return "Error: subjectId is required."
        return get_subject_detail(
            conn, int(subject_id),
            show_options=bool(tool_input.get("showOptions")),
            show_resolutions=bool(tool_input.get("showResolutions")),
            show_notes=bool(tool_input.get("showNotes")),
        )

    if tool_name == "getEntitiesByTag":
        tag = tool_input.get("tag")
        if not tag:
            return "Error: tag is required."
        resolved = _resolve()
        civ_id = resolved["id"] if resolved and "error" not in resolved else None
        return get_entities_by_tag(
            conn,
            tag=tag,
            civ_id=civ_id,
            entity_type=tool_input.get("entityType"),
        )

    if tool_name == "getFavorites":
        civ_id = None
        civ_name_str = tool_input.get("civName")
        if civ_name_str:
            resolved = _resolve()
            if resolved and "error" not in resolved:
                civ_id = resolved["id"]
        return get_favorites(
            conn,
            item_type=tool_input.get("type"),
            civ_id=civ_id,
            tag=tool_input.get("tag"),
            status=tool_input.get("status"),
            limit=int(tool_input.get("limit") or 20),
        )

    if tool_name == "getCivRelations":
        civ_name_str = tool_input.get("civName")
        if not civ_name_str:
            return "Error: civName is required."
        return get_civ_relations(conn, civ_name=civ_name_str)

    if tool_name == "deepExplore":
        question = tool_input.get("question", "")
        if not question:
            return "Error: question is required."
        return deep_explore(
            conn,
            question=question,
            context=tool_input.get("context"),
            db_path=db_path,
            llm_client=llm_client,
            model=model,
            proxy=proxy,
        )

    # --- Map system tools ---

    if tool_name == "getMaps":
        return get_maps(conn)

    if tool_name == "getMapOverview":
        map_name = tool_input.get("mapName", "")
        if not map_name:
            return "Error: mapName is required."
        m = resolve_map_name(conn, map_name)
        if not m:
            return f"Carte « {map_name} » introuvable."
        return get_map_overview(conn, m["id"], m["name"])

    if tool_name == "getCell":
        map_name = tool_input.get("mapName", "")
        q_raw = tool_input.get("q")
        r_raw = tool_input.get("r")
        if not map_name or q_raw is None or r_raw is None:
            return "Error: mapName, q, and r are required."
        m = resolve_map_name(conn, map_name)
        if not m:
            return f"Carte « {map_name} » introuvable."
        return get_cell(conn, m["id"], int(q_raw), int(r_raw))

    if tool_name == "getCellHistory":
        map_name = tool_input.get("mapName", "")
        q_raw = tool_input.get("q")
        r_raw = tool_input.get("r")
        if not map_name or q_raw is None or r_raw is None:
            return "Error: mapName, q, and r are required."
        m = resolve_map_name(conn, map_name)
        if not m:
            return f"Carte « {map_name} » introuvable."
        limit = int(tool_input.get("limit") or 20)
        return get_cell_history(conn, m["id"], int(q_raw), int(r_raw), limit)

    if tool_name == "getTerritory":
        civ_name_str = tool_input.get("civName", "")
        if not civ_name_str:
            return "Error: civName is required."
        resolved = resolve_civ_name(conn, civ_name_str)
        if "error" in resolved:
            return resolved["error"]
        civ = resolved["civ"]
        return get_territory(conn, civ["id"], civ["name"])

    if tool_name == "findEntityOnMap":
        entity_name = tool_input.get("entityName", "")
        if not entity_name:
            return "Error: entityName is required."
        return find_entity_on_map(conn, entity_name)

    if tool_name == "groundCivTerrain":
        civ_name_str = tool_input.get("civName", "")
        if not civ_name_str:
            return "Error: civName is required."
        resolved = resolve_civ_name(conn, civ_name_str)
        if "error" in resolved:
            return resolved["error"]
        civ = resolved["civ"]
        # `or 2` would turn a legitimate radius 0 (just the seat) into 2.
        raw_radius = tool_input.get("radius")
        radius = 2 if raw_radius is None else max(0, int(raw_radius))
        fog = tool_input.get("fog")
        fog = True if fog is None else bool(fog)
        raw_mh = tool_input.get("maxHiddenLevel")
        max_hidden = 0 if raw_mh is None else max(0, int(raw_mh))
        return ground_civ_terrain(conn, civ["id"], civ["name"], radius=radius, fog=fog,
                                  max_hidden_level=max_hidden)

    if tool_name == "discoverAround":
        civ_name_str = tool_input.get("civName", "")
        if not civ_name_str:
            return "Error: civName is required."
        resolved = resolve_civ_name(conn, civ_name_str)
        if "error" in resolved:
            return resolved["error"]
        civ = resolved["civ"]
        return discover_around(conn, civ["id"], civ["name"], tool_input.get("mapName", ""),
                               tool_input.get("around", ""),
                               radius=int(tool_input.get("radius") or 1))

    if tool_name == "proposeSpawnPositions":
        resolved = _sole_map(conn, tool_input.get("mapName", ""))
        if not resolved:
            return ("Précise mapName." if not tool_input.get("mapName")
                    else f"Carte « {tool_input['mapName']} » introuvable.")
        map_id, map_name = resolved
        picks = propose_spawn_positions(
            conn, map_name, n=int(tool_input.get("n") or 5),
            min_spacing=int(tool_input.get("minSpacing") or 0))
        if not picks:
            return f"Aucune province habitable proposable sur {map_name}."
        # Render ranks (NOT coordinates): the agent founds via `at="spawn N"`.
        lines = [f"# Positions de spawn proposées — {map_name}", ""]
        for i, p in enumerate(picks, 1):
            biome = f" ({p['biome']})" if p.get("biome") else ""
            lines.append(f"{i}. **{p['terrain']}**{biome} — score {p['score']} — "
                         f"{', '.join(p['why'])}")
        lines.append("")
        lines.append('Pour fonder : `foundSettlement(civName, at="spawn N")`.')
        return "\n".join(lines)

    if tool_name == "foundSettlement":
        civ_name_str = tool_input.get("civName", "")
        if not civ_name_str:
            return "Error: civName is required."
        resolved = resolve_civ_name(conn, civ_name_str)
        if "error" in resolved:
            return resolved["error"]
        civ = resolved["civ"]
        at = tool_input.get("at")
        if at is None or str(at).strip() == "":
            return "Error: 'at' is required (feature/entité nommée, ou « spawn N »)."
        return found_settlement(conn, civ["id"], civ["name"],
                                tool_input.get("mapName", ""), at,
                                settlement_name=tool_input.get("name"))

    if tool_name == "findNearest":
        resolved = _sole_map(conn, tool_input.get("mapName", ""))
        if not resolved:
            return ("Précise mapName." if not tool_input.get("mapName")
                    else f"Carte « {tool_input['mapName']} » introuvable.")
        map_id, map_name = resolved
        frm, what = tool_input.get("from", ""), tool_input.get("what", "")
        if not frm or not what:
            return "Error: 'from' (civ/feature) et 'what' (ressource/biome/terrain/eau) requis."
        origin, label, civ_id = _origin_from(conn, map_id, map_name, frm)
        if origin is None:
            return f"Point de départ « {frm} » introuvable (civ placée, feature ou entité)."
        # Fog (default true) applies only when the origin is a civ (it has a discovery
        # perspective); a bare feature origin searches omnisciently.
        fog = tool_input.get("fog")
        fog = True if fog is None else bool(fog)
        discovered = discovered_set(conn, map_id, civ_id) if (fog and civ_id) else None
        return find_nearest(conn, map_id, map_name, origin, label, what,
                            n=int(tool_input.get("n") or 3), discovered=discovered)

    if tool_name == "whatIsBetween":
        resolved = _sole_map(conn, tool_input.get("mapName", ""))
        if not resolved:
            return ("Précise mapName." if not tool_input.get("mapName")
                    else f"Carte « {tool_input['mapName']} » introuvable.")
        map_id, map_name = resolved
        ra = resolve_civ_name(conn, tool_input.get("civA", ""))
        rb = resolve_civ_name(conn, tool_input.get("civB", ""))
        if "error" in ra:
            return ra["error"]
        if "error" in rb:
            return rb["error"]
        sa = _civ_seat(conn, map_id, ra["civ"]["id"])
        sb = _civ_seat(conn, map_id, rb["civ"]["id"])
        if not sa:
            return f"{ra['civ']['name']} n'est pas placée sur {map_name}."
        if not sb:
            return f"{rb['civ']['name']} n'est pas placée sur {map_name}."
        # Fog (default true): a province on the path is known if EITHER civ scouted it.
        fog = tool_input.get("fog")
        fog = True if fog is None else bool(fog)
        known = None
        if fog:
            known = (discovered_set(conn, map_id, ra["civ"]["id"])
                     | discovered_set(conn, map_id, rb["civ"]["id"]))
        return what_is_between(conn, map_id, sa, sb, ra["civ"]["name"], rb["civ"]["name"],
                               known=known)

    if tool_name == "recordEvent":
        at = tool_input.get("at")
        if at is None or str(at).strip() == "":
            return "Error: 'at' is required (feature/entité nommée, ou « spawn N »)."
        civ_name = None
        if tool_input.get("civName"):
            cr = resolve_civ_name(conn, tool_input["civName"])
            civ_name = cr["civ"]["name"] if "error" not in cr else tool_input["civName"]
        return record_event(conn, tool_input.get("mapName", ""),
                            tool_input.get("kind", ""), at,
                            tool_input.get("description", ""), civ_name=civ_name)

    if tool_name == "annotate":
        at = tool_input.get("at")
        if at is None or str(at).strip() == "":
            return "Error: 'at' is required (feature/entité nommée, ou « spawn N »)."
        return annotate(conn, tool_input.get("mapName", ""), at,
                        label=tool_input.get("label"), note=tool_input.get("note"))

    if tool_name == "expandTerritory":
        civ_name_str = tool_input.get("civName", "")
        if not civ_name_str:
            return "Error: civName is required."
        resolved = resolve_civ_name(conn, civ_name_str)
        if "error" in resolved:
            return resolved["error"]
        civ = resolved["civ"]
        return expand_territory(conn, civ["id"], civ["name"],
                                tool_input.get("mapName", ""), tool_input.get("toward", ""),
                                amount=int(tool_input.get("amount") or 1))

    if tool_name == "moveEntity":
        entity_name = tool_input.get("entityName", "")
        to = tool_input.get("to")
        if not entity_name or to is None or str(to).strip() == "":
            return "Error: 'entityName' et 'to' (cible sémantique) requis."
        return move_entity(conn, tool_input.get("mapName", ""), entity_name, to)

    if tool_name == "cedeTerritory":
        from_name_str = tool_input.get("fromCiv", "")
        to_name_str = tool_input.get("toCiv", "")
        if not from_name_str or not to_name_str:
            return "Error: 'fromCiv' et 'toCiv' requis."
        rf = resolve_civ_name(conn, from_name_str)
        if "error" in rf:
            return rf["error"]
        rt = resolve_civ_name(conn, to_name_str)
        if "error" in rt:
            return rt["error"]
        at = tool_input.get("at")
        if at is None or str(at).strip() == "":
            return "Error: 'at' is required (province cédée : feature/label/entité nommée)."
        return cede_territory(conn, rf["civ"]["id"], rf["civ"]["name"],
                              rt["civ"]["id"], rt["civ"]["name"],
                              tool_input.get("mapName", ""), at,
                              amount=int(tool_input.get("amount") or 1))

    # Turn transactionality — orchestration only (NOT LLM-facing, absent from
    # tool_definitions): Demiurgos's turn runner brackets a turn so map writes are
    # atomic with its shadow-DB commit.
    if tool_name == "beginTurn":
        return begin_turn(conn)
    if tool_name == "commitTurn":
        return commit_turn(conn)
    if tool_name == "abortTurn":
        return abort_turn(conn)

    if tool_name == "discoverMemory":
        civ_id = None
        if tool_input.get("civName"):
            resolved = _resolve()
            if resolved and "error" in resolved:
                return resolved["error"]
            if resolved:
                civ_id = resolved["id"]
        raw_keys = tool_input.get("keys")
        keys = None
        if isinstance(raw_keys, list):
            keys = [str(k).strip() for k in raw_keys if str(k).strip()] or None
        elif isinstance(raw_keys, str) and raw_keys.strip():
            keys = [raw_keys.strip()]  # tolerate a bare string
        return discover_memory(
            conn,
            keys=keys,
            civ_id=civ_id,
            mem_type=(tool_input.get("type") or None),
            include_inactive=bool(tool_input.get("includeInactive")),
        )

    if tool_name == "editMemory":
        # One tool that does everything: create / update (default) or forget.
        key = (tool_input.get("key") or "").strip()
        if not key:
            return "Error: key is required."
        civ_id = None
        if tool_input.get("civName"):
            resolved = _resolve()
            if resolved and "error" in resolved:
                return resolved["error"]
            if resolved:
                civ_id = resolved["id"]

        # forget=true -> deactivate this memory, ignore the content fields.
        if tool_input.get("forget"):
            return forget_memory(conn, key, civ_id=civ_id)

        content = (tool_input.get("content") or "").strip()
        if not content:
            return "Error: content is required (unless forget=true)."

        # Anchor: the model passes a turn NUMBER; resolve it to the turn_id for
        # this civ (turn numbers are per-civ). Unresolvable -> no anchor.
        source_turn = None
        turn_raw = tool_input.get("turnNumber")
        if turn_raw is not None and civ_id is not None:
            try:
                trow = conn.execute(
                    "SELECT id FROM turn_turns WHERE civ_id = ? AND turn_number = ?",
                    (civ_id, int(turn_raw)),
                ).fetchone()
                if trow:
                    source_turn = trow[0]
            except (TypeError, ValueError):
                pass
        result = save_memory(
            conn, key, content,
            description=(tool_input.get("description") or ""),
            civ_id=civ_id,
            mem_type=(tool_input.get("type") or "fact"),
            source_turn=source_turn,
        )

        # Links to database articles ("entity:Nom", "turn:12", "subject:18").
        # Replaced wholesale on each upsert so the memory's links match what was passed.
        raw_links = tool_input.get("links")
        if isinstance(raw_links, str):
            raw_links = [raw_links]
        if isinstance(raw_links, list):
            row = conn.execute(
                "SELECT id FROM agent_memory WHERE mem_key = ? AND civ_id IS ?",
                (key, civ_id),
            ).fetchone()
            if row:
                _set_memory_links(conn, row[0], raw_links, civ_id)
        return result

    return f"Unknown tool: {tool_name}"
