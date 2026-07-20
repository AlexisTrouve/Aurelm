"""Tests for bot.config."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from bot.config import BotConfig, load_config


class TestLoadConfig:
    def test_defaults(self, tmp_path):
        db_path = str(tmp_path / "aurelm.db")
        Path(db_path).touch()

        cfg = load_config(db_path)
        assert cfg.db_path == db_path
        assert cfg.bot_port == 8473
        assert cfg.proxy is None
        assert not cfg.has_discord
        assert not cfg.has_llm

    def test_loads_json(self, tmp_path):
        db_path = str(tmp_path / "aurelm.db")
        Path(db_path).touch()

        config_data = {
            "bot_port": 9999,
            "proxy": "http://127.0.0.1:7897",
            "wiki_dir": "wiki",
            "gm_authors": ["Mug"],
            "channels": {
                "12345": {"civ_name": "Test Civ", "player": "TestPlayer"}
            },
        }
        config_file = tmp_path / "aurelm_config.json"
        config_file.write_text(json.dumps(config_data))

        cfg = load_config(db_path)
        assert cfg.bot_port == 9999
        assert cfg.proxy == "http://127.0.0.1:7897"
        assert cfg.gm_authors == ["Mug"]
        assert len(cfg.channels) == 1
        assert cfg.channels[0].channel_id == "12345"
        assert cfg.channels[0].civ_name == "Test Civ"

    def test_port_override(self, tmp_path):
        db_path = str(tmp_path / "aurelm.db")
        Path(db_path).touch()

        cfg = load_config(db_path, port_override=5555)
        assert cfg.bot_port == 5555

    def test_env_vars(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "aurelm.db")
        Path(db_path).touch()

        monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")   # pipeline field, still loaded
        monkeypatch.setenv("ETHERYALE_API_KEY", "eai-test")   # the agent's LLM backend key

        cfg = load_config(db_path)
        assert cfg.has_discord
        assert cfg.has_llm
        assert cfg.discord_token == "test-token"
        assert cfg.anthropic_api_key == "test-key"
        assert cfg.proxy_api_key == "eai-test"


class TestPipelineLlmKey:
    """The PIPELINE's LLM key (ingestion) — distinct from the chat agent's.

    Locks the seam that replaced a copy-pasted expression in main.py and server.py.
    """

    def test_claude_proxy_prefers_its_own_key(self):
        """A dedicated pipeline key wins — the proxy routes per key and spreads
        load across upstream accounts, so a separate key is deliberate, not noise."""
        cfg = BotConfig(db_path=None, llm_provider="claude_proxy",
                        anthropic_api_key="pipeline-key", proxy_api_key="agent-key")
        assert cfg.pipeline_llm_key == "pipeline-key"

    def test_claude_proxy_falls_back_to_the_agent_key(self):
        """Only ETHERYALE_API_KEY set → the pipeline reuses it instead of being
        handed an empty string and failing on its first call."""
        cfg = BotConfig(db_path=None, llm_provider="claude_proxy",
                        anthropic_api_key="", proxy_api_key="agent-key")
        assert cfg.pipeline_llm_key == "agent-key"

    def test_claude_proxy_none_when_nothing_configured(self):
        cfg = BotConfig(db_path=None, llm_provider="claude_proxy",
                        anthropic_api_key="", proxy_api_key="")
        assert cfg.pipeline_llm_key is None

    def test_ollama_needs_no_key(self):
        cfg = BotConfig(db_path=None, llm_provider="ollama", proxy_api_key="agent-key")
        assert cfg.pipeline_llm_key is None

    def test_openrouter_resolves_its_own_key(self):
        """None on purpose: OpenRouter is a different service — the provider reads
        its key from env/file. Passing the etheryale key here would be wrong."""
        cfg = BotConfig(db_path=None, llm_provider="openrouter", proxy_api_key="agent-key")
        assert cfg.pipeline_llm_key is None
