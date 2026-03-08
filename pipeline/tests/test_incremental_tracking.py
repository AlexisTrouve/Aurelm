"""Tests for incremental pipeline tracking."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from pipeline.db import (
    get_connection,
    init_db,
    run_migrations,
    get_unprocessed_turns,
    mark_turn_processed,
    mark_all_turns_unprocessed,
    update_progress,
    register_civilization,
    insert_turn_stats,
    update_run_usage,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    run_migrations(db_path)
    yield db_path
    # Try to delete, but don't fail if it's still locked
    try:
        Path(db_path).unlink()
    except PermissionError:
        pass


def test_tracking_tables_exist(temp_db):
    """Verify that tracking tables are created by migrations."""
    conn = get_connection(temp_db)

    # Check pipeline_turn_status exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_turn_status'"
    )
    assert cursor.fetchone() is not None

    # Check pipeline_progress exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_progress'"
    )
    assert cursor.fetchone() is not None

    conn.close()


def test_mark_turn_processed(temp_db):
    """Test marking a turn as processed."""
    conn = get_connection(temp_db)

    # Create test data
    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
        (civ_id, 1),
    )
    turn_id = cursor.lastrowid

    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    # Mark turn as processed
    mark_turn_processed(conn, turn_id, run_id)
    conn.commit()

    # Verify it's marked
    row = conn.execute(
        "SELECT turn_id, pipeline_run_id FROM pipeline_turn_status WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()

    assert row is not None
    assert row["turn_id"] == turn_id
    assert row["pipeline_run_id"] == run_id

    conn.close()


def test_get_unprocessed_turns(temp_db):
    """Test fetching unprocessed turns."""
    conn = get_connection(temp_db)

    # Create test data
    civ_id = register_civilization(temp_db, "Test Civ")

    # Create 3 turns
    for i in range(1, 4):
        conn.execute(
            "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
            (civ_id, i),
        )
    conn.commit()

    # All turns should be unprocessed
    unprocessed = get_unprocessed_turns(conn, civ_id)
    assert len(unprocessed) == 3

    # Mark turn 2 as processed
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    turn_2_id = conn.execute(
        "SELECT id FROM turn_turns WHERE civ_id = ? AND turn_number = 2", (civ_id,)
    ).fetchone()["id"]
    mark_turn_processed(conn, turn_2_id, run_id)
    conn.commit()

    # Now only 2 should be unprocessed
    unprocessed = get_unprocessed_turns(conn, civ_id)
    assert len(unprocessed) == 2

    # Verify turn 2 is not in the list
    turn_numbers = [t["turn_number"] for t in unprocessed]
    assert 2 not in turn_numbers
    assert 1 in turn_numbers
    assert 3 in turn_numbers

    conn.close()


def test_mark_all_turns_unprocessed(temp_db):
    """Test clearing all turn processing status."""
    conn = get_connection(temp_db)

    # Create test data
    civ_id = register_civilization(temp_db, "Test Civ")

    # Create 2 turns and mark them as processed
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid

    for i in range(1, 3):
        cursor = conn.execute(
            "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
            (civ_id, i),
        )
        turn_id = cursor.lastrowid
        mark_turn_processed(conn, turn_id, run_id)
    conn.commit()

    # Verify both are marked as processed
    unprocessed = get_unprocessed_turns(conn, civ_id)
    assert len(unprocessed) == 0

    # Clear all processing status
    mark_all_turns_unprocessed(conn)

    # Now all should be unprocessed again
    unprocessed = get_unprocessed_turns(conn, civ_id)
    assert len(unprocessed) == 2

    conn.close()


def test_update_progress(temp_db):
    """Test updating pipeline progress."""
    conn = get_connection(temp_db)

    # Create test data
    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    # Update progress
    update_progress(
        conn, run_id, "pipeline", civ_id, "Test Civ",
        5, 10, "turn", "running"
    )
    conn.commit()

    # Verify progress was recorded
    row = conn.execute(
        """SELECT phase, civ_id, civ_name, total_units, current_unit, unit_type, status
           FROM pipeline_progress
           WHERE pipeline_run_id = ? AND phase = 'pipeline'""",
        (run_id,),
    ).fetchone()

    assert row is not None
    assert row["phase"] == "pipeline"
    assert row["civ_id"] == civ_id
    assert row["civ_name"] == "Test Civ"
    assert row["total_units"] == 10
    assert row["current_unit"] == 5
    assert row["unit_type"] == "turn"
    assert row["status"] == "running"

    # Update again (should replace due to UNIQUE constraint)
    update_progress(
        conn, run_id, "pipeline", civ_id, "Test Civ",
        10, 10, "turn", "completed"
    )
    conn.commit()

    # Verify only one record exists
    count = conn.execute(
        "SELECT count(*) FROM pipeline_progress WHERE pipeline_run_id = ? AND phase = 'pipeline'",
        (run_id,),
    ).fetchone()[0]
    assert count == 1

    # Verify it was updated
    row = conn.execute(
        "SELECT current_unit, status FROM pipeline_progress WHERE pipeline_run_id = ? AND phase = 'pipeline'",
        (run_id,),
    ).fetchone()
    assert row["current_unit"] == 10
    assert row["status"] == "completed"

    conn.close()


def test_turn_stats_table_exists(temp_db):
    """Verify that migration 008 created pipeline_turn_stats and added columns to pipeline_runs."""
    conn = get_connection(temp_db)

    # Table exists
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_turn_stats'"
    ).fetchone()
    assert row is not None, "pipeline_turn_stats table should exist after migrations"

    # Key columns exist (SQLite PRAGMA returns one row per column)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(pipeline_turn_stats)").fetchall()}
    for expected in ("run_id", "turn_id", "source", "text_chars", "sys_prompt_chars",
                     "chunks", "raw_entities", "after_dedup", "final_entities",
                     "est_tokens", "est_cost_usd"):
        assert expected in cols, f"Column '{expected}' missing from pipeline_turn_stats"

    # Columns added to pipeline_runs
    run_cols = {r["name"] for r in conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()}
    assert "total_tokens" in run_cols
    assert "total_cost_usd" in run_cols

    conn.close()


def test_insert_turn_stats_gm(temp_db):
    """Test inserting GM extraction stats for a turn."""
    conn = get_connection(temp_db)

    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
        (civ_id, 1),
    )
    turn_id = cursor.lastrowid
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    insert_turn_stats(
        conn, run_id, turn_id, "gm",
        text_chars=2500,
        sys_prompt_chars=800,
        chunks=3,
        raw_entities=12,
        after_dedup=9,
        final_entities=7,
        est_tokens=950,
        est_cost_usd=0.0019,
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM pipeline_turn_stats WHERE run_id=? AND turn_id=? AND source='gm'",
        (run_id, turn_id),
    ).fetchone()

    assert row is not None
    assert row["text_chars"] == 2500
    assert row["sys_prompt_chars"] == 800
    assert row["chunks"] == 3
    assert row["raw_entities"] == 12
    assert row["after_dedup"] == 9
    assert row["final_entities"] == 7
    assert row["est_tokens"] == 950
    assert abs(row["est_cost_usd"] - 0.0019) < 1e-9

    conn.close()


def test_insert_turn_stats_pj(temp_db):
    """Test inserting PJ stats — zero entity counts, just text metrics."""
    conn = get_connection(temp_db)

    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
        (civ_id, 2),
    )
    turn_id = cursor.lastrowid
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    insert_turn_stats(
        conn, run_id, turn_id, "pj",
        text_chars=1800,
        sys_prompt_chars=0,
        chunks=1,
        raw_entities=0,
        after_dedup=0,
        final_entities=0,
        est_tokens=450,
        est_cost_usd=0.0,
    )
    conn.commit()

    row = conn.execute(
        "SELECT source, raw_entities, final_entities FROM pipeline_turn_stats WHERE run_id=? AND turn_id=?",
        (run_id, turn_id),
    ).fetchone()

    assert row is not None
    assert row["source"] == "pj"
    assert row["raw_entities"] == 0
    assert row["final_entities"] == 0

    conn.close()


def test_insert_turn_stats_idempotent(temp_db):
    """INSERT OR REPLACE: re-inserting same (run_id, turn_id, source) updates the row."""
    conn = get_connection(temp_db)

    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type) VALUES (?, ?, '[]', 'standard')",
        (civ_id, 1),
    )
    turn_id = cursor.lastrowid
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    # First insert
    insert_turn_stats(conn, run_id, turn_id, "gm",
        text_chars=100, sys_prompt_chars=0, chunks=1,
        raw_entities=2, after_dedup=2, final_entities=2,
        est_tokens=50, est_cost_usd=0.001)
    conn.commit()

    # Second insert with different values (simulates re-run)
    insert_turn_stats(conn, run_id, turn_id, "gm",
        text_chars=200, sys_prompt_chars=50, chunks=2,
        raw_entities=5, after_dedup=4, final_entities=3,
        est_tokens=120, est_cost_usd=0.002)
    conn.commit()

    # Should have exactly one row, with the updated values
    rows = conn.execute(
        "SELECT * FROM pipeline_turn_stats WHERE run_id=? AND turn_id=? AND source='gm'",
        (run_id, turn_id),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["final_entities"] == 3
    assert rows[0]["text_chars"] == 200

    conn.close()


def test_update_run_usage(temp_db):
    """Test updating total token and cost counters on a pipeline run."""
    conn = get_connection(temp_db)

    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    update_run_usage(conn, run_id, total_tokens=42000, total_cost_usd=0.0168)
    conn.commit()

    row = conn.execute(
        "SELECT total_tokens, total_cost_usd FROM pipeline_runs WHERE id=?",
        (run_id,),
    ).fetchone()

    assert row is not None
    assert row["total_tokens"] == 42000
    assert abs(row["total_cost_usd"] - 0.0168) < 1e-9

    conn.close()


def test_progress_multiple_phases(temp_db):
    """Test tracking progress across multiple phases."""
    conn = get_connection(temp_db)

    # Create test data
    civ_id = register_civilization(temp_db, "Test Civ")
    cursor = conn.execute("INSERT INTO pipeline_runs (status) VALUES ('running')")
    run_id = cursor.lastrowid
    conn.commit()

    # Simulate pipeline phases
    phases = [
        ("pipeline", civ_id, "Test Civ", 10, "turn"),
        ("profiler", civ_id, "Test Civ", 50, "entity"),
        ("wiki", None, None, 30, "page"),
    ]

    for phase, civ, civ_name, total, unit_type in phases:
        update_progress(conn, run_id, phase, civ, civ_name, total, total, unit_type, "completed")
        conn.commit()

    # Verify all phases were recorded
    rows = conn.execute(
        "SELECT phase, civ_id, total_units, unit_type, status FROM pipeline_progress WHERE pipeline_run_id = ? ORDER BY phase",
        (run_id,),
    ).fetchall()

    assert len(rows) == 3

    # Check pipeline phase
    assert rows[0]["phase"] == "pipeline"
    assert rows[0]["total_units"] == 10
    assert rows[0]["unit_type"] == "turn"

    # Check profiler phase
    assert rows[1]["phase"] == "profiler"
    assert rows[1]["total_units"] == 50
    assert rows[1]["unit_type"] == "entity"

    # Check wiki phase
    assert rows[2]["phase"] == "wiki"
    assert rows[2]["total_units"] == 30
    assert rows[2]["unit_type"] == "page"
    assert rows[2]["civ_id"] is None  # wiki is global

    conn.close()
