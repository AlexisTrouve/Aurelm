"""Turn preanalysis — novelty detection + player strategy analysis.

Stage 6.5 in the pipeline (between extraction/summarization and subject extraction).
- analyze_novelty: pure SQL, finds entities first seen this turn
- analyze_player_strategy: 1 LLM call, deduces player intent from PJ text
"""

from __future__ import annotations

import json
import re
import sqlite3

from .llm_provider import LLMProvider
from . import llm_stats

# Valid strategy tags the LLM can assign
STRATEGY_TAGS = [
    "expansion", "diplomatie", "defense", "economie",
    "culture", "exploration", "militaire", "religieux",
]

# Prompt for player strategy analysis — compact, JSON output
_STRATEGY_PROMPT = """/no_think
Tu analyses le texte d'un joueur dans un JDR civilisation. Deduis son intention strategique.

CONTEXTE (tours precedents):
{previous_summaries}

SUJETS OUVERTS (decisions en attente):
{open_subjects}

TEXTE DU JOUEUR (tour actuel):
{pj_text}

Reponds en JSON STRICT:
{{
  "strategy": "1-3 phrases decrivant l'intention strategique du joueur",
  "tags": ["tag1", "tag2"]
}}

Tags possibles: expansion, diplomatie, defense, economie, culture, exploration, militaire, religieux.
Choisis 1-3 tags pertinents. Pas d'autres tags.
JSON UNIQUEMENT, pas de texte avant ou apres."""


def analyze_novelty(conn: sqlite3.Connection, turn_id: int, civ_id: int) -> dict:
    """Detect entities first seen in this turn. Pure SQL, no LLM.

    Finds all entities whose first_seen_turn matches turn_id, groups by type,
    and writes novelty_summary + new_entity_ids to turn_turns.

    Returns:
        Dict with new_entity_ids (list[int]) and novelty_summary (str).
    """
    # Find entities that appeared for the first time in this turn
    rows = conn.execute(
        """SELECT id, canonical_name, entity_type FROM entity_entities
           WHERE first_seen_turn = ? AND civ_id = ? AND disabled = 0
           ORDER BY entity_type, canonical_name""",
        (turn_id, civ_id),
    ).fetchall()

    new_ids = [row["id"] for row in rows]

    if not new_ids:
        # No new entities — store empty results
        conn.execute(
            "UPDATE turn_turns SET novelty_summary = '', new_entity_ids = '[]' WHERE id = ?",
            (turn_id,),
        )
        return {"new_entity_ids": [], "novelty_summary": ""}

    # Group by type for the summary
    by_type: dict[str, list[str]] = {}
    for row in rows:
        by_type.setdefault(row["entity_type"], []).append(row["canonical_name"])

    # Build human-readable summary: "3 nouvelles entites: ..."
    parts = []
    for etype, names in sorted(by_type.items()):
        count = len(names)
        # Truncate name list if too many (keep first 5)
        displayed = names[:5]
        suffix = f" (+{count - 5})" if count > 5 else ""
        parts.append(f"{count} {etype}: {', '.join(displayed)}{suffix}")

    total = len(new_ids)
    novelty_summary = f"{total} nouvelle(s) entite(s). {'; '.join(parts)}."

    new_entity_ids_json = json.dumps(new_ids)
    conn.execute(
        "UPDATE turn_turns SET novelty_summary = ?, new_entity_ids = ? WHERE id = ?",
        (novelty_summary, new_entity_ids_json, turn_id),
    )

    return {"new_entity_ids": new_ids, "novelty_summary": novelty_summary}


def analyze_player_strategy(
    conn: sqlite3.Connection,
    turn_id: int,
    civ_id: int,
    provider: LLMProvider,
    model: str,
) -> dict | None:
    """Analyze PJ text to deduce player strategy. 1 LLM call.

    Loads PJ segments for this turn, last 3 PJ turn summaries for context,
    and open subjects. Skips if no PJ text exists for this turn.

    Returns:
        Dict with strategy (str) and tags (list[str]), or None if skipped.
    """
    # Get PJ segments for this turn
    pj_rows = conn.execute(
        """SELECT content FROM turn_segments
           WHERE turn_id = ? AND source = 'pj'
           ORDER BY segment_order""",
        (turn_id,),
    ).fetchall()

    if not pj_rows:
        return None  # No PJ text — skip

    pj_text = "\n\n".join(row["content"] for row in pj_rows)

    # Get turn_number for context queries
    turn_row = conn.execute(
        "SELECT turn_number FROM turn_turns WHERE id = ?", (turn_id,)
    ).fetchone()
    turn_number = turn_row["turn_number"] if turn_row else 0

    # Load summaries from previous 3 PJ turns (for context)
    prev_turns = conn.execute(
        """SELECT turn_number, summary FROM turn_turns
           WHERE civ_id = ? AND turn_number < ? AND summary IS NOT NULL
           ORDER BY turn_number DESC LIMIT 3""",
        (civ_id, turn_number),
    ).fetchall()
    previous_summaries = "\n".join(
        f"T{r['turn_number']:02d}: {r['summary']}" for r in reversed(prev_turns)
    ) or "(aucun tour precedent)"

    # Load open subjects for this civ
    open_subs = conn.execute(
        """SELECT title, direction FROM subject_subjects
           WHERE civ_id = ? AND status = 'open'""",
        (civ_id,),
    ).fetchall()
    open_subjects = "\n".join(
        f"- [{r['direction']}] {r['title']}" for r in open_subs
    ) or "(aucun sujet ouvert)"

    # Build prompt
    prompt = _STRATEGY_PROMPT.format(
        previous_summaries=previous_summaries,
        open_subjects=open_subjects,
        pj_text=pj_text[:8000],  # Cap to avoid blowing context
    )

    # Call LLM
    response = provider.generate(
        model=model,
        system="Tu es un analyste de JDR civilisation.",
        prompt=prompt,
        temperature=0.3,
        max_tokens=500,
        num_ctx=8192,
    )
    llm_stats.increment("preanalysis")

    # Parse JSON response
    strategy, tags = _parse_strategy_response(response)

    # Write to DB
    conn.execute(
        "UPDATE turn_turns SET player_strategy = ?, strategy_tags = ? WHERE id = ?",
        (strategy, json.dumps(tags), turn_id),
    )

    return {"strategy": strategy, "tags": tags}


def _parse_strategy_response(response: str) -> tuple[str, list[str]]:
    """Extract strategy + tags from LLM JSON response.

    Handles markdown code blocks, partial JSON, and invalid tags gracefully.
    """
    text = response.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return (text[:200], [])
        else:
            return (text[:200], [])

    strategy = str(data.get("strategy", ""))
    raw_tags = data.get("tags", [])

    # Filter to valid tags only
    tags = [t for t in raw_tags if t in STRATEGY_TAGS]

    return (strategy, tags)


def run_preanalysis(
    db_path: str,
    model: str,
    provider: LLMProvider | None,
    civ_id: int | None = None,
    run_id: int | None = None,
    use_llm: bool = True,
) -> dict:
    """Orchestrate preanalysis for turns of a specific civilization (or all).

    Runs novelty detection (always) and player strategy (only if use_llm=True).

    Args:
        civ_id: If provided, only analyze turns for this civ. Otherwise all civs.

    Returns:
        Stats dict with novelty/strategy counts.
    """
    from .db import get_connection

    conn = get_connection(db_path)
    stats = {"turns_analyzed": 0, "new_entities_found": 0, "strategies_analyzed": 0}

    try:
        # Target specific civ or iterate all
        if civ_id is not None:
            civ_ids = [civ_id]
        else:
            civ_ids = [r["civ_id"] for r in conn.execute(
                "SELECT DISTINCT civ_id FROM turn_turns"
            ).fetchall()]

        for cid in civ_ids:
            # Get all turns for this civ, ordered
            turns = conn.execute(
                """SELECT id, turn_number FROM turn_turns
                   WHERE civ_id = ? ORDER BY turn_number""",
                (cid,),
            ).fetchall()

            for turn_row in turns:
                turn_id = turn_row["id"]

                # Novelty detection — always runs (pure SQL)
                novelty = analyze_novelty(conn, turn_id, cid)
                if novelty["new_entity_ids"]:
                    stats["new_entities_found"] += len(novelty["new_entity_ids"])

                # Player strategy — only with LLM
                if use_llm and provider:
                    result = analyze_player_strategy(
                        conn, turn_id, cid, provider, model,
                    )
                    if result:
                        stats["strategies_analyzed"] += 1

                stats["turns_analyzed"] += 1

        conn.commit()
    finally:
        conn.close()

    return stats
