"""Build the deterministic E2E fixture DB for the Flutter integration tests.

WHAT: creates `e2e.db` next to this script — a SMALL, fully deterministic Aurelm
database (fixed ids, fixed timestamps) with the REAL Python-owned schema plus a
handful of rows covering every screen the E2E suite navigates (civs, entities +
aliases + mentions, turns, subjects, entity relations).

WHY: the integration tests must run anywhere (CI, another machine), so the
fixture cannot be a machine-local copy of a real DB. This rebuilds it from source
— `init_db` + `run_migrations` produce the canonical schema straight from
`database/schema.sql` + `database/migrations/*.sql` (the same call the pipeline
runner makes), then we insert a known dataset. No binary DB is committed as the
source of truth; the fixture is reproducible from this script.

COMMENT: run from anywhere — `py -3.12 gui/integration_test/fixtures/build_fixture.py`.
The pipeline package is put on sys.path relative to this file, so no install/cwd
assumptions. Values (entity_type, relation_type, subject direction/category/...)
match the real vocabularies so the app renders them exactly as in production.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# --- load the pipeline's db helpers WITHOUT importing the pipeline package ----
# This file: <repo>/gui/integration_test/fixtures/build_fixture.py → parents[3] = repo.
# `pipeline/pipeline/__init__.py` eagerly imports the whole runner (httpx, LLM
# providers…), so `from pipeline.db import …` would drag heavy deps into CI. db.py
# is stdlib-only (sqlite3 + pathlib) and resolves the schema from its own __file__,
# so we load it directly by path — canonical schema, zero extra dependencies.
_REPO = Path(__file__).resolve().parents[3]
_DB_PY = _REPO / "pipeline" / "pipeline" / "db.py"
_spec = importlib.util.spec_from_file_location("aurelm_pipeline_db", _DB_PY)
_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db)  # type: ignore[union-attr]
init_db, run_migrations, get_connection = _db.init_db, _db.run_migrations, _db.get_connection

_OUT = Path(__file__).resolve().parent / "e2e.db"

# Fixed timestamps so every rebuild is byte-stable (no datetime('now')).
_T0 = "2024-01-01T00:00:00"


def _build() -> None:
    if _OUT.exists():
        _OUT.unlink()  # always rebuild from scratch — deterministic

    db_path = str(_OUT)
    init_db(db_path)          # base schema (database/schema.sql)
    run_migrations(db_path)   # all migrations (database/migrations/*.sql)

    conn = get_connection(db_path)
    cur = conn.cursor()

    # --- civilizations --------------------------------------------------------
    cur.executemany(
        "INSERT INTO civ_civilizations (id, name, player_name, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Confluence", "Rubanc", _T0, _T0),
            (2, "Cheveux de Sang", None, _T0, _T0),
        ],
    )

    # --- turns (raw_message_ids is NOT NULL — store a JSON list) --------------
    cur.executemany(
        "INSERT INTO turn_turns (id, civ_id, turn_number, title, summary, "
        "raw_message_ids, turn_type, game_date_start, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'standard', ?, ?)",
        [
            (1, 1, 1, "Les premiers pas", "La Confluence s'installe le long des deux rivières.",
             '["m1"]', "An 0", _T0),
            (2, 1, 2, "La découverte de l'argile", "Les artisans révèlent l'Argile Vivante.",
             '["m2"]', "An 12", _T0),
            (3, 2, 1, "Voiles à l'horizon", "Les Cheveux de Sang accostent pour la première fois.",
             '["m3"]', "An 15", _T0),
        ],
    )

    # --- entities (varied types so every filter/type badge has data) ----------
    cur.executemany(
        "INSERT INTO entity_entities (id, canonical_name, entity_type, civ_id, "
        "description, first_seen_turn, last_seen_turn, is_active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        [
            (1, "Rubanc", "person", 1, "Chef de la Confluence, joueur historique.", 1, 2, _T0, _T0),
            (2, "Argile Vivante", "technology", 1,
             "Argile qui durcit au contact de l'air ;技術 clé de la Confluence.", 2, 2, _T0, _T0),
            (3, "Vallée de la Confluence", "place", 1,
             "Vallée fluviale entre deux rivières cristallines.", 1, 2, _T0, _T0),
            (4, "Caste de l'Air", "caste", 1,
             "L'une des cinq castes de l'oligarchie de la Confluence.", 1, 2, _T0, _T0),
            (5, "Culte des Ancêtres", "belief", 1,
             "Croyance centrale vénérant la lignée fondatrice.", 2, 2, _T0, _T0),
            (6, "Cheveux de Sang", "civilization", 2,
             "Civilisation marine étrangère, premier contact établi.", 3, 3, _T0, _T0),
        ],
    )

    # --- aliases (naming-history UI) -----------------------------------------
    cur.execute(
        "INSERT INTO entity_aliases (entity_id, alias, first_seen_turn_id) VALUES (2, 'Argile Vive', 2)"
    )

    # --- mentions (entity ↔ turn links) --------------------------------------
    cur.executemany(
        "INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context, source) "
        "VALUES (?, ?, ?, ?, 'gm')",
        [
            (1, 1, "Rubanc", "Rubanc mène la fondation.", ),
            (3, 1, "Vallée de la Confluence", "au cœur de la Vallée de la Confluence.", ),
            (2, 2, "Argile Vivante", "les artisans façonnent l'Argile Vivante.", ),
            (4, 2, "Caste de l'Air", "la Caste de l'Air supervise l'ouvrage.", ),
            (6, 3, "Cheveux de Sang", "les Cheveux de Sang débarquent.", ),
        ],
    )

    # --- entity relations (graph edges; real civ relation vocabulary) --------
    cur.executemany(
        "INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, "
        "description, turn_id, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
        [
            (1, 4, "member_of", "Rubanc appartient à la Caste de l'Air.", 1, _T0),
            (1, 3, "located_in", "Rubanc réside dans la Vallée de la Confluence.", 1, _T0),
            (4, 5, "worships", "La Caste de l'Air honore le Culte des Ancêtres.", 2, _T0),
        ],
    )

    # --- subjects (MJ↔PJ threads) --------------------------------------------
    cur.executemany(
        "INSERT INTO subject_subjects (civ_id, source_turn_id, direction, title, description, "
        "source_quote, category, status, tags, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?)",
        [
            (1, 2, "mj_to_pj", "Exploiter l'Argile Vivante ?",
             "Le MJ propose d'industrialiser l'Argile Vivante.",
             "Que faites-vous de cette découverte ?", "choice", "open", _T0, _T0),
            (1, 1, "pj_to_mj", "Cartographier les rivières",
             "Le PJ initie une expédition de cartographie.",
             "Nous remontons la rivière nord.", "initiative", "resolved", _T0, _T0),
        ],
    )

    # --- agent memory (self-authored from GM feedback; migration 039) --------
    cur.executemany(
        "INSERT INTO agent_memory (mem_key, description, content, civ_id, mem_type, "
        "active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
        [
            ("confluence-bronze", "Bronze de la Confluence",
             "Les Confluents n'ont pas encore de bronze (ruling MJ).", 1, "fact", _T0, _T0),
            ("style-citation", "Style de reponse",
             "Toujours citer le tour et la civ a chaque fait.", None, "preference", _T0, _T0),
        ],
    )

    conn.commit()
    conn.close()

    # Report a small manifest so a rebuild is auditable.
    check = get_connection(db_path)
    counts = {
        t: check.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("civ_civilizations", "turn_turns", "entity_entities",
                  "entity_aliases", "entity_mentions", "entity_relations",
                  "subject_subjects", "agent_memory")
    }
    check.close()
    print(f"Built fixture -> {_OUT}")
    for t, n in counts.items():
        print(f"  {t}: {n}")


if __name__ == "__main__":
    _build()
