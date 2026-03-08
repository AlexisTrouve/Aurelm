"""LLM-based summarization -- uses Ollama for turn summaries and entity updates.

Multi-call architecture: one LLM call per author (GM / player) per turn,
then merges results into a single TurnSummary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import llm_stats
from .llm_provider import LLMProvider, OllamaProvider


@dataclass
class TurnSummary:
    short_summary: str      # 1-2 sentences
    detailed_summary: str   # Full paragraph
    key_events: list[str] = field(default_factory=list)
    entities_mentioned: list[str] = field(default_factory=list)
    choices_made: list[str] = field(default_factory=list)
    # Descriptors — generated in the same GM call as the summary
    thematic_tags: list[str] = field(default_factory=list)
    tech_era: str = "neolithique"
    tech_era_reasoning: str = ""
    fantasy_level: str = "realiste"
    fantasy_level_reasoning: str = ""


# Predefined thematic tag vocabulary — exhaustive list given to the LLM.
# The LLM picks only from these; no free-form tags allowed.
THEMATIC_TAGS = [
    "technologie",    # new tool, technique or infrastructure developed
    "ressource",      # resource discovery, exploitation or scarcity
    "diplomatie",     # inter-civ contact, alliance, negotiation, trade deal
    "commerce",       # exchange of goods, markets, trade routes
    "crise",          # disaster, famine, disease, internal conflict
    "combat",         # war, raid, battle, violence
    "religion",       # ritual, belief, cult, oracle, spiritual event
    "culture",        # art, music, fresco, storytelling, identity
    "exploration",    # territorial expansion, scouting, prospection
    "politique",      # governance, law, institution creation or crisis
    "migration",      # population movement, settlement, diaspora
    "decouverte",     # significant find (artefact, ruin, species, place)
    "construction",   # building, infrastructure, monument
    "agriculture",    # farming, herding, food production
    "science",        # systematic knowledge, writing, classification
    "mort",           # death, mourning, funerary rite, epidemic
]

# Ordered tech era labels — LLM picks one and may advance/retreat vs prev turn.
TECH_ERAS = [
    "paleolithique",   # flint, hunting, no settlement
    "mesolithique",    # micro-tools, fishing, semi-nomadic
    "neolithique",     # polished stone, farming, permanent villages
    "chalcolithique",  # copper, early metallurgy
    "age-du-bronze",   # bronze, complex cities, writing emerging
    "age-du-fer",      # iron, armies, roads
    "antiquite",       # empires, philosophy, engineering
    "moyen-age",       # feudalism, castles, religion dominant
    "renaissance",     # printing, humanism, early science
    "pre-industriel",  # proto-industry, global trade
]

# Fantasy level labels — LLM assesses based on supernatural elements in the turn.
FANTASY_LEVELS = [
    "realiste",          # zero supernatural — pure human drama
    "low-fantasy",       # subtle: prophecy, spiritual presence, unexplained but rare
    "balanced-fantasy",  # magic/supernatural present and accepted, not dominant
    "high-fantasy",      # magic central to the narrative and society
    "epic-fantasy",      # pervasive magic, divine intervention, legendary scale
]


@dataclass
class AuthorContent:
    """One author's messages within a turn, pre-grouped."""
    author: str
    is_gm: bool
    content: str


DEFAULT_MODEL = "llama3.1:8b"

# Context window for Ollama calls (default 2048 is way too low)
NUM_CTX = 8192

# Practical limit for text sent to LLM per call (~2K tokens prompt + ~6K tokens content)
MAX_CONTENT_CHARS = 16000


GM_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.
Resume la narration du Maitre du Jeu pour ce tour et attribue des descripteurs.{civ_context}

Niveau technologique du tour precedent : {prev_tech_era}
Niveau fantastique du tour precedent : {prev_fantasy_level}

Tags thematiques disponibles (choisis 1 a 5 UNIQUEMENT parmi cette liste) :
{thematic_tags_list}

Niveaux technologiques (du plus bas au plus haut) :
{tech_eras_list}

Niveaux fantastiques (du plus bas au plus haut) :
{fantasy_levels_list}

Extrais :
1. Un resume court (1-2 phrases, factuel, ce qui se passe dans le monde)
2. Un resume detaille (1 paragraphe complet couvrant la narration)
3. Les evenements cles (liste de phrases courtes -- uniquement les faits importants)
4. Les entites mentionnees (noms propres : personnes, lieux, technologies, institutions, castes)
5. Tags thematiques (1 a 5 tags de la liste fournie)
6. Niveau technologique : raisonnement + label exact de la liste
7. Niveau fantastique : raisonnement + label exact de la liste

Regles :
- Le resume court et le resume detaille doivent etre DIFFERENTS
- Utilise les noms propres exacts du texte
- Ignore les liens YouTube, timestamps, et notes hors-jeu
- Ecris du point de vue du Maitre du Jeu
- tech_era et fantasy_level : utilise EXACTEMENT un label de la liste, rien d'autre
- En cas de doute sur la progression, maintiens le niveau du tour precedent

Reponds UNIQUEMENT en JSON :
{{
  "short_summary": "...",
  "detailed_summary": "...",
  "key_events": [...],
  "entities_mentioned": [...],
  "thematic_tags": ["tag1", "tag2"],
  "tech_era_reasoning": "2-3 phrases justifiant le niveau tech",
  "tech_era": "label-exact",
  "fantasy_level_reasoning": "2-3 phrases justifiant le niveau fantastique",
  "fantasy_level": "label-exact"
}}

Narration du MJ :
{text}"""


PLAYER_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.
Resume les actions et decisions du joueur {player_ref} pour ce tour.{civ_context}

Extrais :
1. Un resume court (1-2 phrases, les decisions principales)
2. Les choix effectues (liste de chaque decision prise)
3. Les entites mentionnees dans les choix (noms propres)

Regles :
- Concentre-toi sur les DECISIONS et ACTIONS du joueur, pas sur la narration
- Utilise les noms propres exacts du texte
- Ignore les liens YouTube, timestamps, et notes hors-jeu

Reponds UNIQUEMENT en JSON : {{"short_summary": "...", "choices_made": [...], "entities_mentioned": [...]}}

Actions du joueur :
{text}"""


# Single-call fallback prompt (when no author split available)
SINGLE_PROMPT = """Tu es un archiviste expert pour un JDR de civilisation.
Resume le tour de jeu suivant en francais.{civ_context}

Extrais :
1. Un resume court (1-2 phrases, factuel)
2. Un resume detaille (1 paragraphe complet, couvrant tous les evenements importants)
3. Les evenements cles (liste de phrases courtes)
4. Les entites mentionnees (noms propres : personnes, lieux, technologies, institutions, castes)
5. Les choix effectues par{player_ref} (liste)

Regles :
- Le resume court et le resume detaille doivent etre DIFFERENTS (pas de copier-coller)
- Utilise les noms propres exacts du texte, pas de paraphrase pour les noms
- Ignore les liens YouTube, timestamps, et notes hors-jeu
- Ecris du point de vue du Maitre du Jeu qui narre l'histoire

Reponds UNIQUEMENT en JSON avec les cles : short_summary, detailed_summary, key_events, entities_mentioned, choices_made.

Tour de jeu :
{text}"""


def summarize_turn(
    turn_text: str,
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
    civ_name: str | None = None,
    player_name: str | None = None,
    author_contents: list[AuthorContent] | None = None,
    provider: LLMProvider | None = None,
    prev_tech_era: str = "neolithique",
    prev_fantasy_level: str = "realiste",
) -> TurnSummary:
    """Generate a structured summary + descriptors for a game turn.

    The GM call produces both narrative summary and turn descriptors (thematic
    tags, tech era, fantasy level) in a single LLM call. prev_tech_era and
    prev_fantasy_level are passed so the LLM can reason about progression.
    Falls back to extractive summary (no tags) if LLM is unavailable.
    """
    if not use_llm:
        return _extractive_summary(turn_text, civ_name=civ_name)

    # Use provided provider or fall back to default Ollama
    llm = provider or OllamaProvider()

    try:
        if author_contents and len(author_contents) > 0:
            result = _multi_call_summary(
                author_contents, model, civ_name=civ_name, player_name=player_name,
                provider=llm, prev_tech_era=prev_tech_era,
                prev_fantasy_level=prev_fantasy_level,
            )
        else:
            result = _single_call_summary(
                turn_text, model, civ_name=civ_name, player_name=player_name,
                provider=llm,
            )
        # If LLM returned empty summary, fall back to extractive
        if not result.short_summary and not result.detailed_summary:
            return _extractive_summary(turn_text, civ_name=civ_name)
        return result
    except Exception:
        # Ollama not running or model not available -- fall back gracefully
        return _extractive_summary(turn_text, civ_name=civ_name)


def _multi_call_summary(
    author_contents: list[AuthorContent],
    model: str,
    civ_name: str | None = None,
    player_name: str | None = None,
    provider: LLMProvider | None = None,
    prev_tech_era: str = "neolithique",
    prev_fantasy_level: str = "realiste",
) -> TurnSummary:
    """Multi-call: one LLM call per author, then merge.

    The GM call includes tag/era descriptors in the same JSON response.
    The player call is unchanged (choices only).
    """
    civ_context = ""
    if civ_name:
        civ_context = f'\nCe tour concerne la civilisation "{civ_name}".'

    gm_parts: list[dict] = []
    player_parts: list[dict] = []

    for ac in author_contents:
        text = _truncate(ac.content)
        if not text.strip():
            continue

        if ac.is_gm:
            prompt = GM_PROMPT.format(
                civ_context=civ_context,
                prev_tech_era=prev_tech_era,
                prev_fantasy_level=prev_fantasy_level,
                thematic_tags_list=", ".join(THEMATIC_TAGS),
                tech_eras_list=" < ".join(TECH_ERAS),
                fantasy_levels_list=" < ".join(FANTASY_LEVELS),
                text=text,
            )
            data = _call_llm(model, prompt, provider)
            gm_parts.append(data)
        else:
            player_ref = player_name or ac.author or "le joueur"
            prompt = PLAYER_PROMPT.format(
                civ_context=civ_context,
                player_ref=player_ref,
                text=text,
            )
            data = _call_llm(model, prompt, provider)
            player_parts.append(data)

    return _merge_summaries(gm_parts, player_parts)


def _coerce_str_list(val: object) -> list[str]:
    """Normalise any LLM list field to List[str].

    Handles: None -> [], bare string -> [string], list with None/non-str -> filtered.
    Same pattern as FactExtractor._coerce_list.
    """
    if val is None:
        return []
    if isinstance(val, str):
        return [val] if val.strip() else []
    if isinstance(val, list):
        return [str(e) for e in val if e is not None and str(e).strip()]
    return []


def _merge_summaries(gm_parts: list[dict], player_parts: list[dict],
                     prev_tech_era: str = "neolithique",
                     prev_fantasy_level: str = "realiste") -> TurnSummary:
    """Merge GM and player LLM outputs into a single TurnSummary.

    Tags and era descriptors come from the GM call (first gm_part wins).
    """
    # GM: narrative summary, key events, entities, descriptors
    gm_short = " ".join(d.get("short_summary", "") for d in gm_parts).strip()
    gm_detailed = " ".join(d.get("detailed_summary", "") for d in gm_parts).strip()
    key_events = []
    for d in gm_parts:
        key_events.extend(_coerce_str_list(d.get("key_events")))

    # Player: choices, short summary
    player_short = " ".join(d.get("short_summary", "") for d in player_parts).strip()
    choices_made = []
    for d in player_parts:
        choices_made.extend(_coerce_str_list(d.get("choices_made")))

    # Merge entities from both
    entities = []
    for d in gm_parts + player_parts:
        entities.extend(_coerce_str_list(d.get("entities_mentioned")))
    seen: set[str] = set()
    unique_entities = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            unique_entities.append(e)

    # Combined short summary
    if gm_short and player_short:
        short_summary = f"{gm_short} {player_short}"
    else:
        short_summary = gm_short or player_short

    # Descriptors — from first GM part, validated against allowed vocabularies
    first_gm = gm_parts[0] if gm_parts else {}
    raw_tags = _coerce_str_list(first_gm.get("thematic_tags"))
    thematic_tags = [t for t in raw_tags if t in THEMATIC_TAGS]

    tech_era = first_gm.get("tech_era", "")
    if tech_era not in TECH_ERAS:
        tech_era = prev_tech_era

    fantasy_level = first_gm.get("fantasy_level", "")
    if fantasy_level not in FANTASY_LEVELS:
        fantasy_level = prev_fantasy_level

    return TurnSummary(
        short_summary=short_summary,
        detailed_summary=gm_detailed,
        key_events=key_events,
        entities_mentioned=unique_entities,
        choices_made=choices_made,
        thematic_tags=thematic_tags,
        tech_era=tech_era,
        tech_era_reasoning=first_gm.get("tech_era_reasoning", ""),
        fantasy_level=fantasy_level,
        fantasy_level_reasoning=first_gm.get("fantasy_level_reasoning", ""),
    )


def _single_call_summary(
    turn_text: str,
    model: str,
    civ_name: str | None = None,
    player_name: str | None = None,
    provider: LLMProvider | None = None,
) -> TurnSummary:
    """Single-call fallback (backward compatible)."""
    civ_context = ""
    if civ_name:
        civ_context = f'\nCe tour concerne la civilisation "{civ_name}".'
        if player_name:
            civ_context += f" Le joueur s'appelle {player_name}."

    player_ref = f" {player_name}" if player_name else " le joueur"
    text = _truncate(turn_text)

    prompt = SINGLE_PROMPT.format(
        civ_context=civ_context,
        player_ref=player_ref,
        text=text,
    )

    data = _call_llm(model, prompt, provider)

    return TurnSummary(
        short_summary=data.get("short_summary", ""),
        detailed_summary=data.get("detailed_summary", ""),
        key_events=_coerce_str_list(data.get("key_events")),
        entities_mentioned=_coerce_str_list(data.get("entities_mentioned")),
        choices_made=_coerce_str_list(data.get("choices_made")),
    )


def _call_llm(model: str, prompt: str, provider: LLMProvider | None = None) -> dict:
    """Call LLM via provider and parse JSON response."""
    llm_stats.increment("summarization")
    llm = provider or OllamaProvider()
    raw_content = llm.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        num_ctx=NUM_CTX,
        json_mode=True,
    )
    return _parse_json_response(raw_content)


def _truncate(text: str) -> str:
    """Truncate text to fit within LLM context limits."""
    if len(text) <= MAX_CONTENT_CHARS:
        return text
    # Keep beginning and end (choices are often at the end)
    half = MAX_CONTENT_CHARS // 2
    return (
        text[:half]
        + "\n\n[... contenu tronque pour le resume ...]\n\n"
        + text[-half:]
    )


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON block from markdown code fence
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


# Patterns for pre-cleaning text before extractive summary
_RE_URL = re.compile(r"https?://\S+")
_RE_TIMESTAMP_LINE = re.compile(r"^\s*\[\s*\d{2}:\d{2}\s*\]\s*$")
_RE_MODIFIE = re.compile(r"\s*\(modifi[eé]\)")
_RE_SOUNDTRACK = re.compile(
    r"^.*(?:Soundtrack|OST|Remix|Topic|Pillars of Eternity|Shadow of the Colossus).*$",
    re.IGNORECASE,
)


def _extractive_summary(text: str, civ_name: str | None = None) -> TurnSummary:
    """Generate a basic extractive summary without LLM.

    Pre-cleans noise (URLs, timestamps, short lines) then takes top sentences.
    """
    # Pre-clean: strip noise before sentence extraction
    cleaned_lines = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _RE_URL.match(stripped):
            continue
        if stripped in ("YouTube", "youtube"):
            continue
        if _RE_SOUNDTRACK.match(stripped):
            continue
        if _RE_TIMESTAMP_LINE.match(stripped):
            continue
        if len(stripped) < 10 and not stripped.endswith("."):
            continue
        # Strip (modifie) markers
        stripped = _RE_MODIFIE.sub("", stripped)
        if stripped:
            cleaned_lines.append(stripped)

    cleaned = " ".join(cleaned_lines)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [s for s in sentences if len(s) > 10]

    short = " ".join(sentences[:2]) if sentences else cleaned[:200]
    detailed = " ".join(sentences[:5]) if len(sentences) > 2 else short

    # Truncate if too long
    if len(short) > 300:
        short = short[:297] + "..."
    if len(detailed) > 1000:
        detailed = detailed[:997] + "..."

    return TurnSummary(
        short_summary=short,
        detailed_summary=detailed,
        key_events=[],
        entities_mentioned=[],
        choices_made=[],
    )
