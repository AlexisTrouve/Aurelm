"""Main entry point: wires aiohttp server + discord.py on the same event loop."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from .agent import Agent
from .config import BotConfig
from .discord_client import AurelmBot
from .fetcher import fetch_and_store
from .server import BotServer

log = logging.getLogger(__name__)


async def _run_sync(config: BotConfig, bot: AurelmBot | None) -> dict:
    """Run a full sync: fetch Discord messages + run pipeline + build wiki."""
    stats: dict = {"messages_fetched": 0, "pipeline": None}

    # Phase 1: Fetch from Discord (if bot is connected)
    if bot and bot.is_ready():
        for ch_cfg in config.channels:
            channel = bot.get_channel(int(ch_cfg.channel_id))
            if channel is None:
                log.warning("Channel %s not found, skipping", ch_cfg.channel_id)
                continue
            count = await fetch_and_store(channel, config.db_path)
            stats["messages_fetched"] += count
    else:
        log.info("Discord not connected, skipping fetch")

    # Phase 2: Run pipeline in thread pool (blocking call)
    def _pipeline() -> dict:
        try:
            sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
            from pipeline.pipeline.runner import run_pipeline_for_channels
            return run_pipeline_for_channels(
                db_path=config.db_path,
                use_llm=False,
                wiki_dir=config.wiki_dir,
                gm_authors=set(config.gm_authors),
                track_progress=True,
            )
        except ImportError:
            log.warning("Pipeline module not available, skipping")
            return {"error": "pipeline not available"}

    pipeline_result = await asyncio.to_thread(_pipeline)
    stats["pipeline"] = pipeline_result
    return stats


async def run(config: BotConfig) -> None:
    """Start bot server and optional Discord client."""
    log_file = Path(config.db_path).parent / "bot.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )
    log.info("Logging to %s", log_file)

    # HTTP server (always starts)
    server = BotServer(config)

    # Discord bot (only if token provided)
    bot: AurelmBot | None = None
    if config.has_discord:
        agent = Agent(config)
        backend = "Claude" if config.has_anthropic else f"Ollama ({config.ollama_model})"
        log.info("Agent backend: %s", backend)
        bot = AurelmBot(agent, proxy=config.proxy)
        bot.set_on_ready(lambda: server.set_discord_connected(True))
    else:
        log.info("DISCORD_BOT_TOKEN not set -- running HTTP-only mode")

    # Wire sync handler
    async def sync_handler() -> dict:
        return await _run_sync(config, bot)

    server.on_sync = sync_handler

    # Start HTTP server
    await server.start()

    try:
        if bot:
            # Run Discord bot (blocks until disconnected)
            await bot.start(config.discord_token)
        else:
            # Just keep the HTTP server running
            log.info("HTTP-only mode. Ctrl+C to stop.")
            while True:
                await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        if bot and not bot.is_closed():
            await bot.close()
        await server.stop()
