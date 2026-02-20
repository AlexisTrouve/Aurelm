"""Alias resolver — detects and confirms entity aliases via pattern matching + LLM.

Two-stage pipeline after entity profiling:

  Stage 1 (Pattern Matching): Finds candidate alias pairs using:
    - LLM-suggested aliases from entity profiles (étage 0 output)
    - Appositive patterns in mention contexts ("X, aussi appelé Y")
    - Description keyword overlap between same-type entities

  Stage 2 (LLM Confirmation): Confirms each candidate with a targeted LLM call
    that receives both entity profiles for context-rich comparison.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import ollama

from .db import get_connection
from .entity_profiler import EntityProfile


@dataclass
class AliasCandidate:
    """A candidate alias pair with the reason it was flagged."""
    entity_a: EntityProfile
    entity_b: EntityProfile
    reason: str
    source: str  # "llm_suggested", "appositive_pattern", "description_overlap"


@dataclass
class ConfirmedAlias:
    """A confirmed alias relationship."""
    primary_entity_id: int
    primary_name: str
    alias_entity_id: int
    alias_name: str
    confidence: str  # high, medium, low
    reasoning: str


DEFAULT_MODEL = "llama3.1:8b"
NUM_CTX = 8192

# Appositive patterns that indicate aliases in French game text
ALIAS_PATTERNS = [
    re.compile(
        r"(?:aussi|également)\s+(?:appelée?s?|nommée?s?|connue?s?\s+sous(?:\s+le\s+nom\s+(?:de|d'))?)\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:surnommée?s?|baptisée?s?)\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"c['\u2019]est-à-dire\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    # "X ou Y" when X is an entity name nearby
    re.compile(
        r"\bou\s+(?:les?\s+|l['\u2019])?([A-Z][a-zà-ÿ]+(?:[\s-][A-Za-zà-ÿ]+)*)",
    ),
]


CONFIRM_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.

On soupçonne que ces deux entités sont en fait la MÊME entité sous des noms différents.

Entité 1 : "{name_a}" (type: {type_a})
Description : {desc_a}

Entité 2 : "{name_b}" (type: {type_b})
Description : {desc_b}

Raison du soupçon : {reason}

Question : Ces deux entités désignent-elles la MÊME chose/personne/lieu/concept ?

Règles :
- Réponds UNIQUEMENT sur la base des descriptions fournies
- En cas de doute, réponds false — mieux vaut rater un alias que fusionner deux entités différentes
- "high" = certain, "medium" = probable, "low" = possible mais incertain

Réponds UNIQUEMENT en JSON : {{"same_entity": true, "confidence": "high/medium/low", "reasoning": "..."}}"""


def find_alias_candidates(profiles: list[EntityProfile]) -> list[AliasCandidate]:
    """Stage 1: Find candidate alias pairs using deterministic pattern matching."""
    candidates: list[AliasCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()

    # Index profiles by normalized name
    name_index: dict[str, EntityProfile] = {}
    for p in profiles:
        name_index[p.canonical_name.lower().strip()] = p

    # --- Signal 1: LLM-suggested aliases from profiling ---
    for p in profiles:
        for alias in p.aliases_suggested:
            alias_lower = alias.lower().strip()
            if alias_lower in name_index:
                other = name_index[alias_lower]
                if other.entity_id != p.entity_id:
                    # Cross-type guard: different types can't be aliases
                    if p.entity_type != other.entity_type:
                        continue
                    pair = _pair_key(p.entity_id, other.entity_id)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        candidates.append(AliasCandidate(
                            entity_a=p,
                            entity_b=other,
                            reason=f"Le profil de '{p.canonical_name}' mentionne '{alias}' comme alias",
                            source="llm_suggested",
                        ))

    # --- Signal 2: Appositive patterns in raw mention contexts ---
    for p in profiles:
        for ctx in p.mention_contexts:
            ctx_lower = ctx.lower()
            if p.canonical_name.lower() not in ctx_lower:
                continue
            for pattern in ALIAS_PATTERNS:
                for match in pattern.finditer(ctx):
                    alias_text = match.group(1).strip().rstrip(".,;:!?")
                    alias_lower = alias_text.lower()
                    if alias_lower in name_index:
                        other = name_index[alias_lower]
                        if other.entity_id != p.entity_id:
                            # Cross-type guard
                            if p.entity_type != other.entity_type:
                                continue
                            pair = _pair_key(p.entity_id, other.entity_id)
                            if pair not in seen_pairs:
                                seen_pairs.add(pair)
                                candidates.append(AliasCandidate(
                                    entity_a=p,
                                    entity_b=other,
                                    reason=f"Pattern appositif : '{ctx.strip()[:100]}'",
                                    source="appositive_pattern",
                                ))

    # --- Signal 3: Description keyword overlap (same entity_type only) ---
    by_type: dict[str, list[EntityProfile]] = {}
    for p in profiles:
        if p.description:
            by_type.setdefault(p.entity_type, []).append(p)

    for _etype, type_profiles in by_type.items():
        for i, pa in enumerate(type_profiles):
            for pb in type_profiles[i + 1:]:
                pair = _pair_key(pa.entity_id, pb.entity_id)
                if pair in seen_pairs:
                    continue
                overlap = _description_overlap(pa.description, pb.description)
                if overlap > 0.6:  # Conservative threshold
                    seen_pairs.add(pair)
                    candidates.append(AliasCandidate(
                        entity_a=pa,
                        entity_b=pb,
                        reason=f"Descriptions très similaires ({overlap:.0%} overlap)",
                        source="description_overlap",
                    ))

    return candidates


def confirm_aliases(
    candidates: list[AliasCandidate],
    model: str = DEFAULT_MODEL,
) -> list[ConfirmedAlias]:
    """Stage 2: Confirm alias candidates with targeted LLM calls."""
    confirmed: list[ConfirmedAlias] = []

    for j, candidate in enumerate(candidates):
        a = candidate.entity_a
        b = candidate.entity_b

        prompt = CONFIRM_PROMPT.format(
            name_a=a.canonical_name,
            type_a=a.entity_type,
            desc_a=a.description or "(pas de description disponible)",
            name_b=b.canonical_name,
            type_b=b.entity_type,
            desc_b=b.description or "(pas de description disponible)",
            reason=candidate.reason,
        )

        try:
            data = _call_ollama(model, prompt)
        except Exception as e:
            print(f"       WARNING: LLM confirmation failed for "
                  f"'{a.canonical_name}' <-> '{b.canonical_name}': {e}")
            continue

        if data.get("same_entity"):
            # Primary = most mentions
            if a.mention_count >= b.mention_count:
                primary, alias_ent = a, b
            else:
                primary, alias_ent = b, a

            confirmed.append(ConfirmedAlias(
                primary_entity_id=primary.entity_id,
                primary_name=primary.canonical_name,
                alias_entity_id=alias_ent.entity_id,
                alias_name=alias_ent.canonical_name,
                confidence=data.get("confidence", "medium"),
                reasoning=data.get("reasoning", ""),
            ))

        print(f"       -> Confirmed {j + 1}/{len(candidates)} candidates")

    return confirmed


def store_aliases(db_path: str, aliases: list[ConfirmedAlias]) -> int:
    """Store confirmed aliases in the entity_aliases table."""
    conn = get_connection(db_path)
    stored = 0

    for alias in aliases:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
                (alias.primary_entity_id, alias.alias_name),
            )
            stored += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return stored


def resolve_aliases(
    db_path: str,
    profiles: list[EntityProfile],
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
) -> dict:
    """Full alias resolution: find candidates -> confirm -> store.

    Returns stats dict with counts.
    """
    stats = {"candidates_found": 0, "aliases_confirmed": 0, "aliases_stored": 0}

    # Stage 1: Pattern matching
    candidates = find_alias_candidates(profiles)
    stats["candidates_found"] = len(candidates)

    if not candidates:
        print("       -> No alias candidates found")
        return stats

    print(f"       -> {len(candidates)} alias candidates found:")
    for c in candidates:
        print(f"          '{c.entity_a.canonical_name}' <-> "
              f"'{c.entity_b.canonical_name}' [{c.source}]")

    if not use_llm:
        print("       -> Skipping LLM confirmation (--no-llm)")
        return stats

    # Stage 2: LLM confirmation
    confirmed = confirm_aliases(candidates, model)
    stats["aliases_confirmed"] = len(confirmed)

    if confirmed:
        print(f"       -> {len(confirmed)} aliases confirmed:")
        for a in confirmed:
            print(f"          '{a.primary_name}' = '{a.alias_name}' "
                  f"[{a.confidence}] {a.reasoning}")

        stats["aliases_stored"] = store_aliases(db_path, confirmed)
    else:
        print("       -> No aliases confirmed by LLM")

    return stats


def _pair_key(id_a: int, id_b: int) -> tuple[int, int]:
    """Canonical pair key to avoid duplicate checks."""
    return (min(id_a, id_b), max(id_a, id_b))


def _description_overlap(desc_a: str, desc_b: str) -> float:
    """Compute keyword overlap ratio between two descriptions."""
    stop_words = {
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "est", "sont",
        "qui", "que", "dans", "pour", "par", "sur", "avec", "ce", "cette", "ces",
        "il", "elle", "ils", "elles", "en", "au", "aux", "se", "sa", "son", "ses",
        "a", "à", "l", "d", "n", "s", "y", "ou", "pas", "plus", "aussi", "être",
        "fait", "leur", "leurs", "ont", "été", "très", "tout", "tous", "toute",
    }
    words_a = {w.lower() for w in re.findall(r"\w+", desc_a)
               if len(w) > 2 and w.lower() not in stop_words}
    words_b = {w.lower() for w in re.findall(r"\w+", desc_b)
               if len(w) > 2 and w.lower() not in stop_words}

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller if smaller > 0 else 0.0


def _call_ollama(model: str, prompt: str) -> dict:
    """Call Ollama and parse JSON response."""
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"num_ctx": NUM_CTX},
        keep_alive=60,  # 60s idle timeout instead of default 5min
    )
    raw = response["message"]["content"]
    return _parse_json_response(raw)


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response."""
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
