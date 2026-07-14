"""Tests for the chat agent — model-picker filtering (HIDDEN_MODELS).

WHAT: verify `Agent.list_models()` drops the deprecated / non-chat models the
proxy still serves, so the Flutter picker only offers current chat models.
WHY: opus-4-6/4-7 are superseded by opus-4-8 and gpt-image-2 is image-gen only —
selecting it would break a chat turn. This locks that filter against regressions.
"""

from __future__ import annotations

import asyncio

from bot.agent import Agent, HIDDEN_MODELS
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
