"""Entity profiler — builds rich descriptions and history for each entity via LLM.

Étage 0 of the alias resolution pipeline. For each entity in the database,
aggregates all mention contexts across turns and asks the LLM to produce:
  - A factual description
  - A chronological history
  - Any known aliases/alternative names found in the text

These profiles enrich the wiki AND feed into alias detection (alias_resolver.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import ollama

from . import llm_stats
from .db import get_connection, update_progress


@dataclass
class EntityProfile:
    """Rich profile for a single entity, built from all its mentions."""
    entity_id: int
    canonical_name: str
    entity_type: str
    civ_id: int | None
    description: str = ""
    history: list[str] = field(default_factory=list)
    aliases_suggested: list[str] = field(default_factory=list)
    raw_relations: list[dict] = field(default_factory=list)
    mention_count: int = 0
    mention_contexts: list[str] = field(default_factory=list)


DEFAULT_MODEL = "llama3.1:8b"
NUM_CTX = 8192
RICH_CONTEXT_WINDOW = 800

PROFILE_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.

Voici les passages complets mentionnant l'entité "{name}" (type: {entity_type}) dans la partie :

{mentions}

Produis :
1. **description** : Description factuelle de cette entité (3-6 phrases). Qui/quoi est-ce ? Quel rôle joue-t-elle ? Quelles sont ses caractéristiques notables ?
2. **turn_summaries** : Pour CHAQUE tour où l'entité apparaît, un résumé de 2-4 phrases expliquant ce qui se passe avec/autour de cette entité dans ce tour. Format : {{"Tour X": "résumé..."}}
3. **aliases** : Les autres noms/appellations utilisés pour cette MÊME entité dans les extraits
4. **relations** : Les relations avec d'autres entités NOMMÉES dans les extraits. Types possibles : located_in, member_of, created_by, allied_with, controls, part_of, produces, worships, enemy_of, trades_with. Format : [{{"target": "Nom exact de l'autre entité", "type": "type_relation", "description": "brève explication"}}]

Règles :
- Base-toi UNIQUEMENT sur les extraits fournis, n'invente rien
- Sois précis et factuel, cite les détails importants (noms, lieux, événements)
- Pour turn_summaries : résume le CONTEXTE et le RÔLE de l'entité, pas juste "elle est mentionnée"
- Pour les alias : ne liste que ceux EXPLICITEMENT présents dans les extraits
- Pour les relations : ne liste que des relations EXPLICITES dans les extraits, avec le nom exact de l'entité cible

Réponds UNIQUEMENT en JSON :
{{"description": "...", "turn_summaries": {{"Tour 1": "...", "Tour 5": "..."}}, "aliases": ["..."], "relations": [{{"target": "...", "type": "...", "description": "..."}}]}}"""


def _find_rich_context_for_mention(
    conn,
    mention_text: str,
    turn_number: int,
    fallback_context: str | None,
    segment_cache: dict[int, list[str]],
) -> str:
    """Find a rich context excerpt for a mention by searching turn segments."""
    if turn_number not in segment_cache:
        segments = conn.execute(
            """SELECT s.content FROM turn_segments s
               JOIN turn_turns t ON s.turn_id = t.id
               WHERE t.turn_number = ?
               ORDER BY s.segment_order""",
            (turn_number,),
        ).fetchall()
        segment_cache[turn_number] = [s["content"] for s in segments]

    mention_lower = mention_text.lower()
    for seg_content in segment_cache[turn_number]:
        pos = seg_content.lower().find(mention_lower)
        if pos != -1:
            half = RICH_CONTEXT_WINDOW // 2
            start = max(0, pos - half)
            end = min(len(seg_content), pos + len(mention_text) + half)
            return seg_content[start:end].strip()

    return (fallback_context or "").strip()


def _get_existing_turn_summaries(history_json: str | None) -> dict[int, str]:
    """Parse existing history JSON to extract turn number -> summary mapping."""
    if not history_json:
        return {}

    try:
        history = json.loads(history_json)
    except json.JSONDecodeError:
        return {}

    turn_map = {}
    for entry in history:
        if not isinstance(entry, str):
            continue
        # Format: "Tour X: résumé"
        match = re.match(r"Tour (\d+):\s*(.*)", entry)
        if match:
            turn_num = int(match.group(1))
            summary = match.group(2)
            turn_map[turn_num] = summary

    return turn_map


def _merge_turn_summaries(existing: dict[int, str], new: dict[int, str]) -> list[str]:
    """Merge existing and new turn summaries, sorted by turn number."""
    merged = {**existing, **new}  # new overwrites existing if duplicate
    return [f"Tour {k}: {v}" for k, v in sorted(merged.items())]


def build_entity_profiles(
    db_path: str,
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
    incremental: bool = True,
    run_id: int | None = None,
    track_progress: bool = False,
) -> list[EntityProfile]:
    """Build rich profiles for all active entities in the database.

    Makes 1 LLM call per entity with full segment context. Returns profiles
    and stores description + turn_summaries in entity_entities.

    Args:
        db_path: Path to database
        model: Ollama model name
        use_llm: Whether to use LLM (if False, skip profiling)
        incremental: If True, only process entities with new mentions in recently processed turns
        run_id: Pipeline run ID for progress tracking
        track_progress: Whether to track progress in pipeline_progress table
    """
    conn = get_connection(db_path)

    effective_run_id: int | None = None
    if incremental:
        # Get entities that have mentions in newly processed turns (last pipeline run)
        # Use provided run_id, or fall back to the most recent pipeline_run_id
        if run_id is None:
            row = conn.execute("SELECT MAX(pipeline_run_id) as max_id FROM pipeline_turn_status").fetchone()
            effective_run_id = row["max_id"] if row and row["max_id"] is not None else 0
        else:
            effective_run_id = run_id
        entities = conn.execute("""
            SELECT DISTINCT e.id, e.canonical_name, e.entity_type, e.civ_id, e.history, e.description
            FROM entity_entities e
            JOIN entity_mentions m ON e.id = m.entity_id
            JOIN turn_turns t ON m.turn_id = t.id
            JOIN pipeline_turn_status pts ON t.id = pts.turn_id
            WHERE e.is_active = 1
            AND pts.pipeline_run_id = ?
            ORDER BY e.id
        """, (effective_run_id,)).fetchall()
    else:
        # Full reprocess: all entities
        entities = conn.execute("""
            SELECT e.id, e.canonical_name, e.entity_type, e.civ_id, e.history, e.description
            FROM entity_entities e
            WHERE e.is_active = 1
            ORDER BY e.id
        """).fetchall()

    # Shared segment cache across all entities
    segment_cache: dict[int, list[str]] = {}

    profiles: list[EntityProfile] = []
    total = len(entities)

    for i, row in enumerate(entities):
        entity_id = row["id"]
        name = row["canonical_name"]
        entity_type = row["entity_type"]
        civ_id = row["civ_id"]
        existing_history = row["history"]
        existing_description = row["description"]

        # In incremental mode, get only mentions from newly processed turns
        # In full mode, get all mentions
        if incremental and effective_run_id:
            mentions = conn.execute("""
                SELECT m.mention_text, m.context, t.turn_number
                FROM entity_mentions m
                JOIN turn_turns t ON m.turn_id = t.id
                JOIN pipeline_turn_status pts ON t.id = pts.turn_id
                WHERE m.entity_id = ?
                AND pts.pipeline_run_id = ?
                ORDER BY t.turn_number
            """, (entity_id, effective_run_id)).fetchall()
        else:
            mentions = conn.execute("""
                SELECT m.mention_text, m.context, t.turn_number
                FROM entity_mentions m
                JOIN turn_turns t ON m.turn_id = t.id
                WHERE m.entity_id = ?
                ORDER BY t.turn_number
            """, (entity_id,)).fetchall()

        mention_contexts = [m["context"] for m in mentions if m["context"]]

        profile = EntityProfile(
            entity_id=entity_id,
            canonical_name=name,
            entity_type=entity_type,
            civ_id=civ_id,
            mention_count=len(mentions),
            mention_contexts=mention_contexts,
        )

        if use_llm and mentions:
            # Build rich contexts from segments, grouped by turn, deduplicated
            by_turn: dict[int, list[str]] = {}
            for m in mentions:
                turn_num = m["turn_number"]
                rich_ctx = _find_rich_context_for_mention(
                    conn, m["mention_text"], turn_num,
                    m["context"], segment_cache,
                )
                if not rich_ctx:
                    continue
                by_turn.setdefault(turn_num, []).append(rich_ctx)

            # Deduplicate and format per turn
            mention_lines = []
            for turn_num in sorted(by_turn.keys()):
                seen: set[str] = set()
                for ctx in by_turn[turn_num]:
                    # Deduplicate by first 100 chars
                    key = ctx[:100].lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    mention_lines.append(f"--- Tour {turn_num} ---\n{ctx}")

            if mention_lines:
                mentions_text = "\n\n".join(mention_lines)
                # Trim if too long for context window
                if len(mentions_text) > 6000:
                    mentions_text = mentions_text[:6000] + "\n[...tronqué...]"

                prompt = PROFILE_PROMPT.format(
                    name=name,
                    entity_type=entity_type,
                    mentions=mentions_text,
                )

                try:
                    data = _call_ollama(model, prompt)
                    profile.description = data.get("description", "")

                    # Convert turn_summaries dict to sorted list
                    turn_summaries = data.get("turn_summaries", {})
                    if isinstance(turn_summaries, dict):
                        profile.history = [
                            f"{k}: {v}" for k, v in sorted(
                                turn_summaries.items(),
                                key=lambda x: _extract_turn_number(x[0]),
                            )
                        ]
                    elif isinstance(turn_summaries, list):
                        profile.history = turn_summaries
                    else:
                        # Fallback to old format
                        profile.history = data.get("history", [])

                    raw_aliases = data.get("aliases", [])
                    profile.aliases_suggested = [
                        a.strip() for a in raw_aliases
                        if isinstance(a, str) and a.strip() and a.strip().lower() != name.lower()
                    ]

                    raw_relations = data.get("relations", [])
                    if isinstance(raw_relations, list):
                        profile.raw_relations = [
                            r for r in raw_relations
                            if isinstance(r, dict) and r.get("target") and r.get("type")
                        ]
                except Exception as e:
                    print(f"       WARNING: LLM failed for '{name}': {e}")

        profiles.append(profile)

        # Store in DB - merge with existing if incremental
        if profile.description or profile.history:
            if incremental and existing_history:
                # Merge new turn summaries with existing ones
                existing_turns = _get_existing_turn_summaries(existing_history)

                # Parse new summaries from profile.history
                new_turns = {}
                for entry in profile.history:
                    match = re.match(r"Tour (\d+):\s*(.*)", entry)
                    if match:
                        turn_num = int(match.group(1))
                        summary = match.group(2)
                        new_turns[turn_num] = summary

                # Merge
                merged_history = _merge_turn_summaries(existing_turns, new_turns)
                history_json = json.dumps(merged_history, ensure_ascii=False) if merged_history else existing_history

                # Keep existing description if we didn't generate a new one
                final_description = profile.description if profile.description else existing_description
            else:
                # Full mode: replace everything
                history_json = json.dumps(profile.history, ensure_ascii=False) if profile.history else None
                final_description = profile.description

            conn.execute(
                """UPDATE entity_entities
                   SET description = ?, history = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (final_description, history_json, entity_id),
            )

        # Commit every 10 entities to avoid losing progress on crash
        if (i + 1) % 10 == 0 or i == total - 1:
            conn.commit()
            print(f"       -> Profiled {i + 1}/{total} entities (committed)")

            # Update progress tracking
            if track_progress and run_id:
                update_progress(
                    conn, run_id, "profiler", civ_id, None,
                    i + 1, total, "entity", "running"
                )

    # Mark profiler phase as completed
    if track_progress and run_id and total > 0:
        # Get a civ_id for progress tracking (use first entity's civ_id)
        first_civ_id = entities[0]["civ_id"] if entities else None
        update_progress(
            conn, run_id, "profiler", first_civ_id, None,
            total, total, "entity", "completed"
        )

    # Resolve and insert relations
    if use_llm:
        relations_count = _resolve_and_insert_relations(conn, profiles, incremental=incremental)
        print(f"       -> {relations_count} relations inserted")

    conn.close()

    described = sum(1 for p in profiles if p.description)
    print(f"       -> {described}/{total} entities got LLM descriptions")

    return profiles


VALID_RELATION_TYPES = {
    "located_in", "member_of", "created_by", "allied_with", "controls",
    "part_of", "produces", "worships", "enemy_of", "trades_with",
}


def _resolve_and_insert_relations(conn, profiles: list[EntityProfile], incremental: bool = False) -> int:
    """Resolve raw LLM relations to entity IDs and insert into entity_relations.

    Uses fuzzy matching: exact match on canonical_name first, then case-insensitive
    LIKE match, then alias lookup. Deduplicates (source, target, type) pairs.

    In incremental mode, only removes/replaces relations for the entities in the current
    batch (preserving relations from prior runs for unaffected entities).
    In full mode, clears all relations before reinserting.
    """
    # Build entity name -> id lookup (canonical + aliases)
    all_entities = conn.execute(
        "SELECT id, canonical_name, civ_id FROM entity_entities WHERE is_active = 1"
    ).fetchall()
    name_to_id: dict[str, int] = {}
    for e in all_entities:
        name_to_id[e["canonical_name"].lower()] = e["id"]

    all_aliases = conn.execute(
        "SELECT entity_id, alias FROM entity_aliases"
    ).fetchall()
    for a in all_aliases:
        name_to_id[a["alias"].lower()] = a["entity_id"]

    if incremental:
        # Only delete relations for entities we are about to reprocess
        source_ids = [p.entity_id for p in profiles if p.raw_relations]
        if source_ids:
            placeholders = ",".join("?" * len(source_ids))
            conn.execute(
                f"DELETE FROM entity_relations WHERE source_entity_id IN ({placeholders})",
                source_ids,
            )
    else:
        # Full mode: clear all relations (regenerate from scratch)
        conn.execute("DELETE FROM entity_relations")

    inserted = 0
    seen: set[tuple[int, int, str]] = set()

    for profile in profiles:
        source_id = profile.entity_id
        for rel in profile.raw_relations:
            target_name = rel["target"].strip()
            rel_type = rel["type"].strip().lower()
            description = rel.get("description", "")

            # Validate relation type
            if rel_type not in VALID_RELATION_TYPES:
                continue

            # Resolve target entity
            target_id = name_to_id.get(target_name.lower())
            if target_id is None:
                # Fuzzy: try LIKE match
                row = conn.execute(
                    "SELECT id FROM entity_entities WHERE LOWER(canonical_name) LIKE ? AND is_active = 1 LIMIT 1",
                    (f"%{target_name.lower()}%",),
                ).fetchone()
                if row:
                    target_id = row["id"]

            if target_id is None or target_id == source_id:
                continue

            # Deduplicate
            key = (source_id, target_id, rel_type)
            if key in seen:
                continue
            seen.add(key)

            conn.execute(
                """INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, description)
                   VALUES (?, ?, ?, ?)""",
                (source_id, target_id, rel_type, description),
            )
            inserted += 1

    conn.commit()
    return inserted


def _extract_turn_number(key: str) -> int:
    """Extract turn number from a key like 'Tour 14'."""
    match = re.search(r'\d+', key)
    return int(match.group()) if match else 0


def _call_ollama(model: str, prompt: str) -> dict:
    """Call Ollama and parse JSON response."""
    llm_stats.increment("entity_profiling")
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"num_ctx": NUM_CTX},
    )
    raw = response["message"]["content"]
    return _parse_json_response(raw)


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}
