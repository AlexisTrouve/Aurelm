"""Tests for subject extraction and tracking.

Unit tests (no LLM):
1. test_schema_migration -- tables created correctly
2. test_insert_subject_idempotent -- UNIQUE constraint
3. test_subject_lifecycle -- open -> resolved via apply_resolutions
4. test_load_open_subjects -- filters status='open', loads options
5. test_resolution_confidence_threshold -- confidence < 0.4 ignored
6. test_build_turn_pairs -- mapping all_chunks -> (gm_text, pj_text)

Integration tests (marked @pytest.mark.integration, require LLM):
7. test_extract_mj_subjects_real -- T14 MJ text
8. test_extract_pj_initiatives_real -- T11 PJ text
"""

import sqlite3
import pytest

from pipeline.subject_helpers import (
    load_open_subjects,
    insert_subject,
    apply_resolutions,
    get_subject_stats,
)
from pipeline.subject_extractor import build_turn_pairs
from pipeline.ingestion import RawMessage
from pipeline.chunker import TurnChunk


# -- Fixtures --

def _init_test_db() -> sqlite3.Connection:
    """Create an in-memory test DB with all required tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    # Minimal schema: civilizations + turns + subject tables
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
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            processed_at TEXT,
            UNIQUE(civ_id, turn_number)
        );

        CREATE TABLE subject_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
            source_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
            direction TEXT NOT NULL CHECK (direction IN ('mj_to_pj', 'pj_to_mj')),
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL CHECK (category IN ('choice', 'question', 'initiative', 'request')),
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'superseded', 'abandoned')),
            source_quote TEXT,
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(civ_id, source_turn_id, title)
        );

        CREATE TABLE subject_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
            option_number INTEGER NOT NULL,
            label TEXT NOT NULL,
            description TEXT,
            is_libre INTEGER NOT NULL DEFAULT 0,
            UNIQUE(subject_id, option_number)
        );

        CREATE TABLE subject_resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
            resolved_by_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
            chosen_option_id INTEGER REFERENCES subject_options(id),
            resolution_text TEXT NOT NULL,
            source_quote TEXT,
            is_libre INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # Seed data: 1 civ, 3 turns
    conn.execute("INSERT INTO civ_civilizations (name) VALUES ('TestCiv')")
    conn.execute("INSERT INTO turn_turns (civ_id, turn_number) VALUES (1, 1)")
    conn.execute("INSERT INTO turn_turns (civ_id, turn_number) VALUES (1, 2)")
    conn.execute("INSERT INTO turn_turns (civ_id, turn_number) VALUES (1, 3)")
    conn.commit()

    return conn


def _msg(id: int, author_id: str, content: str, author_name: str = "test") -> RawMessage:
    """Helper to create a RawMessage for test purposes."""
    return RawMessage(
        id=id,
        discord_message_id=str(id),
        channel_id="chan1",
        author_id=author_id,
        author_name=author_name,
        content=content,
        timestamp=f"2025-01-01T{id:02d}:00:00",
    )


# -- Unit Tests --

def test_schema_migration():
    """Tables are created correctly with all columns."""
    conn = _init_test_db()

    # Verify tables exist and have correct columns
    cols_subjects = {
        row[1]
        for row in conn.execute("PRAGMA table_info(subject_subjects)").fetchall()
    }
    assert "id" in cols_subjects
    assert "civ_id" in cols_subjects
    assert "direction" in cols_subjects
    assert "category" in cols_subjects
    assert "status" in cols_subjects

    cols_options = {
        row[1]
        for row in conn.execute("PRAGMA table_info(subject_options)").fetchall()
    }
    assert "subject_id" in cols_options
    assert "option_number" in cols_options
    assert "is_libre" in cols_options

    cols_resolutions = {
        row[1]
        for row in conn.execute("PRAGMA table_info(subject_resolutions)").fetchall()
    }
    assert "subject_id" in cols_resolutions
    assert "resolved_by_turn_id" in cols_resolutions
    assert "confidence" in cols_resolutions

    conn.close()


def test_insert_subject_idempotent():
    """INSERT OR IGNORE prevents duplicates, returns existing ID."""
    conn = _init_test_db()

    subject = {
        "direction": "mj_to_pj",
        "title": "Choix diplomatique",
        "description": "Test",
        "category": "choice",
        "options": [
            {"number": 1, "label": "Alliance", "description": "S'allier", "is_libre": False},
            {"number": 2, "label": "Guerre", "description": "Attaquer", "is_libre": False},
        ],
    }

    # First insert
    id1 = insert_subject(conn, subject, civ_id=1, turn_id=1)
    conn.commit()
    assert id1 is not None

    # Second insert (same civ, turn, title) -> returns existing ID
    id2 = insert_subject(conn, subject, civ_id=1, turn_id=1)
    assert id2 == id1

    # Verify only 1 row exists
    count = conn.execute("SELECT COUNT(*) FROM subject_subjects").fetchone()[0]
    assert count == 1

    # Verify options were inserted
    opt_count = conn.execute("SELECT COUNT(*) FROM subject_options").fetchone()[0]
    assert opt_count == 2

    conn.close()


def test_subject_lifecycle():
    """Subject goes from open -> resolved via apply_resolutions."""
    conn = _init_test_db()

    # Insert an open subject
    subject = {
        "direction": "mj_to_pj",
        "title": "Expedition nord",
        "description": "Explorer le nord",
        "category": "choice",
        "options": [
            {"number": 1, "label": "Envoyer des eclaireurs", "is_libre": False},
            {"number": 2, "label": "Aller en force", "is_libre": False},
        ],
    }
    subject_id = insert_subject(conn, subject, civ_id=1, turn_id=1)
    conn.commit()

    # Verify it's open
    stats = get_subject_stats(conn, civ_id=1)
    assert stats["open"] == 1
    assert stats["resolved"] == 0

    # Resolve it
    resolutions = [
        {
            "subject_id": subject_id,
            "resolution_text": "Le joueur envoie des eclaireurs",
            "chosen_option_label": "Envoyer des eclaireurs",
            "confidence": 0.9,
        }
    ]
    applied = apply_resolutions(conn, resolutions, turn_id=2)
    conn.commit()
    assert applied == 1

    # Verify it's resolved
    stats = get_subject_stats(conn, civ_id=1)
    assert stats["open"] == 0
    assert stats["resolved"] == 1

    # Verify resolution record exists
    res_row = conn.execute(
        "SELECT * FROM subject_resolutions WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    assert res_row is not None
    assert res_row["resolution_text"] == "Le joueur envoie des eclaireurs"
    assert res_row["confidence"] == 0.9

    conn.close()


def test_load_open_subjects():
    """load_open_subjects returns only open subjects with their options."""
    conn = _init_test_db()

    # Insert 2 subjects: 1 open, 1 resolved
    open_subj = {
        "direction": "mj_to_pj",
        "title": "Ouvert",
        "description": "Sujet ouvert",
        "category": "choice",
        "options": [
            {"number": 1, "label": "A"},
            {"number": 2, "label": "B"},
        ],
    }
    resolved_subj = {
        "direction": "pj_to_mj",
        "title": "Ferme",
        "description": "Sujet resolu",
        "category": "initiative",
        "options": [],
    }

    insert_subject(conn, open_subj, civ_id=1, turn_id=1)
    resolved_id = insert_subject(conn, resolved_subj, civ_id=1, turn_id=1)
    conn.commit()

    # Manually resolve the second one
    conn.execute(
        "UPDATE subject_subjects SET status = 'resolved' WHERE id = ?",
        (resolved_id,),
    )
    conn.commit()

    # Load open subjects
    subjects = load_open_subjects(conn, civ_id=1)
    assert len(subjects) == 1
    assert subjects[0]["title"] == "Ouvert"
    assert len(subjects[0]["options"]) == 2
    assert subjects[0]["options"][0]["label"] == "A"

    conn.close()


def test_resolution_confidence_threshold():
    """Resolutions with confidence below threshold (0.7) are ignored."""
    conn = _init_test_db()

    subject = {
        "direction": "mj_to_pj",
        "title": "Test confiance",
        "description": "Seuil de confiance",
        "category": "choice",
        "options": [],
    }
    subject_id = insert_subject(conn, subject, civ_id=1, turn_id=1)
    conn.commit()

    # Try resolving with low confidence
    resolutions = [
        {
            "subject_id": subject_id,
            "resolution_text": "Reponse vague",
            "confidence": 0.5,  # Below default threshold of 0.7
        }
    ]
    applied = apply_resolutions(conn, resolutions, turn_id=2)
    conn.commit()
    assert applied == 0

    # Subject should still be open
    stats = get_subject_stats(conn, civ_id=1)
    assert stats["open"] == 1
    assert stats["resolved"] == 0

    # Now resolve with sufficient confidence (above 0.7 threshold)
    resolutions[0]["confidence"] = 0.8
    applied = apply_resolutions(conn, resolutions, turn_id=2)
    conn.commit()
    assert applied == 1

    stats = get_subject_stats(conn, civ_id=1)
    assert stats["resolved"] == 1

    conn.close()


def test_build_turn_pairs():
    """build_turn_pairs maps all_chunks -> {turn_number: {gm_text, pj_text}}."""
    gm_id = "gm"

    # Simulate: GM1 -> PJ1 -> GM2 -> PJ2
    chunks = [
        TurnChunk(
            messages=[_msg(1, gm_id, "GM turn 1 text", "Arthur Ignatus")],
            turn_type="standard",
            is_gm_post=True,
        ),
        TurnChunk(
            messages=[_msg(2, "player", "PJ response 1", "Rubanc")],
            turn_type="standard",
            is_gm_post=False,
        ),
        TurnChunk(
            messages=[_msg(3, gm_id, "GM turn 2 text", "Arthur Ignatus")],
            turn_type="standard",
            is_gm_post=True,
        ),
        TurnChunk(
            messages=[_msg(4, "player", "PJ response 2", "Rubanc")],
            turn_type="standard",
            is_gm_post=False,
        ),
    ]

    pairs = build_turn_pairs(chunks, gm_id)

    assert len(pairs) == 2

    assert pairs[1]["gm_text"] == "GM turn 1 text"
    assert pairs[1]["pj_text"] == "PJ response 1"

    assert pairs[2]["gm_text"] == "GM turn 2 text"
    assert pairs[2]["pj_text"] == "PJ response 2"


def test_build_turn_pairs_no_pj():
    """GM turn without PJ response gets empty pj_text."""
    gm_id = "gm"

    chunks = [
        TurnChunk(
            messages=[_msg(1, gm_id, "GM only turn", "Arthur")],
            turn_type="standard",
            is_gm_post=True,
        ),
    ]

    pairs = build_turn_pairs(chunks, gm_id)
    assert len(pairs) == 1
    assert pairs[1]["gm_text"] == "GM only turn"
    assert pairs[1]["pj_text"] == ""


def test_get_subject_stats():
    """get_subject_stats returns correct counts by status."""
    conn = _init_test_db()

    # Insert 3 subjects with different statuses
    for i, title in enumerate(["A", "B", "C"]):
        insert_subject(conn, {
            "direction": "mj_to_pj",
            "title": title,
            "description": "",
            "category": "choice",
            "options": [],
        }, civ_id=1, turn_id=1)
    conn.commit()

    # Manually set statuses
    conn.execute("UPDATE subject_subjects SET status = 'resolved' WHERE title = 'B'")
    conn.execute("UPDATE subject_subjects SET status = 'abandoned' WHERE title = 'C'")
    conn.commit()

    stats = get_subject_stats(conn, civ_id=1)
    assert stats["open"] == 1
    assert stats["resolved"] == 1
    assert stats["abandoned"] == 1
    assert stats["total"] == 3

    conn.close()


# -- Integration Tests (require LLM) --

@pytest.mark.integration
def test_extract_mj_subjects_real():
    """Extract MJ subjects from real Turn 14 text (requires Ollama + qwen3:14b)."""
    from pipeline.subject_extractor import SubjectExtractor
    from pipeline.llm_provider import OllamaProvider

    # Read T14 MJ text (known to have 2 structured choices)
    from pathlib import Path
    civjdr_dir = Path(__file__).parent.parent.parent.parent / "civjdr" / "Background"
    t14_files = sorted(civjdr_dir.glob("*mj-T14*"))
    if not t14_files:
        pytest.skip("civjdr/Background/*mj-T14* not found")

    mj_text = t14_files[0].read_text(encoding="utf-8")

    provider = OllamaProvider()
    extractor = SubjectExtractor(provider=provider, model="qwen3:14b")
    subjects = extractor.extract_mj_subjects(mj_text, turn_number=14)

    # T14 should have at least 1 choice subject
    assert len(subjects) >= 1
    assert all(s.direction == "mj_to_pj" for s in subjects)
    # At least one should be a choice with options
    choice_subjects = [s for s in subjects if s.category == "choice"]
    assert len(choice_subjects) >= 1
    assert len(choice_subjects[0].options) >= 2

    print(f"  Extracted {len(subjects)} MJ subjects from T14:")
    for s in subjects:
        print(f"    - [{s.category}] {s.title} ({len(s.options)} options)")


@pytest.mark.integration
def test_extract_pj_initiatives_real():
    """Extract PJ initiatives from real Turn 11 PJ text (requires Ollama + qwen3:14b)."""
    from pipeline.subject_extractor import SubjectExtractor
    from pipeline.llm_provider import OllamaProvider

    from pathlib import Path
    civjdr_dir = Path(__file__).parent.parent.parent.parent / "civjdr" / "Background"
    t11_files = sorted(civjdr_dir.glob("*pj-T11*"))
    if not t11_files:
        pytest.skip("civjdr/Background/*pj-T11* not found")

    pj_text = t11_files[0].read_text(encoding="utf-8")

    provider = OllamaProvider()
    extractor = SubjectExtractor(provider=provider, model="qwen3:14b")
    initiatives = extractor.extract_pj_subjects(pj_text, turn_number=11)

    # PJ should have at least 1 initiative
    assert len(initiatives) >= 1
    assert all(s.direction == "pj_to_mj" for s in initiatives)

    print(f"  Extracted {len(initiatives)} PJ initiatives from T11:")
    for s in initiatives:
        print(f"    - [{s.category}] {s.title}")
