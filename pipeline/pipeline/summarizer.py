"""LLM-based summarization — uses Ollama for turn summaries and entity updates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import ollama


@dataclass
class TurnSummary:
    short_summary: str      # 1-2 sentences
    detailed_summary: str   # Full paragraph
    key_events: list[str] = field(default_factory=list)
    entities_mentioned: list[str] = field(default_factory=list)
    choices_made: list[str] = field(default_factory=list)


DEFAULT_MODEL = "llama3.1:8b"

SUMMARY_PROMPT = """Tu es un assistant spécialisé dans les JDR de civilisation.
Résume le tour de jeu suivant en français. Extrais :
1. Un résumé court (1-2 phrases)
2. Un résumé détaillé (1 paragraphe)
3. Les événements clés (liste)
4. Les entités mentionnées (noms propres : personnes, lieux, technologies, institutions)
5. Les choix effectués par le joueur (liste)

Réponds en JSON avec les clés : short_summary, detailed_summary, key_events, entities_mentioned, choices_made.

Tour de jeu :
{turn_text}"""


def summarize_turn(turn_text: str, model: str = DEFAULT_MODEL, use_llm: bool = True) -> TurnSummary:
    """Generate a structured summary of a game turn.

    If use_llm is False or Ollama is unavailable, falls back to extractive summary.
    """
    if not use_llm:
        return _extractive_summary(turn_text)

    try:
        return _llm_summary(turn_text, model)
    except Exception:
        # Ollama not running or model not available — fall back gracefully
        return _extractive_summary(turn_text)


def _llm_summary(turn_text: str, model: str) -> TurnSummary:
    """Generate summary using Ollama LLM."""
    prompt = SUMMARY_PROMPT.format(turn_text=turn_text)

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    raw_content = response["message"]["content"]
    data = _parse_json_response(raw_content)

    return TurnSummary(
        short_summary=data.get("short_summary", ""),
        detailed_summary=data.get("detailed_summary", ""),
        key_events=data.get("key_events", []),
        entities_mentioned=data.get("entities_mentioned", []),
        choices_made=data.get("choices_made", []),
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


def _extractive_summary(text: str) -> TurnSummary:
    """Generate a basic extractive summary without LLM.

    Takes the first 2 sentences as short summary, first paragraph as detailed.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if len(s) > 10]

    short = " ".join(sentences[:2]) if sentences else text[:200]
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
