"""Chat session management: persistent named sessions with tags and message history."""

from __future__ import annotations

import json
import sqlite3
import uuid as uuid_lib
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
        self.db_path = db_path

    def create_session(self, name: str) -> ChatSession:
        """Create a new session and save to DB."""
        session_id = str(uuid_lib.uuid4())
        session = ChatSession(session_id=session_id, name=name)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO chat_sessions (uuid, name, created_at, updated_at, last_message_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, name, session.created_at, session.updated_at, session.created_at)
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

    def list_sessions(self, archived: bool = False, tag_filter: str | None = None) -> list[ChatSession]:
        """List all sessions, optionally filtered by archive status and tag."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT uuid FROM chat_sessions WHERE archived = ?"
            params: list = [int(archived)]

            if tag_filter:
                query += (
                    " AND id IN (SELECT session_id FROM chat_session_tags WHERE tag = ?)"
                )
                params.append(tag_filter)

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

    def add_compress_block(self, session_id: str, compressed_content: str) -> None:
        """Add a compress block (phase 1: >=20 messages)."""
        session = self.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        compress_msg = ChatMessage(
            role='assistant',
            content=compressed_content,
            message_type='compress'
        )
        self.save_message(session_id, compress_msg)

        # Update compress count
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET compressed_message_count = compressed_message_count + 1 WHERE uuid = ?",
                (session_id,)
            )
            conn.commit()

    def add_resume_block(self, session_id: str, resume_content: str) -> None:
        """Add a resume block (phase 2: >=4 compresses, max 3 resumes)."""
        session = self.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.resume_count >= 3:
            # Drop oldest resume: find and delete it
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM chat_messages WHERE session_id = (SELECT id FROM chat_sessions WHERE uuid = ?) "
                    "AND message_type = 'resume' ORDER BY created_at ASC LIMIT 1",
                    (session_id,)
                )
                conn.commit()
        else:
            session.resume_count += 1

        resume_msg = ChatMessage(
            role='assistant',
            content=resume_content,
            message_type='resume'
        )
        self.save_message(session_id, resume_msg)

        # Update resume count
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE chat_sessions SET resume_count = resume_count + 1 WHERE uuid = ?",
                (session_id,)
            )
            conn.commit()
