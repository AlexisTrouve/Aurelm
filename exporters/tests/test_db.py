"""Tests for the read-only DB layer."""

from __future__ import annotations

import pytest

from exporters import db


def test_fetch_all_entities(sample_db):
    conn = db.get_connection(sample_db)
    ents = db.fetch_all_entities(conn)
    assert len(ents) == 4
    persons = db.fetch_all_entities(conn, entity_type="person")
    assert {e.canonical_name for e in persons} == {"Oracle", "云隐", "Front-Levé"}
    active = db.fetch_all_entities(conn, active_only=True)
    assert all(e.is_active for e in active)
    assert "Rivière" not in {e.canonical_name for e in active}  # is_active=0


def test_first_seen_turn_resolves_to_turn_number(sample_db):
    # first_seen_turn stores turn_turns.id (10) -> must surface turn_number 1.
    conn = db.get_connection(sample_db)
    oracle = db.fetch_entity(conn, 1)
    assert oracle.first_seen_turn == 1
    assert oracle.last_seen_turn == 2


def test_resolve_entity_id_by_name_and_alias(sample_db):
    conn = db.get_connection(sample_db)
    assert db.resolve_entity_id(conn, "Oracle") == 1
    assert db.resolve_entity_id(conn, "oracle") == 1          # case-insensitive
    assert db.resolve_entity_id(conn, "L'Immortel") == 1      # via alias
    assert db.resolve_entity_id(conn, "云隐") == 2             # CJK name


def test_resolve_entity_id_unknown_raises(sample_db):
    conn = db.get_connection(sample_db)
    with pytest.raises(LookupError):
        db.resolve_entity_id(conn, "Nobody")


def test_mentions_joined_to_turn_numbers(sample_db):
    conn = db.get_connection(sample_db)
    mentions = db.fetch_mentions(conn, 1)
    assert [m.turn_number for m in mentions] == [1, 2]


def test_connection_is_read_only(sample_db):
    conn = db.get_connection(sample_db)
    import sqlite3
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("UPDATE entity_entities SET description='x' WHERE id=1")
