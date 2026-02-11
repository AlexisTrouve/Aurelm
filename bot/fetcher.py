"""Fetch Discord channel history and store in DB."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

log = logging.getLogger(__name__)


async def fetch_and_store(
    channel: discord.TextChannel,
    db_path: str,
) -> int:
    """Fetch messages from a Discord channel and INSERT OR IGNORE into turn_raw_messages.

    Fetches messages after the last known message in DB for this channel.
    Returns the number of new messages inserted.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Find the most recent message we already have for this channel
    row = conn.execute(
        "SELECT MAX(timestamp) FROM turn_raw_messages WHERE discord_channel_id = ?",
        (str(channel.id),),
    ).fetchone()

    after_dt = None
    if row and row[0]:
        try:
            after_dt = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

    inserted = 0
    async for message in channel.history(limit=None, after=after_dt, oldest_first=True):
        # Skip bot messages
        if message.author.bot:
            continue

        # Skip empty messages
        if not message.content and not message.attachments:
            continue

        discord_msg_id = str(message.id)
        channel_id = str(message.channel.id)
        author_id = str(message.author.id)
        author_name = message.author.display_name
        content = message.content or ""
        timestamp = message.created_at.isoformat()

        attachments = None
        if message.attachments:
            import json
            attachments = json.dumps([a.url for a in message.attachments])

        try:
            conn.execute(
                """INSERT OR IGNORE INTO turn_raw_messages
                   (discord_message_id, discord_channel_id, author_id, author_name, content, timestamp, attachments)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (discord_msg_id, channel_id, author_id, author_name, content, timestamp, attachments),
            )
            if conn.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            pass  # Duplicate, skip

    conn.commit()
    conn.close()

    log.info("Fetched %d new messages from #%s", inserted, channel.name)
    return inserted
