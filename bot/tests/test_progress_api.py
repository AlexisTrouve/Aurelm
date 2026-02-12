"""Tests for the /progress API endpoint."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from bot.config import BotConfig
from bot.server import BotServer


@pytest.fixture
def temp_db():
    """Create a temporary database with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize with schema
    import sys
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "pipeline"))
    from pipeline.db import init_db, run_migrations
    init_db(db_path)
    run_migrations(db_path)

    yield db_path
    try:
        Path(db_path).unlink()
    except PermissionError:
        pass


@pytest.fixture
def bot_server(temp_db):
    """Create a BotServer instance (without starting HTTP server)."""
    config = BotConfig(
        db_path=temp_db,
        bot_port=8473,
        discord_token="test_token",
        anthropic_api_key="test_key",
        gm_authors=["Test GM"],
    )
    return BotServer(config)


def test_progress_idle(bot_server):
    """Test progress retrieval when no pipeline is running."""
    result = bot_server._get_current_progress()
    assert result["status"] == "idle"


def test_progress_running(bot_server, temp_db):
    """Test progress retrieval when pipeline is running."""
    # Insert a running pipeline run with progress
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row

    # Create a civ
    cursor = conn.execute(
        "INSERT INTO civ_civilizations (name) VALUES ('Test Civ')"
    )
    civ_id = cursor.lastrowid

    # Create a running pipeline run
    cursor = conn.execute(
        "INSERT INTO pipeline_runs (status) VALUES ('running')"
    )
    run_id = cursor.lastrowid

    # Insert progress entries
    conn.execute(
        """INSERT INTO pipeline_progress
           (pipeline_run_id, phase, civ_id, civ_name, total_units, current_unit, unit_type, status)
           VALUES (?, 'pipeline', ?, 'Test Civ', 10, 5, 'turn', 'running')""",
        (run_id, civ_id),
    )

    conn.execute(
        """INSERT INTO pipeline_progress
           (pipeline_run_id, phase, civ_id, civ_name, total_units, current_unit, unit_type, status)
           VALUES (?, 'profiler', ?, 'Test Civ', 50, 20, 'entity', 'running')""",
        (run_id, civ_id),
    )

    conn.commit()
    conn.close()

    # Get progress
    result = bot_server._get_current_progress()

    assert result["status"] == "running"
    assert result["run_id"] == run_id
    assert "started_at" in result
    assert "phases" in result
    assert len(result["phases"]) == 2

    # Verify phase data (order may vary, so check both)
    phases_by_name = {p["phase"]: p for p in result["phases"]}

    assert "pipeline" in phases_by_name
    assert phases_by_name["pipeline"]["civ_name"] == "Test Civ"
    assert phases_by_name["pipeline"]["total_units"] == 10
    assert phases_by_name["pipeline"]["current_unit"] == 5
    assert phases_by_name["pipeline"]["unit_type"] == "turn"
    assert phases_by_name["pipeline"]["status"] == "running"

    assert "profiler" in phases_by_name
    assert phases_by_name["profiler"]["total_units"] == 50
    assert phases_by_name["profiler"]["current_unit"] == 20
    assert phases_by_name["profiler"]["unit_type"] == "entity"


def test_progress_completed_run_ignored(bot_server, temp_db):
    """Test that completed pipeline runs are not returned as running."""
    # Insert a completed pipeline run
    conn = sqlite3.connect(temp_db)

    cursor = conn.execute(
        "INSERT INTO pipeline_runs (status, completed_at) VALUES ('completed', datetime('now'))"
    )
    run_id = cursor.lastrowid

    # Insert progress for completed run
    conn.execute(
        """INSERT INTO pipeline_progress
           (pipeline_run_id, phase, total_units, current_unit, unit_type, status)
           VALUES (?, 'pipeline', 10, 10, 'turn', 'completed')""",
        (run_id,),
    )

    conn.commit()
    conn.close()

    # Get progress
    result = bot_server._get_current_progress()

    # Should return idle since no running pipeline
    assert result["status"] == "idle"


def test_progress_multiple_phases(bot_server, temp_db):
    """Test progress with all three phases."""
    conn = sqlite3.connect(temp_db)

    # Create a running pipeline run
    cursor = conn.execute(
        "INSERT INTO pipeline_runs (status) VALUES ('running')"
    )
    run_id = cursor.lastrowid

    # Simulate all three phases
    phases = [
        ("pipeline", 1, "Civ A", 5, 5, "turn", "completed"),
        ("profiler", 1, "Civ A", 30, 15, "entity", "running"),
        ("wiki", None, None, 20, 0, "page", "running"),
    ]

    for phase, civ_id, civ_name, total, current, unit, status in phases:
        conn.execute(
            """INSERT INTO pipeline_progress
               (pipeline_run_id, phase, civ_id, civ_name, total_units, current_unit, unit_type, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, phase, civ_id, civ_name, total, current, unit, status),
        )

    conn.commit()
    conn.close()

    # Get progress
    result = bot_server._get_current_progress()

    assert result["status"] == "running"
    assert len(result["phases"]) == 3

    phases_by_name = {p["phase"]: p for p in result["phases"]}

    # Verify pipeline phase completed
    assert phases_by_name["pipeline"]["status"] == "completed"
    assert phases_by_name["pipeline"]["current_unit"] == 5
    assert phases_by_name["pipeline"]["total_units"] == 5

    # Verify profiler phase running
    assert phases_by_name["profiler"]["status"] == "running"
    assert phases_by_name["profiler"]["current_unit"] == 15
    assert phases_by_name["profiler"]["total_units"] == 30

    # Verify wiki phase running
    assert phases_by_name["wiki"]["status"] == "running"
    assert phases_by_name["wiki"]["civ_id"] is None  # wiki is global
