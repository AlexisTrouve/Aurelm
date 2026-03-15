"""Chat session management: persistent named sessions with tags and message history."""

from __future__ import annotations

import json
import sqlite3
import uuid as uuid_lib
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ChatMessage:
    """A single message in a session."""
    role: str  # 'user' or 'assistant'
    content: str
    message_type: str = 'text'  # 'text', 'compress', 'resume', 'thinking'
    tool_calls: list[dict] = field(default_factory=list)  # {name, input, result, tool_use_id}
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ChatSession:
    """A conversation session with tags and history."""
    session_id: str  # UUID for API reference
    name: str
    messages: list[ChatMessage] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    archived: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    compress_count: int = 0  # Number of compress blocks
    resume_count: int = 0    # Number of resume blocks (max 3)


class SessionManager:
    """Manages persistent conversation sessions in SQLite."""

    def __init__(self, db_path: str) -> None:
        # Normalize to absolute path so relative/absolute comparisons always match
        self.db_path = str(Path(db_path).resolve())

    def create_session(self, name: str, db_path: str | None = None) -> ChatSession:
        """Create a new session and save to DB.

        Args:
            name: Human-readable session name.
            db_path: The game database this session is scoped to.
                     Defaults to the SessionManager's own db_path.
        """
        session_id = str(uuid_lib.uuid4())
        session = ChatSession(session_id=session_id, name=name)
        # Scope the session to the given DB path (normalized to absolute)
        scoped_db_path = str(Path(db_path).resolve()) if db_path else self.db_path

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO chat_sessions (uuid, name, db_path, created_at, updated_at, last_message_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, name, scoped_db_path, session.created_at, session.updated_at, session.created_at)
            )
            conn.commit()

        return session

    def load_session(self, session_id: str) -> ChatSession | None:
        """Load session and all its messages from DB."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Load session metadata
            row = conn.execute(
                "SELECT uuid, name, archived, created_at, updated_at, last_message_at, "
                "compressed_message_count, resume_count FROM chat_sessions WHERE uuid = ?",
                (session_id,)
            ).fetchone()

            if not row:
                return None

            session = ChatSession(
                session_id=row['uuid'],
                name=row['name'],
                archived=bool(row['archived']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                compress_count=row['compressed_message_count'],
                resume_count=row['resume_count']
            )

            # Load all messages
            messages = conn.execute(
                "SELECT role, content, message_type, tool_calls, created_at FROM chat_messages "
                "WHERE session_id = (SELECT id FROM chat_sessions WHERE uuid = ?) "
                "ORDER BY message_order ASC",
                (session_id,)
            ).fetchall()

            for msg_row in messages:
                tool_calls = json.loads(msg_row['tool_calls']) if msg_row['tool_calls'] else []
                session.messages.append(ChatMessage(
                    role=msg_row['role'],
                    content=msg_row['content'],
                    message_type=msg_row['message_type'],
                    tool_calls=tool_calls,
                    created_at=msg_row['created_at']
                ))

            # Load tags
            tags = conn.execute(
                "SELECT tag FROM chat_session_tags WHERE session_id = (SELECT id FROM chat_sessions WHERE uuid = ?)",
                (session_id,)
            ).fetchall()
            session.tags = [t['tag'] for t in tags]

        return session

    def list_sessions(
        self,
        archived: bool = False,
        tag_filter: str | None = None,
        db_path: str | None = None,
    ) -> list[ChatSession]:
        """List all sessions, optionally filtered by archive status, tag, and db_path.

        Args:
            archived: If True, list archived sessions; otherwise active ones.
            tag_filter: Only sessions with this tag (exact match).
            db_path: If provided, restrict to sessions scoped to this game DB.
                     Sessions with db_path IS NULL are included as legacy/unscoped.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT uuid FROM chat_sessions WHERE archived = ?"
            params: list = [int(archived)]

            if tag_filter:
                query += (
                    " AND id IN (SELECT session_id FROM chat_session_tags WHERE tag = ?)"
                )
                params.append(tag_filter)

            # Filter by game DB: normalize path before comparing, include unscoped (NULL)
            if db_path:
                normalized = str(Path(db_path).resolve())
                query += " AND (db_path = ? OR db_path IS NULL)"
                params.append(normalized)

            query += " ORDER BY updated_at DESC"

            rows = conn.execute(query, params).fetchall()

        sessions = []
        for row in rows:
            session = self.load_session(row['uuid'])
            if session:
                sessions.append(session)

        return sessions

    def save_message(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to the session."""
        with sqlite3.connect(self.db_path) as conn:
            # Get session id and next message order
            row = conn.execute(
                "SELECT id, message_count FROM chat_sessions WHERE uuid = ?",
                (session_id,)
            ).fetchone()

            if not row:
                raise ValueError(f"Session {session_id} not found")

            session_db_id, current_count = row
            next_order = current_count

            tool_calls_json = json.dumps(message.tool_calls) if message.tool_calls else None

            conn.execute(
                "INSERT INTO chat_messages (session_id, message_order, role, content, message_type, tool_calls, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_db_id, next_order, message.role, message.content, message.message_type, tool_calls_json, message.created_at)
            )

            # Update session metadata
            conn.execute(
                "UPDATE chat_sessions SET message_count = message_count + 1, updated_at = ?, last_message_at = ? WHERE uuid = ?",
                (datetime.now().isoformat(), datetime.now().isoformat(), session_id)
            )
            conn.commit()

    def rename_session(self, session_id: str, new_name: str) -> None:
        """Rename a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET name = ?, updated_at = ? WHERE uuid = ?",
                (new_name, datetime.now().isoformat(), session_id)
            )
            conn.commit()

    def toggle_archive(self, session_id: str, archived: bool) -> None:
        """Archive or unarchive a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET archived = ?, updated_at = ? WHERE uuid = ?",
                (int(archived), datetime.now().isoformat(), session_id)
            )
            conn.commit()

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chat_sessions WHERE uuid = ?", (session_id,))
            conn.commit()

    def add_tag(self, session_id: str, tag: str, tag_type: str = 'free') -> None:
        """Add a tag to a session."""
        with sqlite3.connect(self.db_path) as conn:
            session_db_id = conn.execute(
                "SELECT id FROM chat_sessions WHERE uuid = ?",
                (session_id,)
            ).fetchone()

            if not session_db_id:
                raise ValueError(f"Session {session_id} not found")

            try:
                conn.execute(
                    "INSERT INTO chat_session_tags (session_id, tag, tag_type) VALUES (?, ?, ?)",
                    (session_db_id[0], tag, tag_type)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Tag already exists

    def remove_tag(self, session_id: str, tag: str) -> None:
        """Remove a tag from a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM chat_session_tags WHERE session_id = (SELECT id FROM chat_sessions WHERE uuid = ?) AND tag = ?",
                (session_id, tag)
            )
            conn.commit()

    def get_all_tags(self) -> list[str]:
        """Get all unique tags across all sessions (for filter UI)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT tag FROM chat_session_tags ORDER BY tag"
            ).fetchall()
        return [r[0] for r in rows]

    def count_messages_since_checkpoint(self, session_id: str) -> int:
        """Count text messages since the last compress or resume block.

        Used as one trigger for compression (threshold: 20 messages).
        Only counts 'text' message_type — compress/resume/thinking are excluded.
        """
        session = self.load_session(session_id)
        if not session:
            return 0

        count = 0
        for msg in reversed(session.messages):
            if msg.message_type in ('compress', 'resume'):
                break
            if msg.message_type == 'text':
                count += 1
        return count

    def estimate_tokens_since_checkpoint(self, session_id: str) -> int:
        """Estimate token count since last checkpoint (chars/4 heuristic).

        Includes message content AND tool call results — tool results are
        the biggest token consumers and must be accounted for.
        """
        session = self.load_session(session_id)
        if not session:
            return 0

        total_chars = 0
        for msg in reversed(session.messages):
            if msg.message_type in ('compress', 'resume'):
                break
            if msg.message_type == 'text':
                total_chars += len(msg.content)
                # Tool results stored as JSON dicts in tool_calls
                for tc in msg.tool_calls:
                    total_chars += len(tc.get("result", ""))
                    total_chars += len(tc.get("input_summary", ""))
        return total_chars // 4

    def build_llm_history(self, session_id: str) -> list[dict]:
        """Build optimized message history for the LLM.

        Finds the latest resume or compress checkpoint and returns:
        - The checkpoint summary as a leading context message
        - All raw text messages after that checkpoint

        If no checkpoint exists, returns all text messages (original behavior).
        Tool calls stored in DB are NOT reconstructed into the Anthropic
        tool_use/tool_result format — they're summarized in the flat text.
        """
        session = self.load_session(session_id)
        if not session:
            return []

        # Find the latest checkpoint (resume takes priority over compress)
        checkpoint_idx = -1
        for i in range(len(session.messages) - 1, -1, -1):
            if session.messages[i].message_type in ('compress', 'resume'):
                checkpoint_idx = i
                break

        if checkpoint_idx >= 0:
            # Build history: checkpoint summary + messages after it
            checkpoint = session.messages[checkpoint_idx]
            history = []

            # Inject the summary as a user message so Claude knows the context
            summary_label = (
                "RESUME DE LA CONVERSATION" if checkpoint.message_type == 'resume'
                else "RESUME DES ECHANGES PRECEDENTS"
            )
            history.append({
                "role": "user",
                "content": f"[{summary_label}]\n{checkpoint.content}",
            })
            # Add a fake assistant ack so the alternation is valid
            history.append({
                "role": "assistant",
                "content": "Compris, je dispose du contexte resume ci-dessus. Comment puis-je t'aider ?",
            })

            # Append all text messages after the checkpoint
            for msg in session.messages[checkpoint_idx + 1:]:
                if msg.message_type == 'text':
                    history.append({"role": msg.role, "content": msg.content})

            return history

        # No checkpoint — return all text messages
        return [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
            if msg.message_type == 'text'
        ]

    def get_messages_for_compression(
        self, session_id: str, keep_recent: int = 10,
    ) -> list[ChatMessage]:
        """Get the OLDEST text messages since checkpoint, keeping recent ones intact.

        Per PM spec: compress the 10 oldest, keep the 10 most recent untouched.
        Only the oldest batch is returned for LLM summarization.
        """
        session = self.load_session(session_id)
        if not session:
            return []

        # Collect all text messages since last checkpoint
        all_since_checkpoint = []
        for msg in reversed(session.messages):
            if msg.message_type in ('compress', 'resume'):
                break
            if msg.message_type == 'text':
                all_since_checkpoint.append(msg)
        all_since_checkpoint.reverse()

        # Only compress if we have enough to split (keep_recent stay intact)
        if len(all_since_checkpoint) <= keep_recent:
            return []

        # Return only the oldest batch — the recent ones stay in raw form
        return all_since_checkpoint[:-keep_recent]

    def get_compress_blocks_since_resume(self, session_id: str) -> list[ChatMessage]:
        """Get compress blocks since the last resume, for merging into a resume."""
        session = self.load_session(session_id)
        if not session:
            return []

        result = []
        for msg in reversed(session.messages):
            if msg.message_type == 'resume':
                break
            if msg.message_type == 'compress':
                result.append(msg)
        result.reverse()
        return result

    def add_compress_block(self, session_id: str, compressed_content: str) -> None:
        """Add a compress block (phase 1: >=20 messages since last checkpoint)."""
        compress_msg = ChatMessage(
            role='assistant',
            content=compressed_content,
            message_type='compress'
        )
        self.save_message(session_id, compress_msg)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET compressed_message_count = compressed_message_count + 1 WHERE uuid = ?",
                (session_id,)
            )
            conn.commit()

    def add_resume_block(self, session_id: str, resume_content: str) -> None:
        """Add a resume block (phase 2: >=4 compresses since last resume, max 3 resumes).

        When a resume is created, reset compressed_message_count since those
        compresses are now folded into the resume.
        """
        session = self.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.resume_count >= 3:
            # Drop oldest resume by message_order (more reliable than created_at)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM chat_messages WHERE rowid = ("
                    "  SELECT cm.rowid FROM chat_messages cm"
                    "  JOIN chat_sessions cs ON cs.id = cm.session_id"
                    "  WHERE cs.uuid = ? AND cm.message_type = 'resume'"
                    "  ORDER BY cm.message_order ASC LIMIT 1"
                    ")",
                    (session_id,)
                )
                conn.commit()
        else:
            # Only increment if not replacing
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE chat_sessions SET resume_count = resume_count + 1 WHERE uuid = ?",
                    (session_id,)
                )
                conn.commit()

        resume_msg = ChatMessage(
            role='assistant',
            content=resume_content,
            message_type='resume'
        )
        self.save_message(session_id, resume_msg)

        # Reset compress count — those compresses are folded into this resume
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET compressed_message_count = 0 WHERE uuid = ?",
                (session_id,)
            )
            conn.commit()
