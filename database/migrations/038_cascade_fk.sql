-- Migration 038: Add ON DELETE CASCADE to all FK references to civ_civilizations and turn_turns.
-- SQLite cannot ALTER FK constraints — must recreate tables.

PRAGMA foreign_keys = OFF;

-- 1. turn_turns: civ_id -> CASCADE
CREATE TABLE turn_turns_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    title TEXT,
    summary TEXT,
    detailed_summary TEXT,
    key_events TEXT,
    choices_made TEXT,
    raw_message_ids TEXT NOT NULL,
    turn_type TEXT NOT NULL DEFAULT 'standard',
    game_date_start TEXT,
    game_date_end TEXT,
    media_links TEXT,
    technologies TEXT,
    resources TEXT,
    beliefs TEXT,
    geography TEXT,
    choices_proposed TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT,
    thematic_tags TEXT,
    tech_era TEXT,
    tech_era_reasoning TEXT,
    fantasy_level TEXT,
    fantasy_level_reasoning TEXT,
    novelty_summary TEXT,
    new_entity_ids TEXT,
    player_strategy TEXT,
    strategy_tags TEXT,
    gm_fields TEXT
);
INSERT INTO turn_turns_new SELECT * FROM turn_turns;
DROP TABLE turn_turns;
ALTER TABLE turn_turns_new RENAME TO turn_turns;

-- 2. turn_segments: turn_id -> CASCADE
CREATE TABLE turn_segments_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
    segment_order INTEGER NOT NULL,
    segment_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'gm',
    UNIQUE(turn_id, segment_order)
);
INSERT INTO turn_segments_new SELECT * FROM turn_segments;
DROP TABLE turn_segments;
ALTER TABLE turn_segments_new RENAME TO turn_segments;

-- 3. entity_entities: civ_id -> CASCADE, turn refs -> SET NULL
CREATE TABLE entity_entities_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    civ_id INTEGER REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    description TEXT,
    history TEXT,
    first_seen_turn INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    last_seen_turn INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    hidden INTEGER NOT NULL DEFAULT 0,
    disabled INTEGER NOT NULL DEFAULT 0,
    disabled_at TEXT,
    tags TEXT,
    gm_fields TEXT,
    UNIQUE(canonical_name, civ_id)
);
INSERT INTO entity_entities_new SELECT * FROM entity_entities;
DROP TABLE entity_entities;
ALTER TABLE entity_entities_new RENAME TO entity_entities;

-- 4. entity_mentions: turn_id -> CASCADE
CREATE TABLE entity_mentions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
    segment_id INTEGER REFERENCES turn_segments(id) ON DELETE SET NULL,
    mention_text TEXT NOT NULL,
    context TEXT,
    source TEXT NOT NULL DEFAULT 'gm'
);
INSERT INTO entity_mentions_new SELECT * FROM entity_mentions;
DROP TABLE entity_mentions;
ALTER TABLE entity_mentions_new RENAME TO entity_mentions;

-- 5. entity_relations: turn_id -> SET NULL
CREATE TABLE entity_relations_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    description TEXT,
    turn_id INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO entity_relations_new SELECT * FROM entity_relations;
DROP TABLE entity_relations;
ALTER TABLE entity_relations_new RENAME TO entity_relations;

-- 6. entity_aliases: first_seen_turn_id -> SET NULL
CREATE TABLE entity_aliases_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    first_seen_turn_id INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    UNIQUE(entity_id, alias)
);
INSERT INTO entity_aliases_new SELECT * FROM entity_aliases;
DROP TABLE entity_aliases;
ALTER TABLE entity_aliases_new RENAME TO entity_aliases;

-- 7. pipeline_progress: civ_id -> CASCADE
CREATE TABLE pipeline_progress_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    civ_id INTEGER REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    civ_name TEXT,
    total_units INTEGER NOT NULL,
    current_unit INTEGER NOT NULL,
    unit_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    stage_name TEXT,
    llm_calls_done INTEGER DEFAULT 0,
    llm_calls_total INTEGER DEFAULT 0,
    turn_number INTEGER,
    UNIQUE(pipeline_run_id, phase, civ_id)
);
INSERT INTO pipeline_progress_new SELECT * FROM pipeline_progress;
DROP TABLE pipeline_progress;
ALTER TABLE pipeline_progress_new RENAME TO pipeline_progress;

-- 8. subject_resolutions: resolved_by_turn_id -> CASCADE
CREATE TABLE subject_resolutions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
    resolved_by_turn_id INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
    chosen_option_id INTEGER REFERENCES subject_options(id),
    resolution_text TEXT NOT NULL,
    is_libre INTEGER NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_quote TEXT
);
INSERT INTO subject_resolutions_new SELECT * FROM subject_resolutions;
DROP TABLE subject_resolutions;
ALTER TABLE subject_resolutions_new RENAME TO subject_resolutions;

-- 9. civ_relations: last_turn_id -> SET NULL
CREATE TABLE civ_relations_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    target_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    opinion         TEXT NOT NULL DEFAULT 'unknown',
    description     TEXT,
    treaties        TEXT,
    last_turn_id    INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    gm_lock INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_civ_id, target_civ_id)
);
INSERT INTO civ_relations_new SELECT * FROM civ_relations;
DROP TABLE civ_relations;
ALTER TABLE civ_relations_new RENAME TO civ_relations;

PRAGMA foreign_keys = ON;
