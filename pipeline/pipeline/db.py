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


# ============================================================
# Incremental Pipeline Tracking
# ============================================================


def get_unprocessed_turns(conn: sqlite3.Connection, civ_id: int | None = None) -> list[sqlite3.Row]:
    """Get all turns that haven't been processed yet.

    A turn is considered unprocessed if it doesn't have an entry in pipeline_turn_status.

    Args:
        conn: Database connection
        civ_id: Optional civilization ID to filter by

    Returns:
        List of turn rows (turn_turns table)
    """
    if civ_id is not None:
        query = """
            SELECT t.* FROM turn_turns t
            LEFT JOIN pipeline_turn_status pts ON t.id = pts.turn_id
            WHERE t.civ_id = ? AND pts.turn_id IS NULL
            ORDER BY t.turn_number
        """
        return conn.execute(query, (civ_id,)).fetchall()
    else:
        query = """
            SELECT t.* FROM turn_turns t
            LEFT JOIN pipeline_turn_status pts ON t.id = pts.turn_id
            WHERE pts.turn_id IS NULL
            ORDER BY t.civ_id, t.turn_number
        """
        return conn.execute(query).fetchall()


def mark_turn_processed(conn: sqlite3.Connection, turn_id: int, run_id: int) -> None:
    """Mark a turn as processed.

    Args:
        conn: Database connection
        turn_id: Turn ID to mark as processed
        run_id: Pipeline run ID that processed this turn
    """
    conn.execute(
        "INSERT OR REPLACE INTO pipeline_turn_status (turn_id, pipeline_run_id) VALUES (?, ?)",
        (turn_id, run_id),
    )


def mark_all_turns_unprocessed(conn: sqlite3.Connection) -> None:
    """Clear all turn processing status, forcing a full reprocess."""
    conn.execute("DELETE FROM pipeline_turn_status")
    conn.commit()


def update_progress(
    conn: sqlite3.Connection,
    run_id: int,
    phase: str,
    civ_id: int | None,
    civ_name: str | None,
    current: int,
    total: int,
    unit_type: str,
    status: str = "running",
) -> None:
    """Update pipeline progress for Flutter UI polling.

    Args:
        conn: Database connection
        run_id: Pipeline run ID
        phase: Phase name ('pipeline', 'profiler', 'wiki')
        civ_id: Civilization ID (None for wiki phase)
        civ_name: Civilization name (None for wiki phase)
        current: Current unit number (0-indexed or 1-indexed depending on caller)
        total: Total units to process
        unit_type: Unit type ('turn', 'entity', 'page')
        status: Status ('running', 'completed', 'failed')
    """
    from datetime import datetime

    conn.execute(
        """INSERT OR REPLACE INTO pipeline_progress
           (pipeline_run_id, phase, civ_id, civ_name, total_units, current_unit, unit_type, status, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, phase, civ_id, civ_name, total, current, unit_type, status, datetime.now().isoformat()),
    )
