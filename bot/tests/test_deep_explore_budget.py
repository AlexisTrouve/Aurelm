"""deepExplore must never throw away the research it already collected.

THE BUG: once the token-budget warning fires, the loop's guard becomes
`if msg.tool_calls and not budget_warning_sent` -> False. A model that answers with one
more tool call and no prose (which models routinely do) then falls straight through to
`return msg.content or "(Pas de reponse du sous-agent.)"`, discarding every tool result
gathered so far. It triggers precisely when the research was LONG — budget exhausted
means a lot of work was done — on the tool meant for the hardest questions.
"""
from __future__ import annotations

import pytest

from bot import tools


class _Fn:
    def __init__(self, name: str, arguments: str = "{}"):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, tid: str, name: str):
        self.id = tid
        self.type = "function"
        self.function = _Fn(name)


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Resp:
    def __init__(self, msg):
        self.choices = [type("C", (), {"message": msg})()]


class _FakeCompletions:
    """Replays a scripted list of assistant messages."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        msg = self.script[min(self.calls - 1, len(self.script) - 1)]
        return _Resp(msg)


class _FakeClient:
    def __init__(self, script):
        self.completions = _FakeCompletions(script)
        self.chat = self


def _budget_after_first_round(monkeypatch):
    """Let round 1 through, then report the budget as blown."""
    state = {"n": 0}

    def fake_estimate(messages):
        state["n"] += 1
        return 0 if state["n"] == 1 else 10 ** 9

    monkeypatch.setattr(tools, "_estimate_tokens", fake_estimate)


def test_concludes_in_text_after_the_budget_warning(db, monkeypatch):
    """The model gathers, gets told to stop, tries one more tool call, then concludes."""
    _budget_after_first_round(monkeypatch)
    client = _FakeClient([
        _Msg(tool_calls=[_ToolCall("t1", "searchLore")]),   # round 1: real research
        _Msg(tool_calls=[_ToolCall("t2", "searchLore")]),   # round 2: ignores the stop order
        _Msg(content="Voici la synthese de mes recherches."),
    ])

    out = tools.deep_explore(db, "question complexe", llm_client=client)

    assert out == "Voici la synthese de mes recherches."
    assert "Pas de reponse" not in out


def test_never_returns_empty_when_research_was_collected(db, monkeypatch):
    """A model that only ever emits tool calls must not cost us the whole research."""
    _budget_after_first_round(monkeypatch)
    client = _FakeClient([_Msg(tool_calls=[_ToolCall("t", "searchLore")])])  # never any prose

    out = tools.deep_explore(db, "question complexe", llm_client=client)

    assert out != "(Pas de reponse du sous-agent.)"
    assert "Argile Vivante" in out, "the collected findings must survive"
    assert client.completions.calls < 10, "must terminate, not loop forever"
