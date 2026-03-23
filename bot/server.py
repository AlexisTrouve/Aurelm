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
        self._app.router.add_post("/chat/sessions/{session_id}/duplicate", self._duplicate_session)
        self._app.router.add_post("/chat/sessions/{session_id}/tags", self._add_tag)
        self._app.router.add_delete("/chat/sessions/{session_id}/tags/{tag}", self._remove_tag)
        # Session message history (Fix 1: load messages on session switch)
        self._app.router.add_get("/chat/sessions/{session_id}/messages", self._get_session_messages)
        self._app.router.add_delete("/chat/sessions/{session_id}/messages", self._delete_session_messages)
        self._app.router.add_post("/chat/sessions/{session_id}/messages/{order}/edit", self._edit_message)
        self._app.router.add_get("/chat/sessions/{session_id}/context_size", self._get_context_size)
        # Hot-reload DB path at runtime (Fix 3)
        self._app.router.add_post("/bot/reload-db", self._reload_db)
        # Notes CRUD
        self._app.router.add_get("/notes", self._list_notes)
        self._app.router.add_post("/notes", self._create_note)
        self._app.router.add_put("/notes/{note_id}", self._update_note)
        self._app.router.add_delete("/notes/{note_id}", self._delete_note)
        # Discord channel listing for Flutter config UI
        self._app.router.add_get("/discord/channels", self._discord_channels)
        # Per-channel: preview pending messages + sync
        self._app.router.add_get("/discord/channels/{channel_id}/pending", self._channel_pending)
        self._app.router.add_post("/discord/channels/{channel_id}/sync", self._channel_sync)
        self._runner: web.AppRunner | None = None

        self._last_sync: float | None = None
        self._sync_running = False
        self._last_sync_result: dict | None = None
        self._discord_connected = False

        # Agent wired by main.py when API key is available
        self._agent: "Agent | None" = None
        # Discord client reference — set by main.py for /discord/channels
        self._discord_client: "AurelmBot | None" = None
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

    def set_discord_client(self, client) -> None:
        """Attach the Discord client for /discord/channels endpoint."""
        self._discord_client = client

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

    async def _discord_channels(self, _request: web.Request) -> web.Response:
        """Return text channels the bot can see, grouped by guild."""
        if not self._discord_client or not self._discord_connected:
            return web.json_response(
                {"error": "Discord not connected"}, status=503)

        channels = []
        for guild in self._discord_client.guilds:
            for ch in guild.text_channels:
                channels.append({
                    "id": str(ch.id),
                    "name": ch.name,
                    "guild_id": str(guild.id),
                    "guild_name": guild.name,
                })
        return web.json_response({"channels": channels})

    async def _channel_pending(self, request: web.Request) -> web.Response:
        """Preview pending Discord messages for a channel — detect turns without storing."""
        if not self._discord_client or not self._discord_connected:
            return web.json_response({"error": "Discord not connected"}, status=503)

        channel_id = request.match_info["channel_id"]
        channel = self._discord_client.get_channel(int(channel_id))
        if channel is None:
            return web.json_response({"error": "Channel not found"}, status=404)

        # Find last known message timestamp for this channel
        conn = sqlite3.connect(self.config.db_path)
        row = conn.execute(
            "SELECT MAX(timestamp) FROM turn_raw_messages WHERE discord_channel_id = ?",
            (channel_id,),
        ).fetchone()
        conn.close()

        after_dt = None
        if row and row[0]:
            try:
                from datetime import datetime, timezone
                after_dt = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Fetch new messages from Discord (without storing)
        messages = []
        async for msg in channel.history(limit=None, after=after_dt, oldest_first=True):
            # Don't filter bots/webhooks — GM turns are often posted via bots
            if not msg.content and not msg.attachments:
                continue
            messages.append({
                "id": str(msg.id),
                "author": msg.author.display_name,
                "content": msg.content[:200] if msg.content else "",
                "timestamp": msg.created_at.isoformat(),
            })

        # Turn detection: group consecutive messages by author type (GM vs player)
        gm_names = set(self.config.gm_authors)
        turns = []
        last_is_gm = None
        for m in messages:
            is_gm = m["author"] in gm_names
            if is_gm != last_is_gm:
                turns.append({"is_gm": is_gm, "messages": [m]})
                last_is_gm = is_gm
            else:
                turns[-1]["messages"].append(m)

        gm_turns = [t for t in turns if t["is_gm"]]
        player_turns = [t for t in turns if not t["is_gm"]]

        # Build a readable turn summary for preview
        turn_preview = []
        for t in turns:
            first_msg = t["messages"][0]
            content_preview = first_msg["content"][:150]
            turn_preview.append({
                "type": "MJ" if t["is_gm"] else "PJ",
                "author": first_msg["author"],
                "messages": len(t["messages"]),
                "preview": content_preview,
            })

        return web.json_response({
            "channel_id": channel_id,
            "new_messages": len(messages),
            "gm_turns": len(gm_turns),
            "player_turns": len(player_turns),
            "turns": turn_preview,
        })

    async def _channel_sync(self, request: web.Request) -> web.Response:
        """Fetch + pipeline for a single channel.
        Query params:
          turns=0,1,2  — only import specific turn indices (from /pending)
          If omitted, imports all.
        """
        if self._sync_running:
            return web.json_response({"error": "Sync already running"}, status=409)

        channel_id = request.match_info["channel_id"]
        turns_param = request.query.get("turns")  # e.g. "0,2,3"

        if not self._discord_client or not self._discord_connected:
            return web.json_response({"error": "Discord not connected"}, status=503)

        channel = self._discord_client.get_channel(int(channel_id))
        if channel is None:
            return web.json_response({"error": "Channel not found"}, status=404)

        self._sync_running = True
        try:
            if turns_param is not None:
                # Selective import: fetch messages, group into turns, store only requested
                selected_indices = set(int(x) for x in turns_param.split(",") if x.strip())
                count = await self._selective_fetch(channel, channel_id, selected_indices)
            else:
                # Full import
                from .fetcher import fetch_and_store
                count = await fetch_and_store(channel, self.config.db_path)

            # Run pipeline on whatever is now in DB
            import sys
            def _pipeline() -> dict:
                try:
                    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
                    from pipeline.pipeline.runner import run_pipeline_for_channels
                    from pipeline.pipeline.llm_provider import create_provider
                    provider = create_provider(self.config.llm_provider)
                    return run_pipeline_for_channels(
                        db_path=self.config.db_path,
                        use_llm=True,
                        wiki_dir=self.config.wiki_dir,
                        gm_authors=set(self.config.gm_authors),
                        track_progress=True,
                        model=self.config.ollama_model,
                        provider=provider,
                        extraction_version=self.config.extraction_version,
                    )
                except ImportError:
                    return {"error": "pipeline not available"}

            pipeline_result = await asyncio.to_thread(_pipeline)
            self._last_sync = time.time()
            result = {
                "messages_fetched": count,
                "pipeline": pipeline_result,
            }
            self._last_sync_result = result
            return web.json_response(result)
        finally:
            self._sync_running = False

    async def _selective_fetch(self, channel, channel_id: str,
                                selected_indices: set[int]) -> int:
        """Fetch messages from Discord, group into turns, store only selected turn indices."""
        conn = sqlite3.connect(self.config.db_path)
        row = conn.execute(
            "SELECT MAX(timestamp) FROM turn_raw_messages WHERE discord_channel_id = ?",
            (channel_id,),
        ).fetchone()

        after_dt = None
        if row and row[0]:
            try:
                from datetime import datetime, timezone
                after_dt = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Fetch all messages
        all_msgs = []
        async for msg in channel.history(limit=None, after=after_dt, oldest_first=True):
            if not msg.content and not msg.attachments:
                continue
            all_msgs.append(msg)

        # Group into turns (same logic as _channel_pending)
        gm_names = set(self.config.gm_authors)
        turns: list[list] = []
        last_is_gm = None
        for msg in all_msgs:
            is_gm = msg.author.display_name in gm_names
            if is_gm != last_is_gm:
                turns.append([msg])
                last_is_gm = is_gm
            else:
                turns[-1].append(msg)

        # Store only messages from selected turns
        count = 0
        for idx in selected_indices:
            if idx >= len(turns):
                continue
            for msg in turns[idx]:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO turn_raw_messages
                           (discord_message_id, discord_channel_id, author_id, author_name,
                            content, timestamp, attachments)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(msg.id),
                            channel_id,
                            str(msg.author.id),
                            msg.author.display_name,
                            msg.content,
                            msg.created_at.isoformat(),
                            ",".join(a.url for a in msg.attachments) if msg.attachments else None,
                        ),
                    )
                    count += 1
                except Exception:
                    pass
        conn.commit()
        conn.close()
        return count

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
            # Note: create_session generates its own UUID internally —
            # we must use session.session_id, not a local UUID.
            temp_label = str(uuid.uuid4())[:8]
            session = self._session_manager.create_session(
                f"Conversation {temp_label}",
                db_path=self.config.db_path,
            )
            session_id = session.session_id

        # Build optimized history: uses latest compress/resume as checkpoint
        # instead of sending ALL messages to the LLM
        history = self._session_manager.build_llm_history(session.session_id)

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

                    # Persist assistant response — fold tool result summaries
                    # into the content so they're part of the LLM context on reload.
                    # Raw tool_use/tool_result blocks are NOT persisted; only the
                    # compact text summary survives in the conversation history.
                    enriched_content = response_text
                    if tool_calls:
                        tc_lines = []
                        for tc in tool_calls:
                            name = tc.get("name", "tool")
                            inp = tc.get("input_summary", "")
                            res = tc.get("result_summary", "")
                            tc_lines.append(f"[{name}({inp}) -> {res}]")
                        # Prepend tool context before the response text
                        enriched_content = "\n".join(tc_lines) + "\n\n" + response_text

                    self._session_manager.save_message(
                        session_id,
                        ChatMessage(
                            role="assistant",
                            content=enriched_content,
                            tool_calls=tool_calls
                        )
                    )

            # Check if compression is needed (20+ text messages since last checkpoint)
            await self._maybe_compress_session(session_id, _write)

            # Emit final context estimate based on persisted history (no tool blocks)
            # This is the accurate token count for the NEXT message.
            from .agent import _compress_tool_history, _estimate_tokens
            final_history = self._session_manager.build_llm_history(session_id)
            final_compressed = _compress_tool_history(final_history)
            await _write("context_estimate", {
                "raw_tokens": _estimate_tokens(final_history),
                "compressed_tokens": _estimate_tokens(final_compressed),
                "round": -1,  # -1 = post-response final estimate
            })

            # Include session name + tags in done event for AppBar display
            session = self._session_manager.load_session(session_id)
            session_name = session.name if session else ""
            session_tags = session.tags if session else []
            await _write("done", {
                "session_id": session_id,
                "session_name": session_name,
                "session_tags": session_tags,
            })

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

    async def _duplicate_session(self, request: web.Request) -> web.Response:
        """POST /chat/sessions/{session_id}/duplicate — Clone une session avec tous ses messages."""
        session_id = request.match_info.get("session_id")
        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": f"Session {session_id} not found"}, status=404)

        # Crée une nouvelle session avec le même nom + " (copie)"
        new_name = f"{session.name} (copie)"
        new_session = self._session_manager.create_session(new_name, db_path=self.config.db_path)

        # Copie tous les messages dans l'ordre
        for msg in session.messages:
            self._session_manager.save_message(new_session.session_id, msg)

        # Copie les tags
        for tag in session.tags:
            self._session_manager.add_tag(new_session.session_id, tag)

        return web.json_response({
            "session_id": new_session.session_id,
            "name": new_name,
            "message_count": len(session.messages),
        }, status=201)

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

    async def _edit_message(self, request: web.Request) -> web.Response:
        """POST /chat/sessions/{session_id}/messages/{order}/edit

        Updates the content of a message at position {order}.
        Body: {"content": "new text"}
        """
        session_id = request.match_info["session_id"]
        try:
            order = int(request.match_info["order"])
        except ValueError:
            return web.json_response({"error": "order must be an integer"}, status=400)

        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        content = body.get("content", "")
        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": "Session not found"}, status=404)

        self._session_manager.edit_message(session_id, order, content)
        return web.json_response({"ok": True, "order": order})

    async def _delete_session_messages(self, request: web.Request) -> web.Response:
        """DELETE /chat/sessions/{session_id}/messages?from_order=N

        Deletes all messages with message_order >= from_order.
        from_order defaults to 0 (deletes everything).
        Used by Flutter to truncate history after editing or retrying.
        """
        session_id = request.match_info["session_id"]
        try:
            from_order = int(request.rel_url.query.get("from_order", "0"))
        except ValueError:
            return web.json_response({"error": "from_order must be an integer"}, status=400)

        session = self._session_manager.load_session(session_id)
        if not session:
            return web.json_response({"error": "Session not found"}, status=404)

        deleted = self._session_manager.delete_messages_from(session_id, from_order)
        return web.json_response({"deleted": deleted, "from_order": from_order})

    async def _get_context_size(self, request: web.Request) -> web.Response:
        """GET /chat/sessions/{session_id}/context_size — Estimate context tokens.

        Uses the exact same pipeline as sending a message:
        build_llm_history() -> _compress_tool_history() -> _estimate_tokens().
        Returns raw (before compression) and compressed (what Claude sees) estimates.
        """
        from .agent import _compress_tool_history, _estimate_tokens

        session_id = request.match_info["session_id"]
        history = self._session_manager.build_llm_history(session_id)
        if not history:
            return web.json_response({
                "raw_tokens": 0, "compressed_tokens": 0,
            })

        raw_tokens = _estimate_tokens(history)
        compressed = _compress_tool_history(history)
        compressed_tokens = _estimate_tokens(compressed)

        return web.json_response({
            "raw_tokens": raw_tokens,
            "compressed_tokens": compressed_tokens,
        })

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

        # Build searchable text from ALL tool call fields (input, summaries, full result).
        # The full result is critical: the LLM often passes a short name like "Confluence"
        # while the DB stores "Civilisation de la Confluence". The tool result always
        # contains the canonical name, so searching the full result catches it reliably.
        searchable = " ".join(
            f"{tc.get('input_summary', '')} {tc.get('result_summary', '')} {tc.get('result', '')}"
            for tc in tool_calls
        ).lower()

        # For each civ, build a set of tokens to match: the full name + each significant
        # word (≥4 chars, skips stopwords like "de", "la", "les"). This handles cases
        # where the LLM passes "Confluence" but the DB name is "Civilisation de la Confluence".
        _STOPWORDS = {"de", "la", "le", "les", "du", "des", "et", "en", "un", "une"}

        for (civ_name,) in civ_rows:
            tokens = {civ_name.lower()}
            for word in civ_name.lower().split():
                if len(word) >= 4 and word not in _STOPWORDS:
                    tokens.add(word)

            if any(tok in searchable for tok in tokens):
                try:
                    self._session_manager.add_tag(session_id, civ_name)
                    log.info("Auto-tagged session %s with civ: %s", session_id[:8], civ_name)
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
    # Session compression
    # ---------------------------------------------------------------------- #

    COMPRESS_MSG_THRESHOLD = 20    # text messages before triggering a compress
    COMPRESS_TOKEN_THRESHOLD = 30_000  # estimated tokens (includes tool results)
    RESUME_THRESHOLD = 4           # compress blocks before triggering a resume

    async def _maybe_compress_session(self, session_id: str, _write) -> None:
        """Check and run compress/resume if thresholds are reached.

        Triggers compression when EITHER:
        - 20+ text messages since last checkpoint, OR
        - 30k+ estimated tokens since last checkpoint (tool results are huge)

        Called after persisting messages in a /chat turn. Emits NDJSON events
        so Flutter can display the compress/resume blocks.
        """
        if self._agent is None:
            return

        try:
            msg_count = self._session_manager.count_messages_since_checkpoint(session_id)
            token_count = self._session_manager.estimate_tokens_since_checkpoint(session_id)

            if msg_count < self.COMPRESS_MSG_THRESHOLD and token_count < self.COMPRESS_TOKEN_THRESHOLD:
                return

            # --- Phase 1: Compress ---
            log.info(
                "Session %s: %d messages / ~%dk tokens since checkpoint, compressing...",
                session_id[:8], msg_count, token_count // 1000,
            )

            messages_to_compress = self._session_manager.get_messages_for_compression(session_id)
            if not messages_to_compress:
                return

            # Convert ChatMessage objects to dicts for the summarizer.
            # For assistant messages, include tool call results inline so the
            # summary captures what tools found (not just the final answer).
            msgs_for_llm = []
            for m in messages_to_compress:
                content = m.content
                if m.role == "assistant" and m.tool_calls:
                    tc_lines = []
                    for tc in m.tool_calls:
                        name = tc.get("name", "tool")
                        inp = tc.get("input_summary", "")
                        # Include truncated result — enough for the summary
                        result = tc.get("result", tc.get("result_summary", ""))
                        if len(result) > 500:
                            result = result[:500] + "..."
                        tc_lines.append(f"[outil {name}({inp}) -> {result}]")
                    content = "\n".join(tc_lines) + "\n" + content
                msgs_for_llm.append({"role": m.role, "content": content})
            summary = await self._agent.summarize_for_compress(msgs_for_llm, mode="compress")

            self._session_manager.add_compress_block(session_id, summary)
            await _write("compress", {"content": summary})

            log.info("Session %s: compress block added (%d chars)", session_id[:8], len(summary))

            # --- Phase 2: Resume (if enough compresses accumulated) ---
            session = self._session_manager.load_session(session_id)
            if not session or session.compress_count < self.RESUME_THRESHOLD:
                return

            log.info(
                "Session %s: %d compress blocks, creating resume...",
                session_id[:8], session.compress_count,
            )

            compress_blocks = self._session_manager.get_compress_blocks_since_resume(session_id)
            if not compress_blocks:
                return

            # Feed compress summaries as "messages" to the resume summarizer
            compress_msgs = [
                {"role": "assistant", "content": cb.content}
                for cb in compress_blocks
            ]
            resume_summary = await self._agent.summarize_for_compress(compress_msgs, mode="resume")

            self._session_manager.add_resume_block(session_id, resume_summary)
            await _write("resume", {"content": resume_summary})

            log.info("Session %s: resume block added (%d chars)", session_id[:8], len(resume_summary))

        except Exception:
            # Compression failure should never break the chat flow
            log.exception("Session compression failed for %s", session_id[:8])

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

    # ---------------------------------------------------------------------- #
    # Notes CRUD
    # ---------------------------------------------------------------------- #

    async def _list_notes(self, request: web.Request) -> web.Response:
        """GET /notes?entity_id=X  or  ?subject_id=X  or  ?turn_id=X"""
        entity_id  = request.rel_url.query.get("entity_id")
        subject_id = request.rel_url.query.get("subject_id")
        turn_id    = request.rel_url.query.get("turn_id")

        if not any([entity_id, subject_id, turn_id]):
            return web.json_response(
                {"error": "Provide entity_id, subject_id, or turn_id"}, status=400
            )

        conditions, params = [], []
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(int(entity_id))
        if subject_id:
            conditions.append("subject_id = ?")
            params.append(int(subject_id))
        if turn_id:
            conditions.append("turn_id = ?")
            params.append(int(turn_id))

        where = " OR ".join(conditions)
        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                f"SELECT id, entity_id, subject_id, turn_id, title, content, created_at, updated_at "
                f"FROM notes WHERE {where} ORDER BY created_at DESC",
                params,
            ).fetchall()
            return web.json_response([dict(r) for r in rows])
        finally:
            conn.close()

    async def _create_note(self, request: web.Request) -> web.Response:
        """POST /notes  body: {entity_id|subject_id|turn_id, title, content}"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        entity_id  = body.get("entity_id")
        subject_id = body.get("subject_id")
        turn_id    = body.get("turn_id")
        title      = body.get("title", "").strip()
        content    = body.get("content", "").strip()

        if not any([entity_id, subject_id, turn_id]):
            return web.json_response(
                {"error": "Provide entity_id, subject_id, or turn_id"}, status=400
            )

        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                "INSERT INTO notes (entity_id, subject_id, turn_id, title, content) VALUES (?,?,?,?,?)",
                (entity_id, subject_id, turn_id, title, content),
            )
            conn.commit()
            note_id = cursor.lastrowid
            row = conn.execute(
                "SELECT id, entity_id, subject_id, turn_id, title, content, created_at, updated_at "
                "FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, entity_id, subject_id, turn_id, title, content, created_at, updated_at "
                "FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
            return web.json_response(dict(row), status=201)
        finally:
            conn.close()

    async def _update_note(self, request: web.Request) -> web.Response:
        """PUT /notes/{note_id}  body: {title, content}"""
        note_id = int(request.match_info["note_id"])
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        title   = body.get("title", "").strip()
        content = body.get("content", "").strip()

        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                "UPDATE notes SET title = ?, content = ?, updated_at = datetime('now') WHERE id = ?",
                (title, content, note_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, entity_id, subject_id, turn_id, title, content, created_at, updated_at "
                "FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
            if not row:
                return web.json_response({"error": "Note not found"}, status=404)
            return web.json_response(dict(row))
        finally:
            conn.close()

    async def _delete_note(self, request: web.Request) -> web.Response:
        """DELETE /notes/{note_id}"""
        note_id = int(request.match_info["note_id"])
        conn = sqlite3.connect(self.config.db_path)
        try:
            conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return web.json_response({"ok": True})
        finally:
            conn.close()
