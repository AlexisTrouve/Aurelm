"""Tests for Agent.answer_streaming — Anthropic→claude-p fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_agent_anthropic(tmp_path):
    """Build an Agent configured for Anthropic without real network init."""
    from bot.agent import Agent, OLLAMA_SYSTEM_PROMPT

    db = tmp_path / "test.db"
    db.touch()

    agent = Agent.__new__(Agent)
    agent.config = MagicMock()
    agent.config.db_path = str(db)
    agent.config.proxy = None
    agent._backend = "anthropic"
    agent._claude_prompt = "System prompt"
    agent._ollama_prompt = OLLAMA_SYSTEM_PROMPT

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception(
        "Error code: 500 - {'error': {'type': 'api_error', 'message': 'HTTP 503'}}"
    )
    agent._anthropic = mock_client
    agent._anthropic_tools = []

    return agent


def _mock_cli_result(text: str, returncode: int = 0) -> MagicMock:
    """Fake subprocess.run result for claude -p."""
    r = MagicMock()
    r.returncode = returncode
    r.stdout = text
    r.stderr = ""
    return r


@pytest.mark.asyncio
async def test_fallback_emits_event_on_503(tmp_path):
    """503-style error → 'fallback' event + text from claude -p."""
    agent = _make_agent_anthropic(tmp_path)

    events = []
    with patch("subprocess.run", return_value=_mock_cli_result("Réponse de secours claude -p")):
        async for event_type, data in agent.answer_streaming([], "question de test"):
            events.append((event_type, data))

    types = [e[0] for e in events]

    assert "fallback" in types
    assert "text" in types

    fallback_data = next(d for t, d in events if t == "fallback")
    assert "503" in fallback_data["reason"]
    assert fallback_data["backend"] == "claude-cli"

    text_data = next(d for t, d in events if t == "text")
    assert "claude -p" in text_data["content"] or "secours" in text_data["content"]


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
    assert agent._backend == "anthropic"


@pytest.mark.asyncio
async def test_any_error_triggers_fallback(tmp_path):
    """Any Anthropic error (including 401) falls back to claude -p."""
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
    mock_client.messages.create.side_effect = Exception("Error code: 401 Unauthorized")
    agent._anthropic = mock_client

    events = []
    with patch("subprocess.run", return_value=_mock_cli_result("Réponse locale malgré 401")):
        async for event_type, data in agent.answer_streaming([], "question"):
            events.append((event_type, data))

    types = [e[0] for e in events]
    assert "fallback" in types
    assert "text" in types
    # Backend stays anthropic — we don't switch permanently (no more "continue" to ollama)
    assert agent._backend == "anthropic"


@pytest.mark.asyncio
async def test_fallback_cli_also_fails(tmp_path):
    """If claude -p also fails, response contains error message (no crash)."""
    agent = _make_agent_anthropic(tmp_path)

    events = []
    with patch("subprocess.run", side_effect=FileNotFoundError("claude not found")):
        async for event_type, data in agent.answer_streaming([], "question"):
            events.append((event_type, data))

    types = [e[0] for e in events]
    assert "fallback" in types
    assert "text" in types  # graceful error message, no exception propagation
    text_data = next(d for t, d in events if t == "text")
    assert "indisponible" in text_data["content"]
