"""Tests for the configurable domain-profile ontology (P2).

Two jobs:
  1. Non-regression — the civ profile carries the EXACT historical vocabulary,
     and the old module constants remain valid aliases of it.
  2. Profile-awareness — the two ontology gates (entity types in FactExtractor,
     relation types in entity_profiler) follow the ACTIVE profile.
"""

from __future__ import annotations

import sqlite3

import pytest

from pipeline.domain_profile import CIV_PROFILE, NOVEL_PROFILE, get_profile
from pipeline.entity_filter import VALID_ENTITY_TYPES
from pipeline.entity_profiler import (
    VALID_RELATION_TYPES,
    EntityProfile,
    _resolve_and_insert_relations,
)
from pipeline.extraction_versions import get_version
from pipeline.fact_extractor import FactExtractor

# The historical civ ontology — hardcoded here on purpose: if someone edits the
# civ profile, THIS test (not the live game) is what must break first.
_HIST_CIV_ENTITY_TYPES = {
    "person", "place", "technology", "institution", "resource",
    "creature", "event", "civilization", "caste", "belief",
}
_HIST_CIV_RELATION_TYPES = {
    "located_in", "member_of", "created_by", "allied_with", "controls",
    "part_of", "produces", "worships", "enemy_of", "trades_with",
}


# --- non-regression ---------------------------------------------------------

def test_civ_profile_matches_historical_ontology():
    assert CIV_PROFILE.entity_types == _HIST_CIV_ENTITY_TYPES
    assert CIV_PROFILE.relation_types == _HIST_CIV_RELATION_TYPES


def test_legacy_constants_alias_civ_profile():
    assert VALID_ENTITY_TYPES == _HIST_CIV_ENTITY_TYPES
    assert VALID_RELATION_TYPES == _HIST_CIV_RELATION_TYPES


# --- registry ---------------------------------------------------------------

def test_get_profile_resolution():
    assert get_profile("civ") is CIV_PROFILE
    assert get_profile("novel") is NOVEL_PROFILE
    assert get_profile(None) is CIV_PROFILE      # default keeps civ behaviour
    assert get_profile("") is CIV_PROFILE
    with pytest.raises(KeyError):
        get_profile("does-not-exist")


def test_novel_profile_is_person_centred():
    assert "person" in NOVEL_PROFILE.entity_types
    assert "caste" not in NOVEL_PROFILE.entity_types       # civ-only type
    assert "mentor-de" in NOVEL_PROFILE.relation_types
    assert "heritier" in " ".join(NOVEL_PROFILE.relation_types) or \
           "héritier-du-geste" in NOVEL_PROFILE.relation_types


# --- extraction version binds a profile -------------------------------------

def test_versions_carry_their_profile():
    assert get_version("novel-v1").profile == "novel"
    # a representative civ version defaults to civ
    assert get_version("v22.2.2-pastlevel").profile == "civ"


def test_fact_extractor_entity_gate_follows_profile():
    civ_fe = FactExtractor(version=get_version("v22.2.2-pastlevel"))
    novel_fe = FactExtractor(version=get_version("novel-v1"))
    assert civ_fe.allowed_entity_types == CIV_PROFILE.entity_types
    assert novel_fe.allowed_entity_types == NOVEL_PROFILE.entity_types


# --- relation gate follows the profile (E2E on a tiny DB) -------------------

def _relations_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE entity_entities (id INTEGER PRIMARY KEY, canonical_name TEXT,
            civ_id INTEGER, is_active INTEGER DEFAULT 1);
        CREATE TABLE entity_aliases (id INTEGER PRIMARY KEY, entity_id INTEGER, alias TEXT);
        CREATE TABLE entity_relations (id INTEGER PRIMARY KEY, source_entity_id INTEGER,
            target_entity_id INTEGER, relation_type TEXT, description TEXT);
    """)
    conn.executemany(
        "INSERT INTO entity_entities (id, canonical_name, civ_id, is_active) VALUES (?,?,?,1)",
        [(1, "Oracle", 7), (2, "Front-Levé", 7)],
    )
    conn.commit()
    return conn


def _mentor_profile() -> EntityProfile:
    # Oracle --mentor-de--> Front-Levé : a NOVEL relation type, absent from civ.
    return EntityProfile(
        entity_id=1, canonical_name="Oracle", entity_type="person", civ_id=7,
        raw_relations=[{"target": "Front-Levé", "type": "mentor-de", "description": "guide"}],
    )


def test_relation_gate_rejects_novel_type_under_civ_profile():
    conn = _relations_db()
    inserted = _resolve_and_insert_relations(
        conn, [_mentor_profile()], incremental=False,
        relation_types=CIV_PROFILE.relation_types,
    )
    assert inserted == 0
    assert conn.execute("SELECT COUNT(*) c FROM entity_relations").fetchone()["c"] == 0


def test_relation_gate_accepts_novel_type_under_novel_profile():
    conn = _relations_db()
    inserted = _resolve_and_insert_relations(
        conn, [_mentor_profile()], incremental=False,
        relation_types=NOVEL_PROFILE.relation_types,
    )
    assert inserted == 1
    row = conn.execute("SELECT relation_type FROM entity_relations").fetchone()
    assert row["relation_type"] == "mentor-de"


def test_relation_gate_defaults_to_civ_when_unset():
    # No relation_types passed -> civ gate -> civ type accepted, novel type not.
    conn = _relations_db()
    civ_profile = EntityProfile(
        entity_id=1, canonical_name="Oracle", entity_type="person", civ_id=7,
        raw_relations=[{"target": "Front-Levé", "type": "allied_with", "description": "x"}],
    )
    inserted = _resolve_and_insert_relations(conn, [civ_profile], incremental=False)
    assert inserted == 1


# --- profiling loop end-to-end (regression: no param/loop-var shadowing) -----
# This exercises build_entity_profiles' per-entity loop with a fake LLM. It is
# the test that was MISSING in P2a: renaming the loop var 'profile' collided
# with the DomainProfile param, so domain_profile.name / .relation_types blew up
# with AttributeError on any real profiling run — but no unit test drove the loop
# (integration tests need Ollama). This locks the fix without an LLM.

class _FakeProvider:
    """Returns a fixed JSON string for every profiling call (mimics provider.chat)."""

    def __init__(self, response: str):
        self._response = response

    def chat(self, **kwargs) -> str:
        return self._response


def _profiling_db(tmp_path) -> str:
    from pipeline.db import init_db, run_migrations, get_connection
    db = str(tmp_path / "prof.db")
    init_db(db)
    run_migrations(db)  # gm_fields, tags, etc. are added by migrations
    conn = get_connection(db)
    conn.execute("INSERT INTO civ_civilizations (id, name) VALUES (1, 'Roman')")
    conn.execute("INSERT INTO turn_turns (id, civ_id, turn_number, raw_message_ids) "
                 "VALUES (1, 1, 1, '[]')")
    conn.executemany(
        "INSERT INTO entity_entities (id, canonical_name, entity_type, civ_id, is_active) "
        "VALUES (?,?,?,1,1)",
        [(1, "Oracle", "person"), (2, "Front-Levé", "person")],
    )
    conn.executemany(
        "INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context) VALUES (?,1,?,?)",
        [(1, "Oracle", "Oracle observe."), (2, "Front-Levé", "Front-Levé écoute.")],
    )
    conn.commit(); conn.close()
    return db


def test_build_entity_profiles_novel_profile_end_to_end(tmp_path):
    import json as _json
    from pipeline.entity_profiler import build_entity_profiles

    db = _profiling_db(tmp_path)
    # Fake LLM: a description + one NOVEL relation (mentor-de -> Front-Levé).
    canned = _json.dumps({
        "description": "L'immortel qui observe.",
        "turn_summaries": {"Tour 1": "Oracle observe le camp."},
        "aliases": [],
        "relations": [{"target": "Front-Levé", "type": "mentor-de", "description": "guide"}],
        "tags": [],
    }, ensure_ascii=False)

    profiles = build_entity_profiles(
        db, model="fake", use_llm=True, incremental=False,
        provider=_FakeProvider(canned), domain_profile=NOVEL_PROFILE,
    )

    # Loop ran without AttributeError and wrote descriptions.
    assert any(p.description for p in profiles)
    from pipeline.db import get_connection
    conn = get_connection(db)
    described = conn.execute(
        "SELECT COUNT(*) c FROM entity_entities WHERE description IS NOT NULL AND description != ''"
    ).fetchone()["c"]
    assert described >= 1
    # The novel relation type survived the (novel) gate and was inserted.
    rel = conn.execute(
        "SELECT relation_type FROM entity_relations WHERE relation_type='mentor-de'"
    ).fetchone()
    assert rel is not None
