"""Tests for the glossary exporter."""

from __future__ import annotations

import json
from pathlib import Path

from exporters.glossary_exporter import export_glossary


def test_glossary_writes_md_and_json(sample_db, tmp_path):
    out = tmp_path / "gloss"
    result = export_glossary(sample_db, str(out), title="T")
    assert Path(result["md"]).is_file()
    assert Path(result["json"]).is_file()
    assert result["count"] == "4"


def test_glossary_json_preserves_cjk_and_aliases(sample_db, tmp_path):
    out = tmp_path / "gloss"
    result = export_glossary(sample_db, str(out))
    data = json.loads(Path(result["json"]).read_text(encoding="utf-8"))
    by_name = {r["canonical_name"]: r for r in data}
    assert "云隐" in by_name                       # CJK preserved in JSON
    assert by_name["Oracle"]["aliases"] == ["L'Immortel"]
    assert by_name["Rivière"]["is_active"] is False


def test_glossary_filter_by_type(sample_db, tmp_path):
    out = tmp_path / "gloss"
    result = export_glossary(sample_db, str(out), entity_type="place")
    assert result["count"] == "1"
    md = Path(result["md"]).read_text(encoding="utf-8")
    assert "Rivière" in md
    assert "Oracle" not in md
