"""Tests for the generic document/chapter loader (P3-A)."""

from __future__ import annotations

import sqlite3

import pytest

from pipeline.db import init_db, get_connection
from pipeline.document_loader import (
    _chapter_number,
    _is_translation,
    load_documents,
)


# --- unit helpers -----------------------------------------------------------

def test_chapter_number_parsing():
    from pathlib import Path
    assert _chapter_number("CHAP_T05", 999) == 5
    assert _chapter_number("CHAP_T10", 999) == 10
    assert _chapter_number("prologue", 7) == 7          # no number -> fallback


def test_is_translation_detection():
    from pathlib import Path
    assert _is_translation(Path("CHAP_T06.zh.md")) is True
    assert _is_translation(Path("CHAP_T06.en.md")) is True
    assert _is_translation(Path("CHAP_T06.md")) is False


# --- loading ----------------------------------------------------------------

def _make_corpus(tmp_path):
    """Create a tiny chapter corpus + an initialized Aurelm DB. Returns (dir, db)."""
    chapters = tmp_path / "chapitres"
    chapters.mkdir()
    (chapters / "CHAP_T05.md").write_text("# Cinq\nContenu du chapitre cinq.", encoding="utf-8")
    (chapters / "CHAP_T10.md").write_text("# Dix\nContenu du chapitre dix.", encoding="utf-8")
    (chapters / "CHAP_T06.zh.md").write_text("# 六\n第六章的内容。", encoding="utf-8")  # translation
    db = tmp_path / "novel.db"
    init_db(str(db))
    return str(chapters), str(db)


def test_load_excludes_translations_by_default(tmp_path):
    data_dir, db = _make_corpus(tmp_path)
    inserted = load_documents(data_dir, db)
    assert inserted == 2                                # T05 + T10, .zh excluded
    conn = get_connection(db)
    narrators = conn.execute(
        "SELECT COUNT(*) c FROM turn_raw_messages WHERE author_name='Narrator'"
    ).fetchone()["c"]
    assert narrators == 2


def test_load_includes_translations_when_asked(tmp_path):
    data_dir, db = _make_corpus(tmp_path)
    inserted = load_documents(data_dir, db, include_translations=True)
    assert inserted == 3


def test_each_chapter_gets_a_player_placeholder(tmp_path):
    data_dir, db = _make_corpus(tmp_path)
    load_documents(data_dir, db)
    conn = get_connection(db)
    placeholders = conn.execute(
        "SELECT COUNT(*) c FROM turn_raw_messages WHERE author_name='__player__'"
    ).fetchone()["c"]
    assert placeholders == 2                            # one boundary per chapter


def test_chapters_ordered_numerically_by_timestamp(tmp_path):
    # T5 must precede T10 in timestamp order (not lexical, where "T10" < "T5").
    data_dir, db = _make_corpus(tmp_path)
    load_documents(data_dir, db)
    conn = get_connection(db)
    rows = conn.execute(
        "SELECT content, timestamp FROM turn_raw_messages "
        "WHERE author_name='Narrator' ORDER BY timestamp ASC"
    ).fetchall()
    assert rows[0]["content"].startswith("# Cinq")
    assert rows[1]["content"].startswith("# Dix")


def test_placeholder_precedes_its_chapter(tmp_path):
    # For each chapter, the __player__ placeholder timestamp is strictly earlier.
    data_dir, db = _make_corpus(tmp_path)
    load_documents(data_dir, db)
    conn = get_connection(db)
    rows = conn.execute(
        "SELECT author_name, timestamp FROM turn_raw_messages ORDER BY timestamp ASC"
    ).fetchall()
    # sequence must alternate placeholder, narrator, placeholder, narrator...
    assert [r["author_name"] for r in rows] == [
        "__player__", "Narrator", "__player__", "Narrator",
    ]


def test_channel_scope_is_documents(tmp_path):
    data_dir, db = _make_corpus(tmp_path)
    load_documents(data_dir, db)
    conn = get_connection(db)
    channels = {r["discord_channel_id"] for r in conn.execute(
        "SELECT DISTINCT discord_channel_id FROM turn_raw_messages")}
    assert channels == {"documents"}


def test_empty_file_skipped(tmp_path):
    chapters = tmp_path / "ch"; chapters.mkdir()
    (chapters / "CHAP_T01.md").write_text("Réel.", encoding="utf-8")
    (chapters / "CHAP_T02.md").write_text("   \n  ", encoding="utf-8")  # whitespace only
    db = tmp_path / "n.db"; init_db(str(db))
    inserted = load_documents(str(chapters), str(db))
    assert inserted == 1


def test_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_documents(str(tmp_path / "nope"), str(tmp_path / "x.db"))


# --- incremental, chapter-by-chapter (never full) ---------------------------

def _one_chapter_dir(tmp_path, name: str, num: str, body: str):
    d = tmp_path / name
    d.mkdir()
    (d / f"CHAP_T{num}.md").write_text(f"# Chap {num}\n{body}", encoding="utf-8")
    return str(d)


def test_incremental_chapters_compose_without_collision(tmp_path):
    # Load T05 alone, then T10 alone, into the SAME db (one chapter at a time).
    db = str(tmp_path / "novel.db"); init_db(db)
    dA = _one_chapter_dir(tmp_path, "a", "05", "Contenu cinq.")
    dB = _one_chapter_dir(tmp_path, "b", "10", "Contenu dix.")

    assert load_documents(dA, db) == 1
    assert load_documents(dB, db) == 1     # no id/timestamp collision with T05

    conn = get_connection(db)
    # two distinct placeholders keyed on chapter number (T0005, T0010)
    ph = sorted(r["discord_message_id"] for r in conn.execute(
        "SELECT discord_message_id FROM turn_raw_messages WHERE author_name='__player__'"))
    assert ph == ["synth-player-doc-T0005", "synth-player-doc-T0010"]
    # narrators in chapter order by timestamp (T05 before T10)
    narr = [r["content"][:8] for r in conn.execute(
        "SELECT content FROM turn_raw_messages WHERE author_name='Narrator' ORDER BY timestamp")]
    assert narr == ["# Chap 0", "# Chap 1"]   # "# Chap 05" then "# Chap 10"


def test_reloading_same_chapter_is_idempotent(tmp_path):
    db = str(tmp_path / "novel.db"); init_db(db)
    dA = _one_chapter_dir(tmp_path, "a", "05", "Contenu cinq.")
    assert load_documents(dA, db) == 1
    assert load_documents(dA, db) == 0     # same chapter again -> nothing new
