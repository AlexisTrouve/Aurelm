"""Auth-header wiring for the pipeline LLM providers.

Locks the claude_proxy fix: the etheryale proxy authenticates with `x-api-key`, not
the `Authorization: Bearer` the OpenRouter-shaped client sends by default. Before the
fix, claude_proxy sent only Bearer and 401'd; and a missing key silently fell through
to an unrelated OPENROUTER_API_KEY.
"""

from __future__ import annotations

import pytest

from pipeline.llm_provider import OpenRouterProvider, create_provider


def test_claude_proxy_sends_x_api_key():
    """create_provider('claude_proxy') puts the key in the x-api-key header the
    proxy actually reads (the Bearer it also sends is ignored by the proxy)."""
    provider = create_provider("claude_proxy", api_key="eai_test_key")
    client = provider._get_client()  # lazy-inits httpx with the merged headers
    assert client.headers.get("x-api-key") == "eai_test_key"
    # Bearer is still present (harmless), but x-api-key is what matters.
    assert "Bearer eai_test_key" in client.headers.get("Authorization", "")
    assert provider.base_url == "https://ai.etheryale.com/v1"


def test_claude_proxy_requires_a_key():
    """No key → a clear error, NOT a silent fall-through to OPENROUTER_API_KEY."""
    with pytest.raises(ValueError, match="etheryale key"):
        create_provider("claude_proxy", api_key=None)


def test_openrouter_sends_no_x_api_key():
    """Plain OpenRouter needs no x-api-key — the extra header is claude_proxy-only."""
    provider = OpenRouterProvider(api_key="sk-or-test")
    client = provider._get_client()
    assert "x-api-key" not in client.headers
    assert "Bearer sk-or-test" in client.headers.get("Authorization", "")
