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


def _find_migrations_dir(db_file: Path) -> Path | None:
    """Locate database/migrations/, or None if it truly isn't anywhere expected.

    WHY two candidates: historically this was derived from the DB's location
    (`<db>/../../database/migrations`), which only holds when the DB sits inside
    the repo — true in dev, false for a user whose DB lives in Documents\\Aurelm.
    A packaged install has the DB somewhere else entirely, so we ALSO look relative
    to the bot package, where the build script copies the migrations. The DB-relative
    path is tried first so a dev checkout keeps its existing behaviour exactly.
    """
    candidates = [
        db_file.parent.parent / "database" / "migrations",   # dev: DB inside the repo
        Path(__file__).resolve().parent.parent / "database" / "migrations",  # bundle: next to bot/
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def apply_migrations(db_path: str) -> None:
    """Apply all pending migrations from database/migrations/ directory.

    Migrations are SQL files named NNN_name.sql (e.g., 016_chat_sessions.sql).
    Applies them in order if not already applied.
    Creates the database if it doesn't exist.
    """
    db_file = Path(db_path)
    is_new_db = not db_file.exists()

    migrations_dir = _find_migrations_dir(db_file)
    if migrations_dir is None:
        # A fresh DB with no migrations to apply is not a warning — it's a broken
        # install: every table is missing and the app is dead. Fail loudly.
        raise FileNotFoundError(
            "database/migrations not found. Looked next to the DB and next to the "
            "bot package. In a packaged build the build script must copy "
            "database/migrations into the bundle."
        )

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

    # Parse each migration's version from its NNN_ prefix (in filename order).
    parsed: list[tuple[int, Path]] = []
    for mig_file in sorted(migrations_dir.glob("*.sql")):
        try:
            version = int(mig_file.stem.split("_")[0])
        except (ValueError, IndexError):
            log.warning(f"Skipping invalid migration file: {mig_file.name}")
            continue
        parsed.append((version, mig_file))

    # Guard: two files sharing a number is a bug — the apply step keys by number, so
    # the second would be silently skipped. This shipped once (035/036 map vs
    # pipeline/civ collisions left map_cell_discovery uncreated on some DBs), so we
    # now fail loudly at dev time instead of losing a table in prod.
    seen: dict[int, str] = {}
    for version, mig_file in parsed:
        if version in seen:
            raise ValueError(
                f"duplicate migration number {version}: {seen[version]} and "
                f"{mig_file.name} — renumber one (each NNN_ prefix must be unique)."
            )
        seen[version] = mig_file.name

    # Apply every migration whose number is NOT already recorded — a SET membership
    # check, not "> MAX(version)". WHY: the old max-based check silently skipped any
    # migration added with a number <= the DB's current max (a late file, or the 2nd
    # of a duplicate pair). A set applies each unique-numbered migration exactly once,
    # regardless of insertion order; unique numbers are guaranteed by the guard above.
    applied = {row[0] for row in conn.execute("SELECT version FROM _schema_version")}
    for version, mig_file in parsed:
        if version in applied:
            continue
        log.info(f"Applying migration {version}: {mig_file.name}")
        try:
            with open(mig_file, "r", encoding="utf-8") as f:
                sql = f.read()
            _execute_migration_sql(conn, sql, migrations_dir)
            conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (version,))
            conn.commit()
            applied.add(version)
            log.info(f"Migration {version} applied successfully")
        except Exception as e:
            log.error(f"Failed to apply migration {version}: {e}")
            conn.rollback()
            raise

    conn.close()
    log.info(f"Database schema up to date ({len(applied)} migrations applied)")
