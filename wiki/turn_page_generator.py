"""Turn page generators for Phase 2 — Individual turn pages.

Functions:
- generate_turn_page: Creates a single detailed turn page
- generate_turn_index: Creates the turns/index.md with list and previews

These functions follow the Phase 2 template from REFACTOR_PLAN.md,
separating GM questions from player responses.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime


def generate_turn_page(
    conn: sqlite3.Connection,
    turn_id: int,
    civ_name: str,
    player_name: str | None = None,
) -> str:
    """Generate a single turn page with detailed breakdown.

    Follows Phase 2 template:
    - Turn header with metadata
    - Stats (entities, segments, technologies, resources)
    - Question MJ (narrative + choices proposed)
    - Reponse Joueur (player response)
    - Consequences (if any)
    - Discoveries (geography, technologies, resources, beliefs)
    - Entities mentioned
    - Raw Discord messages

    Args:
        conn: Database connection
        turn_id: Turn ID to generate page for
        civ_name: Civilization name
        player_name: Player name (optional)

    Returns:
        Markdown content for the turn page
    """
    from generate import (
        _capitalize_entity,
        _clean_segment_content,
        _clean_summary,
        _detect_gm_authors,
        _entity_type_label,
        _group_messages_by_author,
        _parse_json_data,
        _parse_json_list,
        is_noise_entity,
    )

    turn = conn.execute("SELECT * FROM turn_turns WHERE id = ?", (turn_id,)).fetchone()
    if not turn:
        return ""

    civ_id = turn["civ_id"]
    turn_number = turn["turn_number"]

    # Parse all JSON fields
    summary = _clean_summary(turn["detailed_summary"] or turn["summary"] or "")
    key_events = _parse_json_list(turn["key_events"])
    choices_made = _parse_json_list(turn["choices_made"])

    # Safely get optional columns that may not exist
    try:
        media_links = _parse_json_data(turn["media_links"]) if turn["media_links"] else []
    except (KeyError, IndexError):
        media_links = []

    try:
        technologies = _parse_json_list(turn["technologies"]) if turn["technologies"] else []
    except (KeyError, IndexError):
        technologies = []

    try:
        resources = _parse_json_list(turn["resources"]) if turn["resources"] else []
    except (KeyError, IndexError):
        resources = []

    try:
        beliefs = _parse_json_list(turn["beliefs"]) if turn["beliefs"] else []
    except (KeyError, IndexError):
        beliefs = []

    try:
        geography = _parse_json_list(turn["geography"]) if turn["geography"] else []
    except (KeyError, IndexError):
        geography = []

    try:
        choices_proposed = _parse_json_list(turn["choices_proposed"]) if turn["choices_proposed"] else []
    except (KeyError, IndexError):
        choices_proposed = []

    # Get Discord timestamp from first message
    raw_ids = _parse_json_list(turn["raw_message_ids"])
    discord_date = ""
    if raw_ids:
        first_msg = conn.execute(
            "SELECT timestamp FROM turn_raw_messages WHERE id = ?",
            (int(raw_ids[0]),)
        ).fetchone()
        if first_msg:
            try:
                dt = datetime.fromisoformat(first_msg["timestamp"].replace("Z", "+00:00"))
                discord_date = dt.strftime("%d/%m/%Y")
            except (ValueError, AttributeError):
                discord_date = ""

    # Get segments by type
    segments = conn.execute(
        """SELECT segment_type, content, segment_order
           FROM turn_segments WHERE turn_id = ? ORDER BY segment_order""",
        (turn_id,)
    ).fetchall()

    segments_by_type = {
        "narrative": [],
        "choice": [],
        "consequence": [],
        "ooc": [],
        "description": [],
    }
    for seg in segments:
        stype = seg["segment_type"]
        if stype in segments_by_type:
            segments_by_type[stype].append(seg["content"])

    # Get entities mentioned
    entities = conn.execute(
        """SELECT DISTINCT e.id, e.canonical_name, e.entity_type,
                  COUNT(m.id) as mentions_in_turn,
                  e.first_seen_turn = ? as is_new
           FROM entity_mentions m
           JOIN entity_entities e ON m.entity_id = e.id
           WHERE m.turn_id = ?
           GROUP BY e.id
           ORDER BY mentions_in_turn DESC, e.entity_type, e.canonical_name""",
        (turn_id, turn_id)
    ).fetchall()

    # Count new entities
    new_entities = [e for e in entities if e["is_new"] and not is_noise_entity(e["canonical_name"])]
    total_mentions = sum(e["mentions_in_turn"] for e in entities)

    # Get GM vs Player messages
    gm_authors = _detect_gm_authors(conn)
    message_groups = _group_messages_by_author(conn, raw_ids, gm_authors) if raw_ids else []

    # Separate GM question vs player response
    gm_messages = [g for g in message_groups if g["is_gm"]]
    player_messages = [g for g in message_groups if not g["is_gm"]]

    # --- Start building page ---
    try:
        title = turn["title"] if turn["title"] else ""
    except (KeyError, IndexError):
        title = ""

    lines = [
        f"# Tour {turn_number}{' — ' + title if title else ''}",
        "",
        f"📅 **{discord_date or 'Date inconnue'}** | "
        f"📊 **{len(segments)} segments** | "
        f"🎯 **{len(new_entities)} nouvelles entités**",
        "",
    ]

    if summary:
        lines.extend([f"> {summary}", ""])

    # Stats section
    lines.extend([
        "## 📊 Statistiques du tour",
        "",
    ])

    if new_entities:
        new_names = ", ".join(f"`{_capitalize_entity(e['canonical_name'])}`" for e in new_entities[:10])
        lines.append(f"- **Entités découvertes** : {new_names}")
    else:
        lines.append("- **Entités découvertes** : aucune")

    lines.extend([
        f"- **Mentions totales** : {total_mentions}",
        f"- **Technologies** : {len(technologies)}",
        f"- **Ressources** : {len(resources)}",
        f"- **Densité narrative** : {len(segments_by_type['narrative'])} narratifs, "
        f"{len(segments_by_type['choice'])} choix, {len(segments_by_type['consequence'])} conséquences",
        "",
    ])

    # Media links (YouTube embeds)
    if media_links:
        lines.extend(["## 🎵 Ambiance", ""])
        for link in media_links:
            if isinstance(link, dict) and link.get("type") == "youtube":
                video_id = link.get("video_id", "")
                lines.append(f"[YouTube](https://www.youtube.com/watch?v={video_id})")
                lines.append("")

    # Question MJ section
    lines.extend([
        "## 🎭 Question du Maître du Jeu",
        "",
    ])

    # Narrative segments
    if segments_by_type["narrative"] or segments_by_type["description"]:
        lines.extend(["### 📖 Récit", ""])
        for content in segments_by_type["narrative"]:
            cleaned = _clean_segment_content(content)
            if cleaned:
                lines.append(cleaned)
                lines.append("")
        for content in segments_by_type["description"]:
            cleaned = _clean_segment_content(content)
            if cleaned:
                lines.append(cleaned)
                lines.append("")

    # Choices proposed
    if choices_proposed or segments_by_type["choice"]:
        lines.extend(["### ⚖️ Choix proposés", ""])
        if choices_proposed:
            for choice in choices_proposed:
                lines.append(f"- {choice}")
        else:
            for content in segments_by_type["choice"]:
                cleaned = _clean_segment_content(content)
                if cleaned:
                    lines.append(cleaned)
                    lines.append("")
        lines.append("")

    # Player response section
    if player_messages:
        player_display = player_name if player_name else player_messages[0]["author"]
        lines.extend([
            f"## 💬 Réponse de {player_display}",
            "",
        ])
        for pm in player_messages:
            content = _clean_segment_content(pm["content"])
            if content:
                lines.append(content)
                lines.append("")

    # Consequences section
    if segments_by_type["consequence"]:
        lines.extend([
            "## 🎯 Conséquences",
            "",
        ])
        for content in segments_by_type["consequence"]:
            cleaned = _clean_segment_content(content)
            if cleaned:
                lines.append(cleaned)
                lines.append("")

    # Discoveries section
    has_discoveries = any([geography, technologies, resources, beliefs])
    if has_discoveries:
        lines.extend(["## 🔍 Découvertes", ""])

        if geography:
            lines.extend(["### 🗺️ Géographie", ""])
            for geo in geography[:10]:
                lines.append(f"- {geo}")
            lines.append("")

        if technologies:
            lines.extend(["### 🔧 Technologies", ""])
            for tech in technologies[:10]:
                lines.append(f"- {tech}")
            lines.append("")

        if resources:
            lines.extend(["### 🌾 Ressources", ""])
            for res in resources[:10]:
                lines.append(f"- {res}")
            lines.append("")

        if beliefs:
            lines.extend(["### ✨ Croyances", ""])
            for belief in beliefs[:10]:
                lines.append(f"- {belief}")
            lines.append("")

    # Entities mentioned
    if entities:
        lines.extend(["## 🏷️ Entités mentionnées", ""])
        for e in entities:
            if is_noise_entity(e["canonical_name"]):
                continue
            name = _capitalize_entity(e["canonical_name"])
            etype = _entity_type_label(e["entity_type"])
            new_marker = " ⭐ *Première apparition*" if e["is_new"] else ""
            lines.append(f"**{name}** ({etype}) — {e['mentions_in_turn']} mentions{new_marker}")
            lines.append("")

    lines.extend(["---", ""])

    # Raw Discord messages
    if message_groups:
        lines.extend([
            "## 📜 Messages Discord originaux",
            "",
        ])
        for group in message_groups:
            role_label = "Maître du Jeu" if group["is_gm"] else group["author"]
            lines.append(f"### {role_label}")
            lines.append("")
            content = _clean_segment_content(group["content"])
            if content:
                # Downgrade headers in content
                content = re.sub(r"^### ", "#### ", content, flags=re.MULTILINE)
                lines.append(content)
                lines.append("")

    return "\n".join(lines)


def generate_turn_index(
    conn: sqlite3.Connection,
    civ_id: int,
    civ_name: str,
) -> str:
    """Generate turn index page with list and previews.

    Creates turns/index.md with:
    - List of all turns
    - Preview summary for each
    - Link to individual turn page

    Args:
        conn: Database connection
        civ_id: Civilization ID
        civ_name: Civilization name

    Returns:
        Markdown content for the turn index page
    """
    from generate import _clean_summary, _parse_json_list

    turns = conn.execute(
        "SELECT * FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
        (civ_id,),
    ).fetchall()

    lines = [
        f"# {civ_name} — Tours de jeu",
        "",
        f"**{len(turns)} tours** enregistrés.",
        "",
    ]

    for turn in turns:
        turn_number = turn["turn_number"]
        # Check if title column exists and has value
        try:
            title = turn["title"] if turn["title"] else ""
        except (KeyError, IndexError):
            title = ""
        summary = _clean_summary(turn["summary"] or "")[:150]

        # Get Discord date
        raw_ids = _parse_json_list(turn["raw_message_ids"])
        discord_date = ""
        if raw_ids:
            first_msg = conn.execute(
                "SELECT timestamp FROM turn_raw_messages WHERE id = ?",
                (int(raw_ids[0]),)
            ).fetchone()
            if first_msg:
                try:
                    dt = datetime.fromisoformat(first_msg["timestamp"].replace("Z", "+00:00"))
                    discord_date = dt.strftime("%d/%m/%Y")
                except (ValueError, AttributeError):
                    pass

        # Count entities
        entity_count = conn.execute(
            "SELECT COUNT(DISTINCT entity_id) FROM entity_mentions WHERE turn_id = ?",
            (turn["id"],)
        ).fetchone()[0]

        title_display = f" — {title}" if title else ""
        date_display = f"*{discord_date}*" if discord_date else ""

        lines.extend([
            f"## [Tour {turn_number}{title_display}](turn-{turn_number:02d}.md)",
            "",
            f"{date_display} | {entity_count} entités mentionnées",
            "",
            f"> {summary}{'...' if len(turn['summary'] or '') > 150 else ''}",
            "",
        ])

    return "\n".join(lines)
