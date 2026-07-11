"""Shared pytest fixtures — a tiny synthetic Aurelm DB.

WHAT: builds a minimal on-disk SQLite DB carrying only the tables the exporters
read (entity_entities, entity_aliases, entity_mentions, entity_relations,
turn_turns), populated with a small graph.

WHY synthetic (not the real civ DB): tests must be deterministic and CI-safe.
One node deliberately has a Chinese name (云隐) so the graph render is exercised
against CJK text — the customer #1 (roman) is in Chinese, and a tofu regression
must fail a test, not ship silently.

Graph shape (ids):
    1 Oracle (person)  --allied_with/worships-->  2 云隐 (person)
    2 云隐 (person)     --allied_with-->           3 Front-Levé (person)
    1 Oracle (person)  --located_in-->            4 Rivière (place)
first_seen_turn values are turn_turns.id (10/20/30 -> turn_number 1/2/3).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

_SCHEMA = """
CREATE TABLE turn_turns (id INTEGER PRIMARY KEY, turn_number INTEGER);
CREATE TABLE entity_entities (
    id INTEGER PRIMARY KEY, canonical_name TEXT, entity_type TEXT, description TEXT,
    history TEXT, first_seen_turn INTEGER, last_seen_turn INTEGER,
    is_active INTEGER DEFAULT 1, civ_id INTEGER
);
CREATE TABLE entity_aliases (id INTEGER PRIMARY KEY, entity_id INTEGER, alias TEXT);
CREATE TABLE entity_mentions (
    id INTEGER PRIMARY KEY, entity_id INTEGER, turn_id INTEGER,
    mention_text TEXT, context TEXT
);
CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY, source_entity_id INTEGER, target_entity_id INTEGER,
    relation_type TEXT, description TEXT, turn_id INTEGER, is_active INTEGER DEFAULT 1
);
"""


@pytest.fixture
def sample_db(tmp_path):
    """Create the synthetic DB, return its path (str)."""
    path = tmp_path / "sample.aurelm.db"
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)

    conn.executemany("INSERT INTO turn_turns (id, turn_number) VALUES (?, ?)",
                     [(10, 1), (20, 2), (30, 3)])

    conn.executemany(
        "INSERT INTO entity_entities "
        "(id, canonical_name, entity_type, description, history, first_seen_turn, "
        "last_seen_turn, is_active, civ_id) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (1, "Oracle", "person", "L'immortel qui observe.",
             json.dumps(["Tour 1: Oracle apparait.", "Tour 2: Oracle parle."]), 10, 20, 1, 7),
            (2, "云隐", "person", "Un personnage au nom chinois.",
             json.dumps(["Tour 1: 云隐 arrive."]), 10, None, 1, 7),
            (3, "Front-Levé", "person", "Le jeune apprenti.",
             json.dumps(["Tour 3: Front-Levé grandit."]), 30, None, 1, 7),
            (4, "Rivière", "place", "Le cours d'eau.",
             json.dumps([]), 10, None, 0, 7),
        ],
    )
    conn.execute("INSERT INTO entity_aliases (entity_id, alias) VALUES (?, ?)", (1, "L'Immortel"))
    conn.executemany(
        "INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context) VALUES (?,?,?,?)",
        [
            (1, 10, "Oracle", "au bord de la riviere"),
            (1, 20, "Oracle", "sous la lune"),
            (2, 10, "云隐", "dans la brume"),
        ],
    )
    conn.executemany(
        "INSERT INTO entity_relations "
        "(source_entity_id, target_entity_id, relation_type, description, turn_id, is_active) "
        "VALUES (?,?,?,?,?,?)",
        [
            (1, 2, "allied_with", "allies de longue date", 10, 1),
            (1, 2, "worships", "veneration", 20, 1),   # 2nd type, same pair -> dedup test
            (2, 3, "allied_with", "mentorat", 30, 1),
            (1, 4, "located_in", "reside au bord", 10, 1),
        ],
    )
    conn.commit()
    conn.close()
    return str(path)
