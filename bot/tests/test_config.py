"""Tests for bot.config."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from bot.config import load_config


class TestLoadConfig:
    def test_defaults(self, tmp_path):
        db_path = str(tmp_path / "aurelm.db")
        Path(db_path).touch()

        cfg = load_config(db_path)
        assert cfg.db_path == db_path
        assert cfg.bot_port == 8473
        assert cfg.proxy is None
        assert not cfg.has_discord
        assert not cfg.has_anthropic

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
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        cfg = load_config(db_path)
        assert cfg.has_discord
        assert cfg.has_anthropic
        assert cfg.discord_token == "test-token"
        assert cfg.anthropic_api_key == "test-key"
