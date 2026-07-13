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
    # Discord user IDs of GM accounts (immutable, preferred over display names)
    gm_discord_ids: list[str] = field(default_factory=list)
    channels: list[ChannelConfig] = field(default_factory=list)
    # NOTE: llm_provider / ollama_model / anthropic_api_key / anthropic_base_url are
    # still used by the PIPELINE INGESTION path (run_pipeline extraction), NOT by the
    # chat agent — the agent now talks only to the etheryale proxy (see below).
    llm_provider: str = "ollama"  # pipeline: 'ollama' | 'openrouter' | 'claude_proxy'
    ollama_model: str = "qwen3:14b"  # pipeline extraction model
    extraction_version: str = "v22.2.2-pastlevel"
    discord_token: str = ""
    anthropic_api_key: str = ""  # pipeline only (claude_proxy provider)
    anthropic_base_url: str | None = None  # pipeline only

    # --- Etheryale proxy: the SINGLE LLM backend ------------------------------
    # WHAT: an OpenAI-compatible surface fronting ALL models (Claude + GPT). The
    # agent talks to it with the OpenAI SDK — one backend replacing the old
    # anthropic-SDK / ollama / claude-p trio. Auth is `x-api-key`, not Bearer.
    # WHY here: model choice is data-driven (any proxy model, per-request override
    # from the Flutter picker); thinking/vision differences are gated by model.
    proxy_base_url: str = "https://ai.etheryale.com/v1"
    proxy_api_key: str = ""             # eai_... — from env ETHERYALE_API_KEY or config
    model: str = "claude-opus-4-8"      # default; the proxy accepts any of its models
    thinking_budget: int = 4000         # Claude extended-thinking budget (proxy vendor ext)
    request_timeout: float = 300.0      # proxy QUEUES (never 429) → generous client timeout

    @property
    def has_discord(self) -> bool:
        return bool(self.discord_token)

    @property
    def has_llm(self) -> bool:
        """True when the etheryale proxy key is configured (the only LLM backend)."""
        return bool(self.proxy_api_key)


def load_config(db_path: str, port_override: int | None = None) -> BotConfig:
    """Load config from aurelm_config.json next to the DB file, plus env vars."""
    db_dir = Path(db_path).parent
    config_file = db_dir / "aurelm_config.json"

    cfg = BotConfig(db_path=db_path)
    data: dict = {}

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cfg.bot_port = data.get("bot_port", cfg.bot_port)
        cfg.proxy = data.get("proxy")
        cfg.wiki_dir = data.get("wiki_dir")
        cfg.gm_authors = data.get("gm_authors", cfg.gm_authors)
        cfg.llm_provider = data.get("llm_provider", cfg.llm_provider)
        cfg.ollama_model = data.get("ollama_model", cfg.ollama_model)
        cfg.extraction_version = data.get("extraction_version", cfg.extraction_version)
        cfg.anthropic_base_url = data.get("anthropic_base_url")
        cfg.gm_discord_ids = data.get("gm_discord_ids", cfg.gm_discord_ids)
        # Etheryale proxy config (the LLM backend)
        cfg.proxy_base_url = data.get("proxy_base_url", cfg.proxy_base_url)
        cfg.model = data.get("model", cfg.model)
        cfg.thinking_budget = data.get("thinking_budget", cfg.thinking_budget)
        cfg.request_timeout = data.get("request_timeout", cfg.request_timeout)

        for ch_id, ch_data in data.get("channels", {}).items():
            cfg.channels.append(ChannelConfig(
                channel_id=ch_id,
                civ_name=ch_data["civ_name"],
                player=ch_data.get("player", ""),
            ))

    if port_override is not None:
        cfg.bot_port = port_override

    # Secrets: env vars take priority over aurelm_config.json values
    cfg.discord_token = (
        os.environ.get("DISCORD_BOT_TOKEN")
        or data.get("discord_token", "")
    )
    cfg.anthropic_api_key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or data.get("anthropic_api_key", "")
    )
    # Etheryale proxy key — env first (ETHERYALE_API_KEY), then config file.
    cfg.proxy_api_key = (
        os.environ.get("ETHERYALE_API_KEY")
        or data.get("proxy_api_key", "")
    )

    return cfg
