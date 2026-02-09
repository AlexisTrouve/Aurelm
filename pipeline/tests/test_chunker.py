"""Tests for turn boundary detection."""

from pipeline.chunker import detect_turn_boundaries
from pipeline.ingestion import RawMessage


def _msg(id: int, author_id: str, content: str) -> RawMessage:
    return RawMessage(
        id=id,
        discord_message_id=str(id),
        channel_id="chan1",
        author_id=author_id,
        author_name="test",
        content=content,
        timestamp=f"2025-01-01T{id:02d}:00:00",
    )


def test_empty_messages():
    assert detect_turn_boundaries([], "gm") == []


def test_single_message():
    msgs = [_msg(1, "gm", "Hello")]
    chunks = detect_turn_boundaries(msgs, "gm")
    assert len(chunks) == 1
    assert len(chunks[0].messages) == 1


def test_gm_after_player_starts_new_turn():
    msgs = [
        _msg(1, "gm", "Your turn"),
        _msg(2, "player1", "I choose A"),
        _msg(3, "gm", "Result of A"),
    ]
    chunks = detect_turn_boundaries(msgs, "gm")
    assert len(chunks) == 2
