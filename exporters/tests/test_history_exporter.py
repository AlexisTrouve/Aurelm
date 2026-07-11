"""Tests for the history exporter."""

from __future__ import annotations

import json
from pathlib import Path

from exporters.history_exporter import _split_event, export_history


def test_split_event_parses_leading_turn_number():
    assert _split_event("Tour 1: Oracle apparait.") == (1, "Oracle apparait.")
    assert _split_event("Chapitre 12 - un evenement") == (12, "un evenement")
    # no leading label+number -> whole string, no turn
    assert _split_event("Pas de prefixe ici") == (None, "Pas de prefixe ici")


def test_history_single_entity(sample_db, tmp_path):
    out = tmp_path / "hist"
    result = export_history(sample_db, str(out), entity="Oracle")
    assert result["count"] == "1"
    data = json.loads(Path(result["json"]).read_text(encoding="utf-8"))
    rec = data[0]
    assert rec["canonical_name"] == "Oracle"
    assert rec["first_seen_turn"] == 1        # resolved from turn id 10
    assert [e["turn"] for e in rec["events"]] == [1, 2]
    assert [m["turn_number"] for m in rec["mentions"]] == [1, 2]


def test_history_all_entities(sample_db, tmp_path):
    out = tmp_path / "hist"
    result = export_history(sample_db, str(out))
    assert result["count"] == "4"
    md = Path(result["md"]).read_text(encoding="utf-8")
    assert "云隐" in md                          # CJK entity present in md
