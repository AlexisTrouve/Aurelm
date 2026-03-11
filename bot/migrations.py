"""Auto-apply database migrations on startup."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)


def _execute_migration_sql(conn: sqlite3.Connection, sql: str, migration_dir: Path) -> None:
    """Execute migration SQL by parsing individual statements.

    Handles both standard SQL and SQLite dot-commands like `.read`.
    Splits on semicolons and executes each statement separately.
    """
    # Process lines: handle dot-commands and remove comments
    lines = []
    for line in sql.split("\n"):
        # Handle .read command (SQLite CLI dot-command)
        if line.strip().startswith(".read"):
            # Extract filename and read/execute it
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                ref_file = migration_dir / parts[1]
                if ref_file.exists():
                    with open(ref_file, "r", encoding="utf-8") as f:
                        ref_sql = f.read()
                    _execute_migration_sql(conn, ref_sql, migration_dir)
        elif line.strip() and not line.strip().startswith("--"):
            # Skip comments and blank lines
            lines.append(line.split("--")[0].rstrip())

    # Rejoin and split by semicolon to get individual statements
    cleaned_sql = " ".join(lines)
    statements = [
        stmt.strip()
        for stmt in cleaned_sql.split(";")
        if stmt.strip()
    ]

    # Execute each statement, gracefully handling idempotent operations
    for stmt in statements:
        if stmt.strip():
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                # Ignore duplicate column errors (migration already applied on schema load)
                if "duplicate column name" in str(e):
                    log.debug(f"Column already exists (idempotent): {stmt[:50]}...")
                else:
                    raise
    conn.commit()


def apply_migrations(db_path: str) -> None:
    """Apply all pending migrations from database/migrations/ directory.

    Migrations are SQL files named NNN_name.sql (e.g., 016_chat_sessions.sql).
    Applies them in order if not already applied.
    Creates the database if it doesn't exist.
    """
    db_file = Path(db_path)
    is_new_db = not db_file.exists()

    migrations_dir = db_file.parent.parent / "database" / "migrations"
    if not migrations_dir.exists():
        log.warning(f"Migrations directory {migrations_dir} not found - skipping")
        return

    # Connect to database (creates it if doesn't exist)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create migration tracking table if not exists
    conn.execute(
        """CREATE TABLE IF NOT EXISTS _schema_version (
            id INTEGER PRIMARY KEY,
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()

    # Get current schema version
    cursor = conn.execute("SELECT COALESCE(MAX(version), 0) FROM _schema_version")
    current_version = cursor.fetchone()[0]

    # Find all migrations
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for mig_file in migration_files:
        # Extract version from filename (NNN_name.sql)
        try:
            version = int(mig_file.stem.split("_")[0])
        except (ValueError, IndexError):
            log.warning(f"Skipping invalid migration file: {mig_file.name}")
            continue

        # Apply if not yet applied
        if version > current_version:
            log.info(f"Applying migration {version}: {mig_file.name}")
            try:
                with open(mig_file, "r", encoding="utf-8") as f:
                    sql = f.read()
                _execute_migration_sql(conn, sql, migrations_dir)
                conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (version,))
                conn.commit()
                log.info(f"Migration {version} applied successfully")
            except Exception as e:
                log.error(f"Failed to apply migration {version}: {e}")
                conn.rollback()
                raise

    conn.close()
    log.info(f"Database schema up to date (version {current_version})")
