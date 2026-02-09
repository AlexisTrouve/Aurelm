"""Exporter — writes structured pipeline output back to SQLite."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .chunker import TurnChunk
from .classifier import ClassifiedSegment
from .ner import ExtractedEntity
from .summarizer import TurnSummary


@dataclass
class ProcessedTurn:
    chunk: TurnChunk
    segments: list[ClassifiedSegment]
    entities: list[ExtractedEntity]
    summary: TurnSummary


def export_turn(db_path: str, civ_id: int, turn: ProcessedTurn) -> int:
    """Write a fully processed turn to the database. Returns the turn ID."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        # Get next turn number
        row = conn.execute(
            "SELECT COALESCE(MAX(turn_number), 0) + 1 FROM turn_turns WHERE civ_id = ?",
            (civ_id,),
        ).fetchone()
        turn_number = row[0] if row else 1

        raw_ids = json.dumps([m.id for m in turn.chunk.messages])

        # Insert turn
        cursor = conn.execute(
            """
            INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids, turn_type, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                civ_id,
                turn_number,
                turn.summary.short_summary,
                turn.summary.detailed_summary,
                raw_ids,
                turn.chunk.turn_type,
            ),
        )
        turn_id = cursor.lastrowid
        assert turn_id is not None

        # Insert segments
        for i, seg in enumerate(turn.segments):
            conn.execute(
                "INSERT INTO turn_segments (turn_id, segment_order, segment_type, content) VALUES (?, ?, ?, ?)",
                (turn_id, i, seg.segment_type.value, seg.text),
            )

        # Insert/update entities
        for ent in turn.entities:
            _upsert_entity(conn, civ_id, turn_id, ent)

        conn.commit()
        return turn_id
    finally:
        conn.close()


def _upsert_entity(
    conn: sqlite3.Connection,
    civ_id: int,
    turn_id: int,
    entity: ExtractedEntity,
) -> None:
    """Insert or update an entity and record its mention."""
    # Check if entity exists
    row = conn.execute(
        "SELECT id FROM entity_entities WHERE canonical_name = ? AND civ_id = ?",
        (entity.text, civ_id),
    ).fetchone()

    if row:
        entity_id = row[0]
        conn.execute(
            "UPDATE entity_entities SET last_seen_turn = ?, updated_at = datetime('now') WHERE id = ?",
            (turn_id, entity_id),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn, last_seen_turn)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entity.text, entity.label, civ_id, turn_id, turn_id),
        )
        entity_id = cursor.lastrowid

    # Record mention
    conn.execute(
        "INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context) VALUES (?, ?, ?, ?)",
        (entity_id, turn_id, entity.text, entity.context),
    )
