"""LLM-based summarization — uses Ollama for turn summaries and entity updates."""

from __future__ import annotations

from dataclasses import dataclass

import ollama


@dataclass
class TurnSummary:
    short_summary: str      # 1-2 sentences
    detailed_summary: str   # Full paragraph
    key_events: list[str]
    entities_mentioned: list[str]
    choices_made: list[str]


DEFAULT_MODEL = "llama3.1:20b"  # GPT-OSS 20B equivalent

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


def summarize_turn(turn_text: str, model: str = DEFAULT_MODEL) -> TurnSummary:
    """Generate a structured summary of a game turn using a local LLM."""
    prompt = SUMMARY_PROMPT.format(turn_text=turn_text)

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    # Parse JSON response
    import json

    data = json.loads(response["message"]["content"])

    return TurnSummary(
        short_summary=data.get("short_summary", ""),
        detailed_summary=data.get("detailed_summary", ""),
        key_events=data.get("key_events", []),
        entities_mentioned=data.get("entities_mentioned", []),
        choices_made=data.get("choices_made", []),
    )
