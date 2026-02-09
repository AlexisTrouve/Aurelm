"""Turn boundary detection — groups raw messages into logical game turns."""

from __future__ import annotations

from dataclasses import dataclass

from .ingestion import RawMessage


@dataclass
class TurnChunk:
    messages: list[RawMessage]
    turn_type: str  # standard, event, first_contact, crisis
    is_gm_post: bool


def detect_turn_boundaries(
    messages: list[RawMessage], gm_author_id: str
) -> list[TurnChunk]:
    """Group sequential messages into turn chunks based on author and content patterns.

    A new turn starts when:
    - The GM posts after a player response
    - A significant time gap exists between messages
    - Content markers indicate a new turn (e.g., turn headers, date markers)
    """
    if not messages:
        return []

    chunks: list[TurnChunk] = []
    current_messages: list[RawMessage] = [messages[0]]

    for msg in messages[1:]:
        is_new_turn = _is_turn_boundary(current_messages[-1], msg, gm_author_id)
        if is_new_turn:
            chunks.append(_make_chunk(current_messages, gm_author_id))
            current_messages = [msg]
        else:
            current_messages.append(msg)

    if current_messages:
        chunks.append(_make_chunk(current_messages, gm_author_id))

    return chunks


def _is_turn_boundary(prev: RawMessage, curr: RawMessage, gm_author_id: str) -> bool:
    """Determine if a message starts a new turn."""
    # GM posting after a non-GM message = new turn
    if curr.author_id == gm_author_id and prev.author_id != gm_author_id:
        return True
    # TODO: Time gap detection
    # TODO: Content marker detection (headers, separators)
    return False


def _make_chunk(messages: list[RawMessage], gm_author_id: str) -> TurnChunk:
    is_gm = any(m.author_id == gm_author_id for m in messages)
    return TurnChunk(
        messages=messages,
        turn_type="standard",  # TODO: Classify turn type from content
        is_gm_post=is_gm,
    )
