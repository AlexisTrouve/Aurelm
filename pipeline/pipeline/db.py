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


def run_migrations(db_path: str) -> None:
    """Apply pending migrations to an existing database.

    Safe to call on fresh DBs (skips already-applied columns) and on existing DBs.
    """
    migrations_dir = SCHEMA_PATH.parent / "migrations"
    if not migrations_dir.exists():
        return
    conn = get_connection(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        applied = {row["filename"] for row in conn.execute("SELECT filename FROM _migrations").fetchall()}

        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name == "001_initial.sql":
                continue
            if sql_file.name in applied:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            # Run each statement individually to handle "duplicate column" gracefully
            for statement in sql.split(";"):
                statement = statement.strip()
                if not statement or statement.startswith("--"):
                    continue
                try:
                    conn.execute(statement)
                except sqlite3.OperationalError as e:
                    if "duplicate column" in str(e):
                        continue  # Column already exists (fresh DB from updated schema)
                    raise
            conn.execute("INSERT INTO _migrations (filename) VALUES (?)", (sql_file.name,))
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
