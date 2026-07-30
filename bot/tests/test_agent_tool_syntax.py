"""The agent must never leak tool-call syntax into the user-visible answer.

Some models (esp. via an OpenAI-compat proxy) emit tool-call wrappers/special tokens
as CONTENT instead of using the tool_calls channel. A system-prompt directive asks
them not to; `_strip_tool_call_syntax` is the enforceable backstop that guarantees a
clean answer regardless of model behaviour.
"""
from __future__ import annotations

import pytest

from bot.agent import _strip_tool_call_syntax as strip


@pytest.mark.parametrize("raw, expected", [
    # Vendor special tokens.
    ("Voici la réponse.<|python_tag|>", "Voici la réponse."),
    ("<|tool_calls_begin|>Bonjour", "Bonjour"),
    # Paired function wrapper — the inner JSON payload goes with it.
    ('Réponse <function=groundCivTerrain>{"civName":"X"}</function> finale', "Réponse finale"),
    ("<function_call>{\"x\":1}</function_call>Texte", "Texte"),
    # tool_call wrapper (Qwen/Hermes style).
    ("<tool_call>{}</tool_call>Bonjour", "Bonjour"),
    # Bracket markers.
    ("[TOOL_CALLS]foo(){}[/TOOL_CALLS]texte", "texte"),
])
def test_strips_leaked_tool_syntax(raw, expected):
    assert strip(raw) == expected


@pytest.mark.parametrize("clean", [
    "Les Confluents ont du bronze depuis le tour 12.",
    "Compare 3 < 5 et x > 2 : les deux tiennent.",           # bare < / > are NOT markers
    "Vois #18 et la civ [Confluence] pour le détail.",       # a [word] is not a TOOL marker
    "",
])
def test_leaves_legitimate_text_intact(clean):
    assert strip(clean) == clean


def test_all_leak_collapses_to_empty():
    assert strip("<|tool_calls_begin|>") == ""


def test_the_hygiene_directive_is_in_the_system_prompt():
    """The prompt half of the fix: the model is told not to leak."""
    from bot.agent import _load_system_prompt
    prompt = _load_system_prompt(db_path=None, include_notes=False)
    assert "Appels d'outils" in prompt and "syntaxe d'un appel d'outil" in prompt
