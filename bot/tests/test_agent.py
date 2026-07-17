"""Tests for the chat agent — model-picker filtering (HIDDEN_MODELS).

WHAT: verify `Agent.list_models()` drops the deprecated / non-chat models the
proxy still serves, so the Flutter picker only offers current chat models.
WHY: opus-4-6/4-7 are superseded by opus-4-8 and gpt-image-2 is image-gen only —
selecting it would break a chat turn. This locks that filter against regressions.
"""

from __future__ import annotations

import asyncio

from bot.agent import (
    CLAUDE_ONLY_EFFORTS,
    EFFORT_LEVELS,
    HIDDEN_MODELS,
    OPENAI_MAX_EFFORT,
    Agent,
    _clamp_effort,
)
from bot.config import BotConfig


class _FakeModel:
    """Minimal stand-in for an OpenAI SDK model object (only `.id` is read)."""

    def __init__(self, model_id: str) -> None:
        self.id = model_id


class _FakeModelsList:
    """Mimics the `.data` list returned by `client.models.list()`."""

    def __init__(self, ids: list[str]) -> None:
        self.data = [_FakeModel(i) for i in ids]


class _FakeModelsEndpoint:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    async def list(self) -> _FakeModelsList:  # matches AsyncOpenAI.models.list
        return _FakeModelsList(self._ids)


class _FakeAsyncClient:
    def __init__(self, ids: list[str]) -> None:
        self.models = _FakeModelsEndpoint(ids)


# The full set the proxy serves as of 2026-07-13 (mix of chat + hidden models).
_PROXY_SERVED = [
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-image-2",
]


def _agent_with_models(ids: list[str]) -> Agent:
    """Build an Agent offline (no network) and stub its async client's model list.

    Constructing the OpenAI clients does not open a connection, so a dummy key is
    enough; db_path=None skips the notes/system-prompt DB read.
    """
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    agent._aclient = _FakeAsyncClient(ids)  # type: ignore[assignment]
    return agent


def test_list_models_drops_hidden_models():
    """The 3 deprecated/non-chat models are filtered out; the 6 chat models stay."""
    agent = _agent_with_models(_PROXY_SERVED)
    models = asyncio.run(agent.list_models())

    assert models == [
        "claude-opus-4-8",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
    ]
    # None of the denylisted ids survive.
    assert not (set(models) & HIDDEN_MODELS)


def test_list_models_preserves_proxy_order():
    """Filtering keeps the proxy's ordering for the surviving models."""
    agent = _agent_with_models(["gpt-5.6-luna", "claude-opus-4-6", "claude-opus-4-8"])
    models = asyncio.run(agent.list_models())
    assert models == ["gpt-5.6-luna", "claude-opus-4-8"]


# --------------------------------------------------------------------------- #
# Reasoning effort + visible-reasoning toggle
# --------------------------------------------------------------------------- #


def test_clamp_effort_downgrades_claude_only_levels_for_gpt():
    """xhigh/max reach Claude untouched but clamp to `high` for GPT.

    Not cosmetic: sending effort=max to a GPT model kills the upstream connection
    (measured), so an unclamped picker choice would break the turn.
    """
    for level in CLAUDE_ONLY_EFFORTS:
        assert _clamp_effort("claude-opus-4-8", level) == level
        assert _clamp_effort("gpt-5.6-luna", level) == OPENAI_MAX_EFFORT


def test_clamp_effort_leaves_shared_levels_alone():
    """Levels both providers accept pass through unchanged for either model."""
    for level in ("low", "medium", "high"):
        assert _clamp_effort("claude-opus-4-8", level) == level
        assert _clamp_effort("gpt-5.6-luna", level) == level


def test_request_extra_sends_effort_and_never_a_thinking_budget():
    """reasoning_effort is the only knob — a `thinking` block would void it.

    The proxy gives an explicit client `thinking` block priority over effort, so
    emitting both would silently disable the effort picker.
    """
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    extra = agent._request_extra("claude-opus-4-8", "high", False)
    assert extra == {"reasoning_effort": "high"}
    assert "thinking" not in extra


def test_request_extra_falls_back_to_configured_default_effort():
    """No per-request effort → the configured default is sent."""
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key", default_effort="low"))
    assert agent._request_extra("claude-opus-4-8")["reasoning_effort"] == "low"


def test_request_extra_show_thinking_adds_include_reasoning():
    """The visible-reasoning toggle adds include_reasoning; off by default."""
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    assert agent._request_extra("claude-opus-4-8", "high", True)["include_reasoning"] is True
    assert "include_reasoning" not in agent._request_extra("claude-opus-4-8", "high", False)


def test_request_extra_clamps_effort_for_gpt():
    """A GM who picks `max` then switches to GPT gets GPT's hardest level, not a dead turn."""
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    assert agent._request_extra("gpt-5.6-luna", "max")["reasoning_effort"] == OPENAI_MAX_EFFORT


def test_effort_levels_ordered_weakest_to_strongest():
    """The picker renders EFFORT_LEVELS in order — lock the contract."""
    assert EFFORT_LEVELS == ("low", "medium", "high", "xhigh", "max")


# --------------------------------------------------------------------------- #
# Streaming robustness
# --------------------------------------------------------------------------- #


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, index: int, tc_id: str, name: str, args: str) -> None:
        self.index = index
        self.id = tc_id
        self.function = _FakeFunction(name, args)


class _FakeDelta:
    def __init__(self, content=None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChunk:
    def __init__(self, delta: _FakeDelta) -> None:
        self.choices = [type("C", (), {"delta": delta})()]

    def model_dump_json(self) -> str:  # used by the null-entry warning log
        return '{"fake":"chunk"}'


class _FakeStream:
    def __init__(self, chunks: list) -> None:
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c

        return gen()


class _FakeCompletions:
    def __init__(self, rounds: list) -> None:
        self._rounds = list(rounds)
        self.calls = 0

    async def create(self, **kwargs):
        chunks = self._rounds[self.calls]
        self.calls += 1
        return _FakeStream(chunks)


class _FakeStreamingClient:
    def __init__(self, rounds: list) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(rounds)})()


def test_streaming_skips_null_tool_call_entries():
    """A null placeholder in tool_calls must not kill the turn.

    The proxy emits a positional, sparse array on parallel tool calls —
    `[null, {index:1,...}]` — so the real call rides at index 1 behind a null.
    Before the guard this raised AttributeError on `tc.index` and the GM got an
    error instead of an answer (measured on real traffic: 83 nulls in 3 turns).
    """
    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    real_call = _FakeToolCall(1, "toolu_1", "listCivs", "{}")
    agent._aclient = _FakeStreamingClient([
        [_FakeChunk(_FakeDelta(tool_calls=[None, real_call]))],  # null + real call
        [_FakeChunk(_FakeDelta(content="Deux civilisations."))],  # final answer
    ])
    agent._exec_tool = lambda name, inp: f"result of {name}"  # no DB in this test

    events = []

    async def drive():
        async for event in agent.answer_streaming([], "Quelles civs ?"):
            events.append(event)

    asyncio.run(drive())
    types = [t for t, _ in events]

    assert "error" not in types, "the null entry must not surface as an error"
    # The real call behind the null still ran end-to-end.
    assert "tool_start" in types and "tool_result" in types
    assert [d for t, d in events if t == "tool_result"][0]["name"] == "listCivs"
    assert [d for t, d in events if t == "text"][-1]["content"] == "Deux civilisations."


def test_list_models_empty_on_error():
    """A models.list() failure yields an empty list (picker falls back to default)."""

    class _BoomEndpoint:
        async def list(self):
            raise RuntimeError("proxy unreachable")

    class _BoomClient:
        models = _BoomEndpoint()

    agent = Agent(BotConfig(db_path=None, proxy_api_key="test-key"))
    agent._aclient = _BoomClient()  # type: ignore[assignment]
    assert asyncio.run(agent.list_models()) == []
