"""Integration tests for the pipeline runner."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from pipeline.db import init_db, get_connection, register_civilization
from pipeline.loader import load_directory
from pipeline.runner import run_pipeline


CIVJDR_DIR = Path(__file__).resolve().parent.parent.parent.parent / "civjdr" / "Background"


class TestDBInit:
    """Test database initialization."""

    def test_init_creates_tables(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            init_db(db_path)
            conn = get_connection(db_path)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {row[0] for row in tables}
            assert "civ_civilizations" in table_names
            assert "turn_raw_messages" in table_names
            assert "turn_turns" in table_names
            assert "entity_entities" in table_names
            conn.close()
        finally:
            os.unlink(db_path)

    def test_register_civilization_idempotent(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            init_db(db_path)
            id1 = register_civilization(db_path, "Test Civ", player_name="Player1")
            id2 = register_civilization(db_path, "Test Civ", player_name="Player1")
            assert id1 == id2
        finally:
            os.unlink(db_path)


class TestLoaderIntegration:
    """Test loading real civjdr data."""

    @pytest.mark.skipif(
        not CIVJDR_DIR.is_dir(),
        reason="civjdr/Background directory not available"
    )
    def test_load_civjdr_files(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            init_db(db_path)
            count = load_directory(str(CIVJDR_DIR), db_path)
            assert count > 0, "Should load at least some messages"
            # We expect roughly 2 messages per file (GM + player) for ~19 files
            assert count >= 10, f"Expected at least 10 messages, got {count}"
        finally:
            os.unlink(db_path)


class TestFullPipeline:
    """Integration test: run the full pipeline on real data."""

    @pytest.mark.skipif(
        not CIVJDR_DIR.is_dir(),
        reason="civjdr/Background directory not available"
    )
    def test_pipeline_end_to_end_no_llm(self):
        """Run full pipeline without LLM on real civjdr data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            stats = run_pipeline(
                data_dir=str(CIVJDR_DIR),
                db_path=db_path,
                civ_name="Civilisation de la Confluence",
                player_name="Rubanc",
                use_llm=False,
            )

            # Check stats
            assert stats["messages_loaded"] > 0
            assert stats["turns_created"] > 0
            assert stats["segments_created"] > 0

            # Check DB contents
            conn = get_connection(db_path)

            # Check turns exist
            turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
            assert turn_count > 0, f"Expected turns, got {turn_count}"

            # Check segments exist
            seg_count = conn.execute("SELECT count(*) FROM turn_segments").fetchone()[0]
            assert seg_count > 0

            # Check entities exist (if spaCy available)
            entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
            # NER might not run if spaCy model isn't installed
            # So we just check it doesn't crash

            # Check pipeline run was recorded
            run = conn.execute(
                "SELECT status FROM pipeline_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert run[0] == "completed"

            # Check civilization was registered
            civ = conn.execute(
                "SELECT name FROM civ_civilizations WHERE name = ?",
                ("Civilisation de la Confluence",),
            ).fetchone()
            assert civ is not None

            conn.close()
        finally:
            os.unlink(db_path)

    @pytest.mark.skipif(
        not CIVJDR_DIR.is_dir(),
        reason="civjdr/Background directory not available"
    )
    def test_pipeline_creates_summaries(self):
        """Check that extractive summaries are created for turns."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            run_pipeline(
                data_dir=str(CIVJDR_DIR),
                db_path=db_path,
                civ_name="Civilisation de la Confluence",
                use_llm=False,
            )

            conn = get_connection(db_path)
            summaries = conn.execute(
                "SELECT summary FROM turn_turns WHERE summary IS NOT NULL"
            ).fetchall()
            assert len(summaries) > 0, "Should have at least one summary"
            # Check summaries are non-empty
            for row in summaries:
                assert row[0] and len(row[0]) > 0
            conn.close()
        finally:
            os.unlink(db_path)
