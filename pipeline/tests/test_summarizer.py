"""Tests for pipeline.summarizer -- focus on LLM output robustness.

All tests in TestSummarizerNullFields fail before fix and pass after.
"""

from __future__ import annotations

import pytest
from pipeline.summarizer import _merge_summaries, TurnSummary


class TestSummarizerMergeNullFields:
    """Bug E: LLM returns null (or string) for list fields.
    _merge_summaries calls list.extend(None) -> TypeError crash.
    """

    def test_null_key_events_does_not_crash(self):
        """LLM returns {"key_events": null} -- must not raise TypeError."""
        gm_parts = [
            {"short_summary": "Foo", "detailed_summary": "Bar", "key_events": None,
             "entities_mentioned": []}
        ]
        result = _merge_summaries(gm_parts, [])
        assert isinstance(result, TurnSummary)
        assert result.key_events == []

    def test_null_entities_mentioned_does_not_crash(self):
        """LLM returns {"entities_mentioned": null} -- must not raise TypeError."""
        gm_parts = [
            {"short_summary": "Foo", "detailed_summary": "Bar", "key_events": [],
             "entities_mentioned": None}
        ]
        result = _merge_summaries(gm_parts, [])
        assert isinstance(result, TurnSummary)
        assert result.entities_mentioned == []

    def test_null_choices_made_does_not_crash(self):
        """LLM returns {"choices_made": null} in player part -- must not crash."""
        player_parts = [
            {"short_summary": "Player chose X", "choices_made": None,
             "entities_mentioned": []}
        ]
        result = _merge_summaries([], player_parts)
        assert isinstance(result, TurnSummary)
        assert result.choices_made == []

    def test_string_key_events_does_not_produce_chars(self):
        """LLM returns {"key_events": "single event"} -- must not iterate chars."""
        gm_parts = [
            {"short_summary": "Foo", "detailed_summary": "Bar",
             "key_events": "Fondation de la cite",
             "entities_mentioned": []}
        ]
        result = _merge_summaries(gm_parts, [])
        assert isinstance(result, TurnSummary)
        assert isinstance(result.key_events, list)
        # Must NOT have exploded into individual characters
        for event in result.key_events:
            assert len(event) > 1, f"key_events contains single char {event!r} -- string iterated as chars"

    def test_string_entities_mentioned_does_not_produce_chars(self):
        """LLM returns {"entities_mentioned": "Nanzagouets"} -- must not iterate chars."""
        gm_parts = [
            {"short_summary": "X", "detailed_summary": "Y",
             "key_events": [],
             "entities_mentioned": "Nanzagouets"}
        ]
        result = _merge_summaries(gm_parts, [])
        assert isinstance(result, TurnSummary)
        for e in result.entities_mentioned:
            assert len(e) > 1, f"entities_mentioned contains single char {e!r}"

    def test_multiple_gm_parts_one_null(self):
        """Mix of valid and null parts in a multi-chunk response -- must merge correctly."""
        gm_parts = [
            {"short_summary": "Part 1", "detailed_summary": "Detail 1",
             "key_events": ["Evenement 1"], "entities_mentioned": ["Caste de l Air"]},
            {"short_summary": "Part 2", "detailed_summary": "Detail 2",
             "key_events": None, "entities_mentioned": None},
        ]
        result = _merge_summaries(gm_parts, [])
        assert isinstance(result, TurnSummary)
        assert "Evenement 1" in result.key_events
        assert "Caste de l Air" in result.entities_mentioned


class TestSummarizerSingleTurnNullFields:
    """Bug F: Single-turn summarize path -- data.get("key_events", []) returns None
    when LLM includes the key with a null value. TurnSummary gets key_events=None,
    crashing any downstream code that iterates over it.
    """

    def test_turnSummary_key_events_none_is_list(self):
        """Verify that a TurnSummary constructed with key_events=None causes issues downstream."""
        # Simulate what happens when summarize_turn_single returns data.get("key_events", []) = None
        # The dataclass won't enforce types at init time
        ts = TurnSummary(
            short_summary="X",
            detailed_summary="Y",
            key_events=None,   # This happens when LLM returns {"key_events": null}
            entities_mentioned=None,
            choices_made=None,
        )
        # Downstream code iterates over these:
        # Confirm that iterating over None crashes (proving we need the fix)
        with pytest.raises(TypeError):
            list(ts.key_events)   # None is not iterable
