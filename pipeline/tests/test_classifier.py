"""Tests for message type classification."""

from pipeline.classifier import SegmentType, classify_segments


def test_choice_detection():
    text = "Que fais-tu face à cette menace ?\n1. Attaquer\n2. Fuir\n3. Négocier"
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.CHOICE


def test_ooc_detection():
    text = "(Note du MJ : on reprend la semaine prochaine)"
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.OOC


def test_narrative_default():
    text = "Le soleil se lève sur la vallée. Les premiers rayons illuminent la confluence des deux rivières."
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.NARRATIVE
