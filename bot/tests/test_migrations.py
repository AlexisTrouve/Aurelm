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
