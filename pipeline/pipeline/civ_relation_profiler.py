"""Civ relation profiler — synthesizes inter-civilization relationships via LLM.

For each (source_civ, target_civ) pair that has accumulated civ_mentions,
collects all mention contexts chronologically and runs a single LLM call to
produce a unilateral relationship profile:

  - opinion   : allied | friendly | neutral | suspicious | hostile | unknown
  - description : factual narrative of how source_civ perceives target_civ
  - treaties  : list of agreements/treaties detected in the contexts

One row per directional pair in civ_relations — A→B and B→A are independent.
Analogous pattern to entity_profiler.py.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from .db import get_connection
from .llm_provider import LLMProvider


VALID_OPINIONS = {"allied", "friendly", "neutral", "suspicious", "hostile", "unknown"}

PROFILE_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

La civilisation "{source_civ}" a mentionné "{target_civ}" dans les tours suivants :

{contexts}

D'après ces passages, détermine la relation de {source_civ} envers {target_civ} :

1. **opinion** : choisir EXACTEMENT parmi : allied, friendly, neutral, suspicious, hostile, unknown
   - allied    : alliance formelle, coopération active
   - friendly  : relations positives, bonne volonté
   - neutral   : ni hostile ni favorable, peu de contact
   - suspicious: méfiance, prudence, tensions latentes
   - hostile   : conflit ouvert, hostilité déclarée
   - unknown   : pas assez d'information pour déterminer
2. **description** : résumé factuel de la relation (2-4 phrases). Comment {source_civ} perçoit {target_civ} ? Quels événements ont forgé cette relation ?
3. **treaties** : liste des accords, traités, pactes ou engagements EXPLICITEMENT mentionnés dans les passages. Liste vide si aucun.

Règles :
- Base-toi UNIQUEMENT sur les passages fournis, n'invente rien
- Si les passages sont insuffisants pour déterminer l'opinion, utilise "unknown"
- Pour les traités : ne liste que ce qui est explicitement nommé dans les textes

Réponds UNIQUEMENT en JSON :
{{"opinion": "...", "description": "...", "treaties": ["...", "..."]}}"""


def _build_contexts_text(mentions: list[dict]) -> str:
    """Format mention rows as 'Tour X: [context]' for the LLM prompt."""
    lines = []
    for m in mentions:
        turn_num = m.get("turn_number", "?")
        ctx = (m.get("context") or "").strip()
        if ctx:
            lines.append(f"Tour {turn_num}: {ctx}")
    return "\n\n".join(lines) if lines else "(aucun contexte disponible)"


def _parse_profile_response(response: str) -> dict:
    """Extract opinion + description + treaties from LLM JSON response."""
    text = response.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    opinion = data.get("opinion", "unknown")
    if opinion not in VALID_OPINIONS:
        opinion = "unknown"

    description = data.get("description") or ""
    if not isinstance(description, str):
        description = str(description)

    treaties = data.get("treaties") or []
    if not isinstance(treaties, list):
        treaties = []
    treaties = [str(t) for t in treaties if t]

    return {"opinion": opinion, "description": description, "treaties": treaties}


def build_civ_relations(
    db_path: str,
    source_civ_id: int,
    model: str = "llama3.1:8b",
    provider: LLMProvider | None = None,
    use_llm: bool = True,
) -> dict:
    """Profile all inter-civ relations for source_civ_id.

    Finds all target civs that appear in source_civ's civ_mentions,
    aggregates contexts per pair, calls LLM, and upserts civ_relations.

    Returns stats dict: {"relations_built": N, "pairs_found": M}
    """
    conn = get_connection(db_path)
    stats = {"relations_built": 0, "pairs_found": 0}

    try:
        # Find all target civs that source_civ has mentioned
        pairs = conn.execute(
            """SELECT DISTINCT m.target_civ_id, c.name as target_name
               FROM civ_mentions m
               JOIN civ_civilizations c ON c.id = m.target_civ_id
               WHERE m.source_civ_id = ?""",
            (source_civ_id,),
        ).fetchall()

        if not pairs:
            return stats

        source_name = conn.execute(
            "SELECT name FROM civ_civilizations WHERE id = ?", (source_civ_id,)
        ).fetchone()["name"]

        stats["pairs_found"] = len(pairs)

        # Load gm_locked relation pairs so we skip them below
        locked_pairs = set()
        try:
            locked_rows = conn.execute(
                "SELECT source_civ_id, target_civ_id FROM civ_relations WHERE gm_lock = 1"
            ).fetchall()
            locked_pairs = {(r["source_civ_id"], r["target_civ_id"]) for r in locked_rows}
        except Exception:
            pass  # gm_lock column may not exist on old DBs

        for pair in pairs:
            target_civ_id = pair["target_civ_id"]
            target_name = pair["target_name"]

            # Skip GM-locked relations — the GM has validated/edited this relation
            if (source_civ_id, target_civ_id) in locked_pairs:
                continue

            # Collect all mention contexts sorted chronologically
            mentions = conn.execute(
                """SELECT m.context, t.turn_number
                   FROM civ_mentions m
                   JOIN turn_turns t ON t.id = m.turn_id
                   WHERE m.source_civ_id = ? AND m.target_civ_id = ?
                   ORDER BY t.turn_number ASC""",
                (source_civ_id, target_civ_id),
            ).fetchall()

            # Get the most recent turn_id for last_turn_id FK
            last_mention = conn.execute(
                """SELECT m.turn_id FROM civ_mentions m
                   JOIN turn_turns t ON t.id = m.turn_id
                   WHERE m.source_civ_id = ? AND m.target_civ_id = ?
                   ORDER BY t.turn_number DESC LIMIT 1""",
                (source_civ_id, target_civ_id),
            ).fetchone()
            last_turn_id = last_mention["turn_id"] if last_mention else None

            if use_llm and provider is not None:
                contexts_text = _build_contexts_text(
                    [dict(m) for m in mentions]
                )
                prompt = PROFILE_PROMPT.format(
                    source_civ=source_name,
                    target_civ=target_name,
                    contexts=contexts_text,
                )
                try:
                    response = provider.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Tu es un archiviste expert pour un JDR de civilisation."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.3,
                        max_tokens=600,
                        num_ctx=8192,
                    )
                    profile = _parse_profile_response(response)
                except Exception as e:
                    print(f"    [warn] LLM call failed for {source_name}->{target_name}: {e}")
                    profile = {
                        "opinion": "unknown",
                        "description": "",
                        "treaties": [],
                    }
            else:
                # No-LLM mode: register the pair as unknown opinion
                profile = {"opinion": "unknown", "description": "", "treaties": []}

            conn.execute(
                """INSERT INTO civ_relations
                       (source_civ_id, target_civ_id, opinion, description,
                        treaties, last_turn_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_civ_id, target_civ_id) DO UPDATE SET
                       opinion      = excluded.opinion,
                       description  = excluded.description,
                       treaties     = excluded.treaties,
                       last_turn_id = excluded.last_turn_id,
                       updated_at   = excluded.updated_at""",
                (
                    source_civ_id,
                    target_civ_id,
                    profile["opinion"],
                    profile["description"] or None,
                    json.dumps(profile["treaties"], ensure_ascii=False) if profile["treaties"] else None,
                    last_turn_id,
                    datetime.now().isoformat(),
                ),
            )
            stats["relations_built"] += 1

        conn.commit()
    finally:
        conn.close()

    return stats
