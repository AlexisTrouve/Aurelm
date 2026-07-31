"""Tests for migration discovery + application.

WHY this exists: `apply_migrations` used to derive the migrations directory purely
from the DB's location (`<db>/../../database/migrations`). That holds only when the
DB lives inside the repo — true in dev, false for a packaged install where the DB
sits in the user's Documents folder. The result was a fresh DB with ZERO tables and
an app that died on first use, while /health still answered 200. These lock the fix:
migrations are found relative to the bot package too, a fresh DB gets a real schema,
and a genuinely missing migrations dir fails loudly instead of skipping.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bot.migrations import _find_migrations_dir, apply_migrations


def test_finds_migrations_relative_to_the_bot_package():
    """A DB outside the repo (the packaged case) still locates migrations.

    tmp_path is nowhere near database/migrations, so the DB-relative candidate
    misses and the package-relative one must catch it.
    """
    db_file = Path("/some/user/Documents/Aurelm/aurelm.db")
    found = _find_migrations_dir(db_file)
    assert found is not None, "migrations must be found relative to the bot package"
    assert found.name == "migrations"
    assert (found / ".." ).resolve().name == "database"


def test_fresh_db_gets_a_real_schema(tmp_path):
    """Applying migrations to a non-existent DB creates the core tables."""
    db = tmp_path / "fresh.db"
    assert not db.exists()

    apply_migrations(str(db))

    assert db.exists()
    tables = {
        r[0]
        for r in sqlite3.connect(db).execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    # The exact count grows with the schema; assert the anchors, not a magic number.
    assert "civ_civilizations" in tables
    assert "turn_turns" in tables
    assert "entity_entities" in tables


def test_missing_migrations_dir_raises_not_skips(tmp_path, monkeypatch):
    """A truly missing migrations dir is a broken install — fail loudly.

    Silently skipping is how the original bug shipped: no tables, no error.
    """
    monkeypatch.setattr(
        "bot.migrations._find_migrations_dir", lambda _db: None
    )
    with pytest.raises(FileNotFoundError, match="database/migrations"):
        apply_migrations(str(tmp_path / "x.db"))


def _versions(db) -> list[int]:
    return [r[0] for r in sqlite3.connect(db).execute(
        "SELECT version FROM _schema_version ORDER BY version")]


def test_fresh_db_records_each_version_once(tmp_path):
    """The collision bug (two 035_/036_ files) double-recorded versions AND, on an
    incremental upgrade, silently dropped the 2nd of a pair. A fresh DB must now record
    every migration exactly once — no duplicate version rows."""
    db = tmp_path / "fresh.db"
    apply_migrations(str(db))
    vers = _versions(db)
    assert len(vers) == len(set(vers)), f"duplicate version rows: {vers}"


def test_fresh_db_has_the_previously_colliding_map_migrations(tmp_path):
    """The two migrations that shared numbers with pipeline/civ ones must both land:
    map_maps.metadata (was 035) and the map_cell_discovery table (was 036). Before the
    renumber, a DB at the colliding number never got the second one."""
    db = tmp_path / "fresh.db"
    apply_migrations(str(db))
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "map_cell_discovery" in tables            # was 036_map_cell_discovery
    cols = {row[1] for row in conn.execute("PRAGMA table_info(map_maps)")}
    assert "metadata" in cols                        # was 035_map_maps_metadata


def test_reapplying_migrations_is_idempotent(tmp_path):
    """Running the migrator twice is a no-op: no crash, no new rows."""
    db = tmp_path / "fresh.db"
    apply_migrations(str(db))
    before = _versions(db)
    apply_migrations(str(db))                        # second run
    assert _versions(db) == before


def test_duplicate_migration_number_fails_loudly(tmp_path, monkeypatch):
    """Two files sharing a number must raise (the SET-based apply would otherwise skip
    the second silently) — the guard that stops this class of bug recurring."""
    migs = tmp_path / "migs"
    migs.mkdir()
    (migs / "001_alpha.sql").write_text("CREATE TABLE alpha (x INTEGER);", encoding="utf-8")
    (migs / "001_beta.sql").write_text("CREATE TABLE beta (x INTEGER);", encoding="utf-8")
    monkeypatch.setattr("bot.migrations._find_migrations_dir", lambda _db: migs)
    with pytest.raises(ValueError, match="duplicate migration number 1"):
        apply_migrations(str(tmp_path / "dup.db"))
