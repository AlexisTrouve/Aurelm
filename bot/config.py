"""Configuration loader for Aurelm bot.

Reads aurelm_config.json (next to DB) and secrets from env vars.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChannelConfig:
    channel_id: str
    civ_name: str
    player: str


@dataclass
class BotConfig:
    db_path: str
    bot_port: int = 8473
    proxy: str | None = None
    wiki_dir: str | None = None
    gm_authors: list[str] = field(default_factory=lambda: ["Arthur Ignatus"])
    channels: list[ChannelConfig] = field(default_factory=list)
    ollama_model: str = "llama3.1:8b"
    discord_token: str = ""
    anthropic_api_key: str = ""

    @property
    def has_discord(self) -> bool:
        return bool(self.discord_token)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


def load_config(db_path: str, port_override: int | None = None) -> BotConfig:
    """Load config from aurelm_config.json next to the DB file, plus env vars."""
    db_dir = Path(db_path).parent
    config_file = db_dir / "aurelm_config.json"

    cfg = BotConfig(db_path=db_path)

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cfg.bot_port = data.get("bot_port", cfg.bot_port)
        cfg.proxy = data.get("proxy")
        cfg.wiki_dir = data.get("wiki_dir")
        cfg.gm_authors = data.get("gm_authors", cfg.gm_authors)
        cfg.ollama_model = data.get("ollama_model", cfg.ollama_model)

        for ch_id, ch_data in data.get("channels", {}).items():
            cfg.channels.append(ChannelConfig(
                channel_id=ch_id,
                civ_name=ch_data["civ_name"],
                player=ch_data.get("player", ""),
            ))

    if port_override is not None:
        cfg.bot_port = port_override

    # Secrets from env vars
    cfg.discord_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    cfg.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    return cfg
