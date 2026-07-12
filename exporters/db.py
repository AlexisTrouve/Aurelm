"""Read-only SQLite access for the exporters.

WHAT: Thin query helpers over the four domain-neutral Aurelm tables
(entity_entities, entity_aliases, entity_mentions, entity_relations) plus
turn_turns for human turn numbers. Every helper returns exporters.models
dataclasses, never raw rows.

WHY read-only at the connection level: exporters must NEVER be able to mutate a
live civ DB (the §1 non-regression guard-rail). We open the DB in SQLite URI
"mode=ro", so any accidental write raises instead of corrupting game data.

WHY load-everything-then-traverse-in-Python for the graph: relation counts are
tiny (hundreds), so pulling all relations once and doing BFS in memory is
simpler and faster than per-node queries, and keeps the DB layer dumb.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Entity, Mention, Relation


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open the DB strictly read-only and return a Row-yielding connection.

    COMMENT: we build a proper file:// URI (as_uri() percent-encodes spaces and
    handles the Windows drive letter) and append ?mode=ro so SQLite refuses any
    write. resolve(strict=True) fails loudly if the path is wrong.
    """
    uri = Path(db_path).resolve(strict=True).as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_history(raw: str | None) -> list[str]:
    """Parse the history JSON column into a list of event strings.

    WHY defensive: history is a JSON array of strings in practice, but crashed
    runs can leave NULL/empty/odd values. We normalise everything to list[str]
    so downstream code never has to guard again.
    """
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return [raw]  # not JSON — treat the whole blob as one event
    if isinstance(data, list):
        return [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in data]
    return [data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)]


def _row_to_entity(row: sqlite3.Row) -> Entity:
    """Map an entity_entities row to an Entity dataclass."""
    return Entity(
        id=row["id"],
        canonical_name=row["canonical_name"],
        entity_type=row["entity_type"],
        description=row["description"],
        history=_parse_history(row["history"]),
        first_seen_turn=row["first_seen_turn"],
        last_seen_turn=row["last_seen_turn"],
        is_active=bool(row["is_active"]),
        civ_id=row["civ_id"],
    )


# --- Entities ---------------------------------------------------------------

def fetch_all_entities(
    conn: sqlite3.Connection,
    entity_type: str | None = None,
    civ_id: int | None = None,
    active_only: bool = False,
) -> list[Entity]:
    """Return entities, optionally filtered by type / civ scope / active flag."""
    # COMMENT: first_seen_turn / last_seen_turn are FKs to turn_turns.id (an
    # internal row id), NOT the human turn number. We resolve them to turn_number
    # via correlated subqueries so the model carries display-ready numbers.
    sql = ("SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history, "
           "(SELECT turn_number FROM turn_turns WHERE id = e.first_seen_turn) AS first_seen_turn, "
           "(SELECT turn_number FROM turn_turns WHERE id = e.last_seen_turn) AS last_seen_turn, "
           "e.is_active, e.civ_id FROM entity_entities e")
    where, params = [], []
    if entity_type is not None:
        where.append("e.entity_type = ?"); params.append(entity_type)
    if civ_id is not None:
        where.append("e.civ_id = ?"); params.append(civ_id)
    if active_only:
        where.append("e.is_active = 1")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.canonical_name COLLATE NOCASE"
    return [_row_to_entity(r) for r in conn.execute(sql, params)]


def fetch_entity(conn: sqlite3.Connection, entity_id: int) -> Entity | None:
    """Return a single entity by id, or None."""
    row = conn.execute(
        "SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history, "
        "(SELECT turn_number FROM turn_turns WHERE id = e.first_seen_turn) AS first_seen_turn, "
        "(SELECT turn_number FROM turn_turns WHERE id = e.last_seen_turn) AS last_seen_turn, "
        "e.is_active, e.civ_id "
        "FROM entity_entities e WHERE e.id = ?", (entity_id,)
    ).fetchone()
    return _row_to_entity(row) if row else None


def resolve_entity_id(conn: sqlite3.Connection, name: str) -> int:
    """Resolve a human-typed name to an entity id.

    WHY: the CLI takes --center "Some Name"; we must map it to an id. We try, in
    order: exact canonical_name (case-insensitive), exact alias, then a LIKE
    prefix. Ambiguous/absent names raise LookupError with suggestions rather
    than silently picking one (no fallback that hides a wrong target).
    """
    # 1. exact canonical name (case-insensitive)
    rows = conn.execute(
        "SELECT id, canonical_name FROM entity_entities "
        "WHERE canonical_name = ? COLLATE NOCASE", (name,)
    ).fetchall()
    if len(rows) == 1:
        return rows[0]["id"]
    if len(rows) > 1:
        opts = ", ".join(f"{r['canonical_name']} (id={r['id']})" for r in rows)
        raise LookupError(f"Ambiguous name '{name}' — matches: {opts}")

    # 2. exact alias
    rows = conn.execute(
        "SELECT e.id, e.canonical_name FROM entity_aliases a "
        "JOIN entity_entities e ON e.id = a.entity_id "
        "WHERE a.alias = ? COLLATE NOCASE", (name,)
    ).fetchall()
    if len(rows) == 1:
        return rows[0]["id"]

    # 3. LIKE prefix (suggest, don't guess)
    like = conn.execute(
        "SELECT id, canonical_name FROM entity_entities "
        "WHERE canonical_name LIKE ? COLLATE NOCASE ORDER BY canonical_name LIMIT 8",
        (name + "%",)
    ).fetchall()
    if len(like) == 1:
        return like[0]["id"]
    suggestions = ", ".join(f"{r['canonical_name']}" for r in like) or "none"
    raise LookupError(f"No exact entity named '{name}'. Closest: {suggestions}")


def fetch_aliases(conn: sqlite3.Connection, entity_id: int) -> list[str]:
    """Return the list of alias strings for an entity."""
    return [r["alias"] for r in conn.execute(
        "SELECT alias FROM entity_aliases WHERE entity_id = ? ORDER BY alias", (entity_id,)
    )]


# --- Relations --------------------------------------------------------------

def fetch_all_relations(conn: sqlite3.Connection, active_only: bool = False) -> list[Relation]:
    """Return all relations (edges). Cheap: hundreds of rows even on big games."""
    sql = ("SELECT source_entity_id, target_entity_id, relation_type, description, "
           "turn_id, is_active FROM entity_relations")
    if active_only:
        sql += " WHERE is_active = 1"
    return [
        Relation(
            source_id=r["source_entity_id"],
            target_id=r["target_entity_id"],
            relation_type=r["relation_type"],
            description=r["description"],
            turn_id=r["turn_id"],
            is_active=bool(r["is_active"]),
        )
        for r in conn.execute(sql)
    ]


# --- Mentions ---------------------------------------------------------------

def fetch_mentions(conn: sqlite3.Connection, entity_id: int) -> list[Mention]:
    """Return an entity's mentions, joined to turn_turns for the turn number.

    Ordered by turn number so the history exporter reads chronologically.
    """
    rows = conn.execute(
        "SELECT m.entity_id, m.turn_id, t.turn_number, m.mention_text, m.context "
        "FROM entity_mentions m "
        "LEFT JOIN turn_turns t ON t.id = m.turn_id "
        "WHERE m.entity_id = ? "
        "ORDER BY t.turn_number IS NULL, t.turn_number, m.id", (entity_id,)
    ).fetchall()
    return [
        Mention(
            entity_id=r["entity_id"],
            turn_id=r["turn_id"],
            turn_number=r["turn_number"],
            mention_text=r["mention_text"],
            context=r["context"],
        )
        for r in rows
    ]
