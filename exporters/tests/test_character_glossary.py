"""Tests for the character glossary exporter (persons + per-chapter history)."""

from __future__ import annotations

import json
from pathlib import Path

from exporters.character_glossary import export_character_glossary, _per_chapter
from exporters.db import get_connection, fetch_entity, fetch_mentions


def test_characters_only_persons(sample_db, tmp_path):
    out = tmp_path / "chars"
    result = export_character_glossary(sample_db, str(out))
    data = json.loads(Path(result["json"]).read_text(encoding="utf-8"))
    names = {r["canonical_name"] for r in data}
    assert "Rivière" not in names          # place excluded
    assert "Oracle" in names and "云隐" in names


def test_per_chapter_uses_summaries_then_mentions(sample_db):
    conn = get_connection(sample_db)
    oracle = fetch_entity(conn, 1)          # history: "Tour 1: ...", "Tour 2: ..."
    per = _per_chapter(oracle, fetch_mentions(conn, 1))
    chapters = [c["chapter"] for c in per]
    assert chapters == [1, 2]               # both chapters present, in order
    assert all(c["source"] == "summary" for c in per)  # rich summaries used


def test_markdown_has_per_chapter_section(sample_db, tmp_path):
    out = tmp_path / "chars"
    result = export_character_glossary(sample_db, str(out), title="Persos")
    md = Path(result["md"]).read_text(encoding="utf-8")
    assert "# Persos" in md
    assert "**Par chapitre :**" in md
    assert "**Chapitre 1**" in md
    assert "云隐" in md                      # CJK character rendered
