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
    # GM then player then GM → 3 separate chunks (each author switch = boundary)
    msgs = [
        _msg(1, "gm", "Your turn"),
        _msg(2, "player1", "I choose A"),
        _msg(3, "gm", "Result of A"),
    ]
    chunks = detect_turn_boundaries(msgs, "gm")
    assert len(chunks) == 3
    assert chunks[0].messages == [msgs[0]]
    assert chunks[0].is_gm_post is True
    assert chunks[1].messages == [msgs[1]]
    assert chunks[1].is_gm_post is False
    assert chunks[2].messages == [msgs[2]]
    assert chunks[2].is_gm_post is True


def test_player_after_gm_starts_new_chunk():
    # Player response must be in its own chunk, not appended to the GM chunk
    msgs = [
        _msg(1, "gm", "GM narrative"),
        _msg(2, "player1", "Player response"),
    ]
    chunks = detect_turn_boundaries(msgs, "gm")
    assert len(chunks) == 2
    assert chunks[0].is_gm_post is True
    assert chunks[1].is_gm_post is False
    assert chunks[1].messages[0].content == "Player response"


def test_new_layout_sequence():
    # Simulates the new-layout loader output:
    # [__player__ placeholder] [MJ content] [PJ response] [__player__] [MJ] [PJ] ...
    # Each source (MJ/PJ) should land in its own chunk.
    synth = "00000000"  # _SYNTHETIC_PLAYER_ID
    gm = "aabbccdd"
    player = "11223344"

    msgs = [
        _msg(1, synth, "[Tour 1]"),       # synthetic placeholder
        _msg(2, gm, "MJ turn 1"),         # GM content
        _msg(3, player, "PJ response 1"), # player response
        _msg(4, synth, "[Tour 2]"),       # next placeholder
        _msg(5, gm, "MJ turn 2"),         # GM content
        _msg(6, player, "PJ response 2"), # player response
    ]
    chunks = detect_turn_boundaries(msgs, gm)

    # Expected chunks:
    #   [synth T1]                  is_gm=False
    #   [gm T1]                     is_gm=True   ← boundary: gm after synth
    #   [player T1, synth T2]       is_gm=False  ← boundary: player after gm
    #                                               (synth T2 appended: non-gm after non-gm = no boundary)
    #   [gm T2]                     is_gm=True   ← boundary: gm after synth
    #   [player T2]                 is_gm=False  ← boundary: player after gm
    assert len(chunks) == 5

    # GM chunks are isolated — contain only GM messages
    gm_chunks = [c for c in chunks if c.is_gm_post]
    assert len(gm_chunks) == 2
    assert all(m.author_id == gm for c in gm_chunks for m in c.messages)

    # Non-GM chunks contain no GM messages
    non_gm_chunks = [c for c in chunks if not c.is_gm_post]
    assert len(non_gm_chunks) == 3
    assert all(m.author_id != gm for c in non_gm_chunks for m in c.messages)


def test_multiple_gm_messages_stay_together():
    # Multiple consecutive GM messages belong to the same chunk
    msgs = [
        _msg(1, "player1", "Player action"),
        _msg(2, "gm", "GM part 1"),
        _msg(3, "gm", "GM part 2"),
        _msg(4, "player1", "Player response"),
    ]
    chunks = detect_turn_boundaries(msgs, "gm")
    # player | [gm, gm] | player
    assert len(chunks) == 3
    assert len(chunks[1].messages) == 2  # both GM messages in one chunk
    assert chunks[1].is_gm_post is True


def test_multiple_player_messages_stay_together():
    # Multiple consecutive player messages belong to the same chunk
    msgs = [
        _msg(1, "gm", "GM narrative"),
        _msg(2, "player1", "Player part 1"),
        _msg(3, "player1", "Player part 2"),
        _msg(4, "gm", "GM next turn"),
    ]
    chunks = detect_turn_boundaries(msgs, "gm")
    # [gm] | [player, player] | [gm]
    assert len(chunks) == 3
    assert len(chunks[1].messages) == 2
    assert chunks[1].is_gm_post is False
