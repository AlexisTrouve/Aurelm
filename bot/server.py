"""aiohttp HTTP server exposing /health, /status, /sync to Flutter GUI."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from typing import TYPE_CHECKING

from aiohttp import web

from .sessions import SessionManager, ChatMessage

if TYPE_CHECKING:
    from .config import BotConfig

log = logging.getLogger(__name__)


class BotServer:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._app = web.Application()
        self._app.router.add_get("/health", self._health)
        self._app.router.add_get("/status", self._status)
        self._app.router.add_get("/progress", self._progress)
        self._app.router.add_post("/sync", self._sync)
        self._app.router.add_post("/chat", self._chat)
        self._app.router.add_get("/chat/sessions", self._list_sessions)
        self._app.router.add_post("/chat/sessions", self._create_session)
        self._app.router.add_post("/chat/sessions/{session_id}/rename", self._rename_session)
        self._app.router.add_post("/chat/sessions/{session_id}/archive", self._archive_session)
        self._app.router.add_delete("/chat/sessions/{session_id}", self._delete_session)
        self._app.router.add_post("/chat/sessions/{session_id}/tags", self._add_tag)
        self._app.router.add_delete("/chat/sessions/{session_id}/tags/{tag}", self._remove_tag)
        # Session message history (Fix 1: load messages on session switch)
        self._app.router.add_get("/chat/sessions/{session_id}/messages", self._get_session_messages)
        # Hot-reload DB path at runtime (Fix 3)
        self._app.router.add_post("/bot/reload-db", self._reload_db)
        self._runner: web.AppRunner | None = None

        self._last_sync: float | None = None
        self._sync_running = False
        self._last_sync_result: dict | None = None
        self._discord_connected = False

        # Agent wired by main.py when API key is available
        self._agent: "Agent | None" = None
        # Session manager for persistent conversation history
        self._session_manager = SessionManager(config.db_path)
        # Legacy in-memory conversation histories keyed by UUID (deprecated, kept for backwards compatibility)
        self._conversations: dict[str, list[dict]] = {}

        # Callables set by main.py
        self.on_sync: asyncio.coroutines | None = None  # async callable

    def set_discord_connected(self, connected: bool) -> None:
        self._discord_connected = connected

    def set_agent(self, agent) -> None:
        """Attach the LLM agent for /chat endpoint."""
        self._agent = agent

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

    async def _progress(self, _request: web.Request) -> web.Response:
        """Return current pipeline progress for UI polling."""
        progress_info = self._get_current_progress()
        return web.json_response(progress_info)

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

    async def _chat(self, request: web.Request) -> web.StreamResponse:
        """POST /chat — NDJSON stream of agent events during a turn.

        Request body: {"message": "...", "session_id": "optional-uuid"}

        One JSON object per line, streamed as events happen:
            {"type": "tool_start", "name": "...", "input_summary": "..."}
            {"type": "tool_result", "name": "...", "result": "...", ...}
            {"type": "thinking", "content": "..."}
            {"type": "text", "content": "..."}
            {"type": "done", "session_id": "uuid"}
            {"type": "error", "message": "..."}
        """
        if self._agent is None:
            return web.json_response(
                {"error": "Agent not configured (missing ANTHROPIC_API_KEY?)"},
                status=503,
            )

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        message = body.get("message", "").strip()
        if not message:
            return web.json_response({"error": "Empty message"}, status=400)

        session_id = body.get("session_id")

        # Load or create session
        if session_id:
            session = self._session_manager.load_session(session_id)
            if not session:
                return web.json_response({"error": f"Session {session_id} not found"}, status=404)
        else:
            # Create anonymous session scoped to current game DB (Fix 2)
            session_id = str(uuid.uuid4())
            session = self._session_manager.create_session(
                f"Conversation {session_id[:8]}",
                db_path=self.config.db_path,
            )

        # Build history for LLM: convert ChatMessage to dict
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        # NDJSON stream — each event is one JSON line
        resp = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "application/x-ndjson",
                "Cache-Control": "no-cache",
            },
        )
        await resp.prepare(request)

        async def _write(event_type: str, data: dict) -> None:
            payload = {"type": event_type, **data}
            line = json.dumps(payload, ensure_ascii=False) + "\n"
            await resp.write(line.encode("utf-8"))

        try:
            # Stream events from the async generator in real time
            async for event_type, data in self._agent.answer_streaming(history, message):
                await _write(event_type, data)

                # When we get the final text, persist conversation in DB
                if event_type == "text":
                    response_text = data.get("content", "")
                    tool_calls = data.get("tool_calls", [])

                    # Persist user message
                    self._session_manager.save_message(
                        session_id,
                        ChatMessage(role="user", content=message)
                    )

                    # Persist assistant response with tool calls
                    self._session_manager.save_message(
                        session_id,
                        ChatMessage(
                            role="assistant",
                            content=response_text,
                            tool_calls=tool_calls
                        )
                    )

            await _write("done", {"session_id": session_id})

            # Auto-tag session with civilizations referenced in this turn
            self._auto_tag_civs(session_id, tool_calls)

        except Exception as exc:
            log.exception("Agent error in /chat")
            await _write("error", {"message": str(exc)})

        await resp.write_eof()
        return resp

    async def _list_sessions(self, request: web.Request) -> web.Response:
        """GET /chat/sessions — List all active sessions.

        Only returns sessions scoped to the currently active game DB,
        so switching databases shows the right conversation history.
        """
        archived = request.query.get("archived", "false").lower() == "true"
        tag_filter = request.query.get("tag")

        # Filter sessions by the current game DB path (Fix 2)
        sessions = self._session_manager.list_sessions(
            archived=archived,
            tag_filter=tag_filter,
            db_path=self.config.db_path,
        )

        result = []
        for session in sessions:
            last_msg = session.messages[-1] if session.messages else None
            result.append({
                "session_id": session.session_id,
                "name": session.name,
                "message_count": len(session.messages),
                "tags": session.tags,
                "archived": session.archived,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "last_message": last_msg.content[:100] if last_msg else None,
            })

        return web.json_response({"sessions": result, "total": len(result)})

    async def _create_session(self, request: web.Request) -> web.Response:
        """POST /chat/sessions — Create a new session."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        name = body.get("name", "").strip()
        if not name:
            return web.json_response({"error": "Session name required"}, status=400)

        # Scope the new session to the current game DB (Fix 2)
        session = self._session_manager.create_session(name, db_path=self.config.db_path)

        return web.json_response({
            "session_id": session.session_id,
            "name": session.name,
            "created_at": session.created_at,
        }, status=201)

    async def _rename_session(self, request: web.Request) -> web.Response:
        """POST /chat/sessions/{session_id}/rename — Rename a session."""
        session_id = request.match_info.get("session_id")

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        new_name = body.get("name", "").strip()
        if not new_name:
            return web.json_response({"error": "New name required"}, status=400)

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        self._session_manager.rename_session(session_id, new_name)

        return web.json_response({"session_id": session_id, "name": new_name})

    async def _archive_session(self, request: web.Request) -> web.Response:
        """POST /chat/sessions/{session_id}/archive — Archive/unarchive a session."""
        session_id = request.match_info.get("session_id")

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        archived = body.get("archived", not session.archived)
        self._session_manager.toggle_archive(session_id, archived)

        return web.json_response({"session_id": session_id, "archived": archived})

    async def _delete_session(self, request: web.Request) -> web.Response:
        """DELETE /chat/sessions/{session_id} — Delete a session."""
        session_id = request.match_info.get("session_id")

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        self._session_manager.delete_session(session_id)

        return web.json_response({"deleted": session_id})

    async def _add_tag(self, request: web.Request) -> web.Response:
        """POST /chat/sessions/{session_id}/tags — Add a tag to a session."""
        session_id = request.match_info.get("session_id")

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        tag = body.get("tag", "").strip()
        if not tag:
            return web.json_response({"error": "Tag required"}, status=400)

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        self._session_manager.add_tag(session_id, tag)

        return web.json_response({"session_id": session_id, "tag": tag})

    async def _remove_tag(self, request: web.Request) -> web.Response:
        """DELETE /chat/sessions/{session_id}/tags/{tag} — Remove a tag from a session."""
        session_id = request.match_info.get("session_id")
        tag = request.match_info.get("tag")

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        if tag not in session.tags:
            return web.json_response({"error": f"Tag {tag} not in session"}, status=400)

        self._session_manager.remove_tag(session_id, tag)

        return web.json_response({"session_id": session_id, "removed_tag": tag})

    async def _get_session_messages(self, request: web.Request) -> web.Response:
        """GET /chat/sessions/{session_id}/messages — Load full message history for a session.

        Used by Flutter when switching sessions: loads past messages so the
        chat UI can display the conversation history from where it was left.
        """
        session_id = request.match_info["session_id"]
        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": "Session not found"}, status=404)

        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "message_type": msg.message_type,
                "tool_calls": msg.tool_calls,  # already a list of dicts
                "created_at": msg.created_at,
            }
            for msg in session.messages
        ]
        return web.json_response({"session_id": session_id, "messages": messages})

    def _auto_tag_civs(self, session_id: str, tool_calls: list[dict]) -> None:
        """Tag a session with any civilization names referenced in this turn's tool calls.

        Scans input_summary and result_summary of each tool call against the
        known civ list from the active DB. Silent no-op if DB not available or
        civ table empty (e.g. pipeline hasn't run yet).
        Does not add duplicate tags — SessionManager.add_tag is idempotent.
        """
        if not tool_calls or not self.config.db_path:
            return
        try:
            conn = sqlite3.connect(self.config.db_path, check_same_thread=False)
            civ_rows = conn.execute(
                "SELECT name FROM civ_civilizations ORDER BY LENGTH(name) DESC"
            ).fetchall()
            conn.close()
        except Exception:
            return  # DB not ready or table missing — silently skip

        if not civ_rows:
            return

        # Build a single string with all tool call content for this turn
        searchable = " ".join(
            f"{tc.get('input_summary', '')} {tc.get('result_summary', '')}"
            for tc in tool_calls
        ).lower()

        # Tag once per civ found (longest names first to avoid substring false positives)
        for (civ_name,) in civ_rows:
            if civ_name.lower() in searchable:
                try:
                    self._session_manager.add_tag(session_id, civ_name)
                    log.debug("Auto-tagged session %s with civ: %s", session_id[:8], civ_name)
                except Exception:
                    pass  # Don't let tagging failure bubble up

    async def _reload_db(self, request: web.Request) -> web.Response:
        """POST /bot/reload-db — Hot-swap the active game database at runtime.

        Body: {"db_path": "/path/to/aurelm.db"}

        Updates config and reinitialises the SessionManager so subsequent
        session queries target the new DB. The agent's tool calls also pick up
        the new path immediately via self.config.db_path.
        """
        import os

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        db_path = body.get("db_path", "").strip()
        if not db_path:
            return web.json_response({"error": "db_path required"}, status=400)

        if not os.path.exists(db_path):
            return web.json_response(
                {"error": f"Database not found: {db_path}"}, status=404
            )

        old_path = self.config.db_path
        # Swap the active DB path — agent tool calls read config.db_path at query time
        self.config.db_path = db_path
        # Reinitialise SessionManager so it points to the new DB file
        self._session_manager = SessionManager(db_path)

        log.info("Hot-reloaded database: %s -> %s", old_path, db_path)
        return web.json_response({"ok": True, "db_path": db_path})

    # ---------------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------------- #

    def _get_last_pipeline_run(self) -> dict | None:
        conn = sqlite3.connect(self.config.db_path)
        try:
            row = conn.execute(
                "SELECT id, started_at, completed_at, status, messages_processed, turns_created, entities_extracted, error_message "
                "FROM pipeline_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
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
        finally:
            conn.close()

    def _get_current_progress(self) -> dict:
        """Retrieve current pipeline progress from DB.

        Returns:
            - If a pipeline run is in progress: {'status': 'running', 'run_id': ..., 'phases': [...]}
            - If no active run: {'status': 'idle'}
        """
        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Get the latest running pipeline run
            run_row = conn.execute(
                "SELECT id, started_at FROM pipeline_runs WHERE status = 'running' ORDER BY id DESC LIMIT 1"
            ).fetchone()

            if not run_row:
                return {"status": "idle"}

            run_id = run_row["id"]
            started_at = run_row["started_at"]

            # Get progress entries for this run
            progress_rows = conn.execute(
                """SELECT phase, civ_id, civ_name, total_units, current_unit, unit_type, status, updated_at
                   FROM pipeline_progress
                   WHERE pipeline_run_id = ?
                   ORDER BY updated_at DESC""",
                (run_id,),
            ).fetchall()

            phases = []
            for row in progress_rows:
                phases.append({
                    "phase": row["phase"],
                    "civ_id": row["civ_id"],
                    "civ_name": row["civ_name"],
                    "total_units": row["total_units"],
                    "current_unit": row["current_unit"],
                    "unit_type": row["unit_type"],
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                })

            return {
                "status": "running",
                "run_id": run_id,
                "started_at": started_at,
                "phases": phases,
            }

        except Exception as exc:
            log.exception("Failed to get progress")
            return {"status": "error", "error": str(exc)}
        finally:
            conn.close()
