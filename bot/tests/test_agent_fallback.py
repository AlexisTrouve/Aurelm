"""Tests for Agent.answer_streaming — Anthropic→Ollama fallback on 503."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_agent_anthropic(tmp_path):
    """Build an Agent configured for Anthropic without real network init."""
    from bot.agent import Agent, OLLAMA_SYSTEM_PROMPT

    db = tmp_path / "test.db"
    db.touch()

    # Skip __init__ to avoid real Anthropic/Ollama init
    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.db_path = str(db)
    agent.config.proxy = None
    agent._backend = "anthropic"
    agent._claude_prompt = "System prompt"
    agent._ollama_prompt = OLLAMA_SYSTEM_PROMPT

    # Mock Anthropic client — will raise 503 by default
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception(
        "Error code: 500 - {'error': {'type': 'api_error', 'message': 'HTTP 503'}}"
    )
    agent._anthropic = mock_client
    agent._anthropic_tools = []

    return agent


def _make_ollama_response(text: str) -> MagicMock:
    """Fake successful Ollama response."""
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = text
    resp = MagicMock()
    resp.message = msg
    resp.prompt_eval_count = 10
    resp.eval_count = 20
    return resp


@pytest.mark.asyncio
async def test_fallback_emits_event_on_503(tmp_path):
    """503-style error → 'fallback' event emitted + backend switches to ollama."""
    agent = _make_agent_anthropic(tmp_path)

    events = []
    ollama_resp = _make_ollama_response("Réponse de secours depuis Ollama")

    with patch("ollama.chat", return_value=ollama_resp):
        async for event_type, data in agent.answer_streaming([], "question de test"):
            events.append((event_type, data))
            if event_type == "text":
                break  # stop after final response

    types = [e[0] for e in events]

    # Fallback event must be present
    assert "fallback" in types, f"Expected 'fallback' event, got: {types}"

    # Backend permanently switched to ollama
    assert agent._backend == "ollama"

    # Ollama model initialised
    assert hasattr(agent, "_ollama_model")

    # Fallback reason contains the error
    fallback_data = next(d for t, d in events if t == "fallback")
    assert "503" in fallback_data["reason"]
    assert fallback_data["backend"] == "ollama"

    # Final text response arrived (from Ollama)
    assert "text" in types


@pytest.mark.asyncio
async def test_no_fallback_on_clean_anthropic(tmp_path):
    """If Anthropic responds cleanly, no fallback event is emitted."""
    from bot.agent import Agent, OLLAMA_SYSTEM_PROMPT

    db = tmp_path / "test.db"
    db.touch()

    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.db_path = str(db)
    agent.config.proxy = None
    agent._backend = "anthropic"
    agent._claude_prompt = "System"
    agent._ollama_prompt = OLLAMA_SYSTEM_PROMPT

    # Successful Anthropic response
    text_block = MagicMock()
    text_block.text = "Bonne réponse"
    text_block.type = "text"
    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"
    response.usage.input_tokens = 100
    response.usage.output_tokens = 20

    mock_client = MagicMock()
    mock_client.messages.create.return_value = response
    agent._anthropic = mock_client
    agent._anthropic_tools = []

    events = []
    async for event_type, data in agent.answer_streaming([], "question"):
        events.append((event_type, data))
        if event_type == "text":
            break

    types = [e[0] for e in events]
    assert "fallback" not in types
    assert "text" in types
    assert agent._backend == "anthropic"  # unchanged


@pytest.mark.asyncio
async def test_any_error_triggers_fallback(tmp_path):
    """Any Anthropic error (including 401 auth) should fall back to Ollama."""
    from bot.agent import Agent, OLLAMA_SYSTEM_PROMPT

    db = tmp_path / "test.db"
    db.touch()

    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.db_path = str(db)
    agent.config.proxy = None
    agent._backend = "anthropic"
    agent._claude_prompt = "System"
    agent._ollama_prompt = OLLAMA_SYSTEM_PROMPT
    agent._anthropic_tools = []

    mock_client = MagicMock()
    # 401 auth error — should also trigger fallback
    mock_client.messages.create.side_effect = Exception("Error code: 401 Unauthorized")
    agent._anthropic = mock_client

    events = []
    ollama_resp = _make_ollama_response("Réponse locale malgré 401")
    with patch("ollama.chat", return_value=ollama_resp):
        async for event_type, data in agent.answer_streaming([], "question"):
            events.append((event_type, data))
            if event_type == "text":
                break

    types = [e[0] for e in events]
    assert "fallback" in types, "Tout type d'erreur doit déclencher le fallback"
    assert agent._backend == "ollama"
    assert "text" in types  # réponse Ollama reçue
