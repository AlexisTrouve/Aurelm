"""Database helpers for subject tracking (MJ<->PJ open/resolved subjects).

Separated from subject_extractor.py for testability — these functions
operate on sqlite3 connections without LLM dependencies.
"""

from __future__ import annotations

import sqlite3
from typing import Any


def load_open_subjects(conn: sqlite3.Connection, civ_id: int) -> list[dict]:
    """Load all open subjects for a civilization, with their options.

    Returns a list of dicts with keys:
        id, title, description, direction, category, source_turn_number,
        options: [{option_number, label, description, is_libre}]
    """
    rows = conn.execute(
        """SELECT s.id, s.title, s.description, s.direction, s.category,
                  t.turn_number AS source_turn_number
           FROM subject_subjects s
           JOIN turn_turns t ON s.source_turn_id = t.id
           WHERE s.civ_id = ? AND s.status = 'open'
           ORDER BY t.turn_number, s.id""",
        (civ_id,),
    ).fetchall()

    subjects = []
    for row in rows:
        subject = {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "direction": row["direction"],
            "category": row["category"],
            "source_turn_number": row["source_turn_number"],
        }

        # Load options for this subject
        opt_rows = conn.execute(
            """SELECT option_number, label, description, is_libre
               FROM subject_options
               WHERE subject_id = ?
               ORDER BY option_number""",
            (row["id"],),
        ).fetchall()

        subject["options"] = [
            {
                "option_number": o["option_number"],
                "label": o["label"],
                "description": o["description"],
                "is_libre": bool(o["is_libre"]),
            }
            for o in opt_rows
        ]
        subjects.append(subject)

    return subjects


def insert_subject(
    conn: sqlite3.Connection,
    subject: dict,
    civ_id: int,
    turn_id: int,
) -> int | None:
    """Insert a subject with its options. Returns subject_id, or None if duplicate.

    Args:
        subject: Dict with keys title, description, direction, category,
                 options: [{number, label, description, is_libre}]
        civ_id: Civilization ID
        turn_id: Source turn ID

    Uses INSERT OR IGNORE for idempotency (UNIQUE on civ_id, source_turn_id, title).
    """
    import json as _json
    cursor = conn.execute(
        """INSERT OR IGNORE INTO subject_subjects
           (civ_id, source_turn_id, direction, title, description, category, source_quote, tags)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            civ_id,
            turn_id,
            subject["direction"],
            subject["title"],
            subject.get("description", ""),
            subject["category"],
            subject.get("source_quote", ""),
            _json.dumps(subject.get("tags", []), ensure_ascii=False),
        ),
    )

    # If INSERT was ignored (duplicate), fetch existing ID
    if cursor.rowcount == 0:
        row = conn.execute(
            """SELECT id FROM subject_subjects
               WHERE civ_id = ? AND source_turn_id = ? AND title = ?""",
            (civ_id, turn_id, subject["title"]),
        ).fetchone()
        return row["id"] if row else None

    subject_id = cursor.lastrowid

    # Insert options
    for opt in subject.get("options", []):
        conn.execute(
            """INSERT OR IGNORE INTO subject_options
               (subject_id, option_number, label, description, is_libre)
               VALUES (?, ?, ?, ?, ?)""",
            (
                subject_id,
                opt.get("number", opt.get("option_number", 0)),
                opt["label"],
                opt.get("description", ""),
                1 if opt.get("is_libre", False) else 0,
            ),
        )

    return subject_id


def apply_resolutions(
    conn: sqlite3.Connection,
    resolutions: list[dict],
    turn_id: int,
    confidence_threshold: float = 0.7,
) -> int:
    """Apply resolution matches to open subjects.

    Each resolution dict has keys:
        subject_id, resolution_text, chosen_option_label (optional),
        is_libre (optional), confidence

    All resolutions are stored in DB for reference.
    Only resolutions >= confidence_threshold mark the subject as 'resolved'.
    Returns count of resolutions that changed status to resolved.
    """
    applied = 0

    for res in resolutions:
        confidence = res.get("confidence", 0.0)
        subject_id = res["subject_id"]

        # Find matching option by label (if provided)
        chosen_option_id = None
        chosen_label = res.get("chosen_option_label")
        if chosen_label:
            opt_row = conn.execute(
                """SELECT id FROM subject_options
                   WHERE subject_id = ? AND LOWER(label) = LOWER(?)""",
                (subject_id, chosen_label),
            ).fetchone()
            if opt_row:
                chosen_option_id = opt_row["id"]

        is_libre = 1 if res.get("is_libre", False) else 0

        # Always store the resolution record (for reporting/transparency)
        conn.execute(
            """INSERT INTO subject_resolutions
               (subject_id, resolved_by_turn_id, chosen_option_id,
                resolution_text, is_libre, confidence, source_quote)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                subject_id,
                turn_id,
                chosen_option_id,
                res["resolution_text"],
                is_libre,
                confidence,
                res.get("source_quote", ""),
            ),
        )

        # Only mark subject as resolved if confidence meets threshold
        if confidence >= confidence_threshold:
            conn.execute(
                """UPDATE subject_subjects
                   SET status = 'resolved', updated_at = datetime('now')
                   WHERE id = ?""",
                (subject_id,),
            )
            applied += 1

    return applied


def get_subject_stats(conn: sqlite3.Connection, civ_id: int) -> dict[str, int]:
    """Get subject counts by status for a civilization.

    Returns dict with keys: open, resolved, superseded, abandoned, total.
    """
    rows = conn.execute(
        """SELECT status, COUNT(*) as cnt
           FROM subject_subjects
           WHERE civ_id = ?
           GROUP BY status""",
        (civ_id,),
    ).fetchall()

    stats: dict[str, int] = {"open": 0, "resolved": 0, "superseded": 0, "abandoned": 0}
    for row in rows:
        stats[row["status"]] = row["cnt"]
    stats["total"] = sum(stats.values())

    return stats
