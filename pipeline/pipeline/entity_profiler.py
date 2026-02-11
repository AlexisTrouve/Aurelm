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

from .db import get_connection


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
    mention_count: int = 0
    mention_contexts: list[str] = field(default_factory=list)


DEFAULT_MODEL = "llama3.1:8b"
NUM_CTX = 8192

PROFILE_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.

Voici toutes les mentions de l'entité "{name}" (type: {entity_type}) dans la partie.

{mentions}

Produis :
1. Une description factuelle de cette entité (2-4 phrases, basée UNIQUEMENT sur les extraits ci-dessus)
2. Une chronologie (liste d'événements clés impliquant cette entité, dans l'ordre des tours)
3. Les autres noms ou appellations utilisés pour désigner cette MÊME entité dans les extraits (alias, surnoms, traductions, variantes orthographiques)

Règles :
- Base-toi UNIQUEMENT sur les extraits fournis, n'invente rien
- Si une seule mention, fais une description courte basée sur le contexte disponible
- La chronologie doit mentionner le numéro de tour
- Pour les alias : ne liste que ceux EXPLICITEMENT présents dans les extraits

Réponds UNIQUEMENT en JSON : {{"description": "...", "history": ["Tour X: ...", ...], "aliases": ["..."]}}"""


def build_entity_profiles(
    db_path: str,
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
) -> list[EntityProfile]:
    """Build rich profiles for all active entities in the database.

    Makes 1 LLM call per entity. Returns profiles and stores
    description + history in entity_entities.
    """
    conn = get_connection(db_path)

    entities = conn.execute("""
        SELECT e.id, e.canonical_name, e.entity_type, e.civ_id
        FROM entity_entities e
        WHERE e.is_active = 1
        ORDER BY e.id
    """).fetchall()

    profiles: list[EntityProfile] = []
    total = len(entities)

    for i, row in enumerate(entities):
        entity_id = row["id"]
        name = row["canonical_name"]
        entity_type = row["entity_type"]
        civ_id = row["civ_id"]

        # Aggregate all mentions with context, ordered by turn
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
            # Format mentions for prompt -- deduplicate identical contexts
            seen_ctx: set[str] = set()
            mention_lines = []
            for m in mentions:
                ctx = m["context"]
                if not ctx or ctx in seen_ctx:
                    continue
                seen_ctx.add(ctx)
                mention_lines.append(f"Tour {m['turn_number']}: \"...{ctx}...\"")

            if mention_lines:
                mentions_text = "\n".join(mention_lines)
                prompt = PROFILE_PROMPT.format(
                    name=name,
                    entity_type=entity_type,
                    mentions=mentions_text,
                )

                try:
                    data = _call_ollama(model, prompt)
                    profile.description = data.get("description", "")
                    profile.history = data.get("history", [])
                    raw_aliases = data.get("aliases", [])
                    # Clean aliases: remove self-references and empties
                    profile.aliases_suggested = [
                        a.strip() for a in raw_aliases
                        if a.strip() and a.strip().lower() != name.lower()
                    ]
                except Exception as e:
                    print(f"       WARNING: LLM failed for '{name}': {e}")

        profiles.append(profile)

        # Store in DB
        if profile.description:
            history_json = json.dumps(profile.history, ensure_ascii=False) if profile.history else None
            conn.execute(
                """UPDATE entity_entities
                   SET description = ?, history = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (profile.description, history_json, entity_id),
            )

        if (i + 1) % 10 == 0 or i == total - 1:
            print(f"       -> Profiled {i + 1}/{total} entities")

    conn.commit()
    conn.close()

    described = sum(1 for p in profiles if p.description)
    print(f"       -> {described}/{total} entities got LLM descriptions")

    return profiles


def _call_ollama(model: str, prompt: str) -> dict:
    """Call Ollama and parse JSON response."""
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
