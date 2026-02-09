"""Discord message ingestion — fetches and normalizes raw messages from the database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class RawMessage:
    id: int
    discord_message_id: str
    channel_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: str


def fetch_unprocessed_messages(db_path: str, channel_id: str) -> list[RawMessage]:
    """Fetch raw messages that haven't been assigned to a turn yet."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT rm.* FROM turn_raw_messages rm
            WHERE rm.discord_channel_id = ?
            AND rm.id NOT IN (
                SELECT value FROM turn_turns, json_each(turn_turns.raw_message_ids)
            )
            ORDER BY rm.timestamp ASC
            """,
            (channel_id,),
        ).fetchall()
        return [
            RawMessage(
                id=row["id"],
                discord_message_id=row["discord_message_id"],
                channel_id=row["discord_channel_id"],
                author_id=row["author_id"],
                author_name=row["author_name"],
                content=row["content"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]
    finally:
        conn.close()


def normalize_content(content: str) -> str:
    """Normalize Discord message content: strip formatting, fix encoding."""
    # Remove Discord-specific formatting artifacts
    text = content.strip()
    # Normalize whitespace
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines)
