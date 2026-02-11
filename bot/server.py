"""aiohttp HTTP server exposing /health, /status, /sync to Flutter GUI."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from .config import BotConfig

log = logging.getLogger(__name__)


class BotServer:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._app = web.Application()
        self._app.router.add_get("/health", self._health)
        self._app.router.add_get("/status", self._status)
        self._app.router.add_post("/sync", self._sync)
        self._runner: web.AppRunner | None = None

        self._last_sync: float | None = None
        self._sync_running = False
        self._last_sync_result: dict | None = None
        self._discord_connected = False

        # Callables set by main.py
        self.on_sync: asyncio.coroutines | None = None  # async callable

    def set_discord_connected(self, connected: bool) -> None:
        self._discord_connected = connected

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self.config.bot_port)
        await site.start()
        log.info("HTTP server listening on http://127.0.0.1:%d", self.config.bot_port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    # ---------------------------------------------------------------------- #
    # Endpoints
    # ---------------------------------------------------------------------- #

    async def _health(self, _request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def _status(self, _request: web.Request) -> web.Response:
        # Pipeline run info from DB
        pipeline_info = self._get_last_pipeline_run()
        return web.json_response({
            "discord_connected": self._discord_connected,
            "sync_running": self._sync_running,
            "last_sync": self._last_sync,
            "last_sync_result": self._last_sync_result,
            "last_pipeline_run": pipeline_info,
        })

    async def _sync(self, _request: web.Request) -> web.Response:
        if self._sync_running:
            return web.json_response(
                {"error": "Sync already in progress"}, status=409
            )

        self._sync_running = True
        try:
            if self.on_sync:
                result = await self.on_sync()
            else:
                result = {"error": "No sync handler configured"}

            self._last_sync = time.time()
            self._last_sync_result = result
            return web.json_response(result)
        except Exception as exc:
            log.exception("Sync failed")
            err = {"error": str(exc)}
            self._last_sync_result = err
            return web.json_response(err, status=500)
        finally:
            self._sync_running = False

    # ---------------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------------- #

    def _get_last_pipeline_run(self) -> dict | None:
        try:
            conn = sqlite3.connect(self.config.db_path)
            row = conn.execute(
                "SELECT id, started_at, completed_at, status, messages_processed, turns_created, entities_extracted, error_message "
                "FROM pipeline_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "id": row[0],
                "started_at": row[1],
                "completed_at": row[2],
                "status": row[3],
                "messages_processed": row[4],
                "turns_created": row[5],
                "entities_extracted": row[6],
                "error_message": row[7],
            }
        except Exception:
            return None
