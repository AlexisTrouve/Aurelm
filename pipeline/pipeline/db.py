"""Database initialization and helpers for the Aurelm pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a connection with foreign keys enforced and row factory set."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str, schema_path: Path | None = None) -> None:
    """Initialize the database from schema.sql if tables don't exist."""
    schema = (schema_path or SCHEMA_PATH).read_text(encoding="utf-8")
    conn = get_connection(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def register_civilization(
    db_path: str,
    name: str,
    player_name: str | None = None,
    discord_channel_id: str | None = None,
) -> int:
    """Register a civilization, returning its id. Idempotent — returns existing id if already registered."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM civ_civilizations WHERE name = ?", (name,)
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO civ_civilizations (name, player_name, discord_channel_id) VALUES (?, ?, ?)",
            (name, player_name, discord_channel_id),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_civilization_id(db_path: str, name: str) -> int | None:
    """Look up a civilization id by name."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM civ_civilizations WHERE name = ?", (name,)
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()
