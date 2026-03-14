"""Tests for turn preanalysis — novelty detection + player strategy.

Unit tests (no LLM):
1. test_novelty_detection — entities new vs existing
2. test_novelty_empty_turn — turn with no new entities
3. test_player_strategy_skip_no_pj — no PJ segments = skip
"""

import json
import sqlite3
import pytest

from pipeline.turn_preanalysis import (
    analyze_novelty,
    analyze_player_strategy,
    _parse_strategy_response,
    STRATEGY_TAGS,
)


# -- Fixtures --

def _init_test_db() -> sqlite3.Connection:
    """Create an in-memory test DB with required tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE civ_civilizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            player_name TEXT,
            discord_channel_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE turn_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
            turn_number INTEGER NOT NULL,
            title TEXT,
            summary TEXT,
            detailed_summary TEXT,
            key_events TEXT,
            choices_made TEXT,
            raw_message_ids TEXT NOT NULL DEFAULT '[]',
            turn_type TEXT NOT NULL DEFAULT 'standard',
            game_date_start TEXT,
            game_date_end TEXT,
            media_links TEXT,
            technologies TEXT,
            resources TEXT,
            beliefs TEXT,
            geography TEXT,
            choices_proposed TEXT,
            novelty_summary TEXT,
            new_entity_ids TEXT,
            player_strategy TEXT,
            strategy_tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            processed_at TEXT,
            UNIQUE(civ_id, turn_number)
        );

        CREATE TABLE turn_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
            segment_order INTEGER NOT NULL,
            segment_type TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'gm'
        );

        CREATE TABLE entity_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            civ_id INTEGER REFERENCES civ_civilizations(id),
            description TEXT,
            history TEXT,
            first_seen_turn INTEGER REFERENCES turn_turns(id),
            last_seen_turn INTEGER REFERENCES turn_turns(id),
            is_active INTEGER NOT NULL DEFAULT 1,
            disabled INTEGER NOT NULL DEFAULT 0,
            hidden INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE subject_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
            source_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
            direction TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


def _seed_civ_and_turns(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """Create a civ with 2 turns. Returns (civ_id, turn1_id, turn2_id)."""
    conn.execute("INSERT INTO civ_civilizations (name) VALUES ('TestCiv')")
    civ_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number) VALUES (?, 1)", (civ_id,)
    )
    t1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute(
        "INSERT INTO turn_turns (civ_id, turn_number) VALUES (?, 2)", (civ_id,)
    )
    t2_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.commit()
    return civ_id, t1_id, t2_id


# -- Tests --

class TestNoveltyDetection:
    """Tests for analyze_novelty — pure SQL, no LLM."""

    def test_novelty_detection(self):
        """Entities first seen this turn are detected and grouped by type."""
        conn = _init_test_db()
        civ_id, t1_id, t2_id = _seed_civ_and_turns(conn)

        # Insert entities: 2 first seen at T1, 1 first seen at T2
        conn.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn) VALUES (?, ?, ?, ?)",
            ("Argile Vivante", "technology", civ_id, t1_id),
        )
        conn.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn) VALUES (?, ?, ?, ?)",
            ("Cercle des Sages", "institution", civ_id, t1_id),
        )
        conn.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn) VALUES (?, ?, ?, ?)",
            ("Fleuve Mere", "place", civ_id, t2_id),
        )
        conn.commit()

        # Analyze T1 — should find 2 new entities
        result = analyze_novelty(conn, t1_id, civ_id)
        assert len(result["new_entity_ids"]) == 2
        assert "2 nouvelle(s) entite(s)" in result["novelty_summary"]
        assert "Argile Vivante" in result["novelty_summary"]
        assert "Cercle des Sages" in result["novelty_summary"]

        # Verify DB was updated
        row = conn.execute(
            "SELECT novelty_summary, new_entity_ids FROM turn_turns WHERE id = ?",
            (t1_id,),
        ).fetchone()
        assert json.loads(row["new_entity_ids"]) == result["new_entity_ids"]

        # Analyze T2 — should find 1 new entity
        result2 = analyze_novelty(conn, t2_id, civ_id)
        assert len(result2["new_entity_ids"]) == 1
        assert "Fleuve Mere" in result2["novelty_summary"]

        conn.close()

    def test_novelty_empty_turn(self):
        """Turn with no new entities gets empty summary."""
        conn = _init_test_db()
        civ_id, t1_id, t2_id = _seed_civ_and_turns(conn)

        # No entities at all — T1 should have empty novelty
        result = analyze_novelty(conn, t1_id, civ_id)
        assert result["new_entity_ids"] == []
        assert result["novelty_summary"] == ""

        # Verify DB
        row = conn.execute(
            "SELECT novelty_summary, new_entity_ids FROM turn_turns WHERE id = ?",
            (t1_id,),
        ).fetchone()
        assert row["new_entity_ids"] == "[]"
        assert row["novelty_summary"] == ""

        conn.close()

    def test_novelty_ignores_disabled_entities(self):
        """Disabled entities are not counted in novelty."""
        conn = _init_test_db()
        civ_id, t1_id, t2_id = _seed_civ_and_turns(conn)

        # Active entity
        conn.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn, disabled) VALUES (?, ?, ?, ?, 0)",
            ("Active Ent", "person", civ_id, t1_id),
        )
        # Disabled entity — should be excluded
        conn.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn, disabled) VALUES (?, ?, ?, ?, 1)",
            ("Disabled Ent", "person", civ_id, t1_id),
        )
        conn.commit()

        result = analyze_novelty(conn, t1_id, civ_id)
        assert len(result["new_entity_ids"]) == 1
        assert "Active Ent" in result["novelty_summary"]
        assert "Disabled Ent" not in result["novelty_summary"]

        conn.close()


class TestPlayerStrategySkip:
    """Tests for analyze_player_strategy when no PJ text exists."""

    def test_player_strategy_skip_no_pj(self):
        """No PJ segments for the turn => returns None, no DB update."""
        conn = _init_test_db()
        civ_id, t1_id, _ = _seed_civ_and_turns(conn)

        # Only GM segments, no PJ
        conn.execute(
            "INSERT INTO turn_segments (turn_id, segment_order, segment_type, content, source) "
            "VALUES (?, 1, 'narrative', 'GM text here', 'gm')",
            (t1_id,),
        )
        conn.commit()

        # Should return None (skip) without calling LLM
        result = analyze_player_strategy(conn, t1_id, civ_id, None, "fake-model")
        assert result is None

        # DB columns should remain NULL
        row = conn.execute(
            "SELECT player_strategy, strategy_tags FROM turn_turns WHERE id = ?",
            (t1_id,),
        ).fetchone()
        assert row["player_strategy"] is None
        assert row["strategy_tags"] is None

        conn.close()


class TestParseStrategyResponse:
    """Tests for _parse_strategy_response JSON parsing."""

    def test_valid_json(self):
        """Clean JSON response is parsed correctly."""
        response = '{"strategy": "Le joueur explore le nord.", "tags": ["exploration"]}'
        strategy, tags = _parse_strategy_response(response)
        assert strategy == "Le joueur explore le nord."
        assert tags == ["exploration"]

    def test_json_in_markdown_fence(self):
        """JSON wrapped in ```json ... ``` is extracted."""
        response = '```json\n{"strategy": "Defense priority", "tags": ["defense", "militaire"]}\n```'
        strategy, tags = _parse_strategy_response(response)
        assert strategy == "Defense priority"
        assert set(tags) == {"defense", "militaire"}

    def test_invalid_tags_filtered(self):
        """Tags not in STRATEGY_TAGS are filtered out."""
        response = '{"strategy": "test", "tags": ["exploration", "invalid_tag", "culture"]}'
        strategy, tags = _parse_strategy_response(response)
        assert tags == ["exploration", "culture"]

    def test_garbage_response(self):
        """Non-JSON response returns truncated text + empty tags."""
        response = "I cannot process this request"
        strategy, tags = _parse_strategy_response(response)
        assert strategy == "I cannot process this request"
        assert tags == []
