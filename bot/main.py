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
from .migrations import apply_migrations
from .server import BotServer

log = logging.getLogger(__name__)

_pipeline_log = logging.getLogger("pipeline")


class _StdoutToLogger:
    """Redirect print() output to the Python logger.

    The pipeline uses print() for progress (e.g. "[6/10] Processing turns...").
    When running inside the bot process, those prints would go to stdout and
    get lost. This wrapper captures them and routes to bot.log instead.
    """

    def __init__(self) -> None:
        self._buf = ""

    def write(self, msg: str) -> None:
        self._buf += msg
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            stripped = line.rstrip()
            if stripped:
                _pipeline_log.info("%s", stripped)

    def flush(self) -> None:
        if self._buf.strip():
            _pipeline_log.info("%s", self._buf.strip())
            self._buf = ""

    # Make it a valid stream (needed by some stdlib internals)
    def isatty(self) -> bool:
        return False


async def _run_sync(config: BotConfig, bot: AurelmBot | None) -> dict:
    """Run a full sync: fetch Discord messages for every civ + run pipeline per civ."""
    import sqlite3 as _sqlite3

    stats: dict = {"messages_fetched": 0, "civs": [], "pipeline": {}}

    # --- Look up all civs with a Discord channel from the DB ---
    conn = _sqlite3.connect(config.db_path)
    conn.row_factory = _sqlite3.Row
    civ_rows = conn.execute(
        "SELECT id, name, player_name, discord_channel_id "
        "FROM civ_civilizations WHERE discord_channel_id IS NOT NULL AND discord_channel_id != ''"
    ).fetchall()
    conn.close()

    if not civ_rows:
        log.info("No civs with discord_channel_id configured — nothing to sync")
        return stats

    log.info("Global sync: found %d civ(s) with Discord channels", len(civ_rows))

    # --- Phase 1: Fetch Discord messages for each civ channel ---
    if bot and bot.is_ready():
        for row in civ_rows:
            channel_id = row["discord_channel_id"]
            # fetch_channel() makes a REST call — works even if not in cache.
            # get_channel() only hits the local cache and returns None after fresh start.
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as exc:
                log.warning("Could not fetch channel %s (civ %s): %s",
                            channel_id, row["name"], exc)
                continue
            count = await fetch_and_store(channel, config.db_path)
            stats["messages_fetched"] += count
            log.info("Fetched %d messages for %s", count, row["name"])
    else:
        log.info("Discord not connected, skipping fetch phase")

    # --- Phase 2: Run pipeline per civ in thread pool ---
    def _pipeline_all() -> dict:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from pipeline.pipeline.runner import run_pipeline
            from pipeline.pipeline.llm_provider import create_provider
            from pipeline.pipeline.ingestion import fetch_unprocessed_messages
            from pipeline.pipeline.db import get_connection
            import pipeline.pipeline.runner as _runner

            if config.gm_authors:
                _runner.GM_AUTHORS = set(config.gm_authors)

            llm_api_key = config.anthropic_api_key if config.llm_provider == "claude_proxy" else None
            provider = create_provider(config.llm_provider, api_key=llm_api_key)

            results = {}
            # Reload civ rows inside thread (DB connection must be in same thread)
            _conn = get_connection(config.db_path)
            rows = _conn.execute(
                "SELECT id, name, player_name, discord_channel_id "
                "FROM civ_civilizations WHERE discord_channel_id IS NOT NULL AND discord_channel_id != ''"
            ).fetchall()
            _conn.close()

            civ_total = len(rows)
            for civ_index, row in enumerate(rows, start=1):
                civ_id = row["id"]
                civ_name = row["name"]
                player_name = row["player_name"]
                channel_id = row["discord_channel_id"]

                messages = fetch_unprocessed_messages(config.db_path, channel_id)
                if not messages:
                    log.info("No new messages for %s — skipping pipeline", civ_name)
                    results[civ_name] = {"skipped": "no_new_messages"}
                    continue

                log.info("Running pipeline for %s (%d/%d)", civ_name, civ_index, civ_total)
                result = run_pipeline(
                    db_path=config.db_path,
                    civ_name=civ_name,
                    player_name=player_name,
                    use_llm=True,
                    wiki_dir=config.wiki_dir,
                    track_progress=True,
                    model=config.ollama_model,
                    provider=provider,
                    extraction_version=config.extraction_version,
                    messages=messages,
                    civ_id=civ_id,
                    channel_id=channel_id,
                    civ_index=civ_index,
                    civ_total=civ_total,
                )
                results[civ_name] = result

            return results
        except ImportError:
            log.warning("Pipeline module not available, skipping")
            return {"error": "pipeline not available"}

    pipeline_result = await asyncio.to_thread(_pipeline_all)
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

    # Redirect stdout so pipeline print() calls land in bot.log
    sys.stdout = _StdoutToLogger()

    # Auto-apply database migrations
    log.info("Applying database migrations...")
    apply_migrations(config.db_path)

    # HTTP server (always starts)
    server = BotServer(config)

    # Always create the agent (needed for /chat endpoint, not just Discord)
    agent = Agent(config)
    backend = "Claude" if config.has_anthropic else f"Ollama ({config.ollama_model})"
    log.info("Agent backend: %s", backend)
    server.set_agent(agent)

    # Discord bot (only if token provided)
    bot: AurelmBot | None = None
    if config.has_discord:
        bot = AurelmBot(agent, proxy=config.proxy)
        bot.set_on_ready(lambda: server.set_discord_connected(True))
        server.set_discord_client(bot)
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
