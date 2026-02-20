-- Aurelm Database Schema
-- SQLite with WAL mode and foreign keys enforced

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================
-- CIVILIZATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS civ_civilizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    player_name TEXT,
    discord_channel_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- TURNS
-- ============================================================

CREATE TABLE IF NOT EXISTS turn_raw_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_message_id TEXT UNIQUE NOT NULL,
    discord_channel_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    attachments TEXT,  -- JSON array of attachment URLs
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS turn_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
    turn_number INTEGER NOT NULL,
    title TEXT,
    summary TEXT,
    detailed_summary TEXT,
    key_events TEXT,        -- JSON array of strings
    choices_made TEXT,       -- JSON array of strings
    raw_message_ids TEXT NOT NULL,  -- JSON array of turn_raw_messages.id
    turn_type TEXT NOT NULL DEFAULT 'standard',  -- standard, event, first_contact, crisis
    game_date_start TEXT,  -- In-game date/era
    game_date_end TEXT,
    media_links TEXT,        -- JSON array of {type, url, title?}
    technologies TEXT,       -- JSON array of strings
    resources TEXT,          -- JSON array of strings
    beliefs TEXT,            -- JSON array of strings
    geography TEXT,          -- JSON array of strings
    choices_proposed TEXT,   -- JSON array of strings
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT,
    UNIQUE(civ_id, turn_number)
);

CREATE TABLE IF NOT EXISTS turn_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    segment_order INTEGER NOT NULL,
    segment_type TEXT NOT NULL,  -- narrative, choice, consequence, ooc, description
    content TEXT NOT NULL,
    UNIQUE(turn_id, segment_order)
);

-- ============================================================
-- ENTITIES (extracted by NER)
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- person, place, technology, institution, resource, creature, event
    civ_id INTEGER REFERENCES civ_civilizations(id),  -- NULL for global/cross-civ entities
    description TEXT,
    history TEXT,           -- JSON array of chronological events
    first_seen_turn INTEGER REFERENCES turn_turns(id),
    last_seen_turn INTEGER REFERENCES turn_turns(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(canonical_name, civ_id)
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    UNIQUE(entity_id, alias)
);

CREATE TABLE IF NOT EXISTS entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    segment_id INTEGER REFERENCES turn_segments(id),
    mention_text TEXT NOT NULL,
    context TEXT  -- Surrounding text for disambiguation
);

-- ============================================================
-- RELATIONS between entities
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,  -- located_in, member_of, created_by, allied_with, controls, etc.
    description TEXT,
    turn_id INTEGER REFERENCES turn_turns(id),  -- When this relation was established
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- PIPELINE STATE
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    messages_processed INTEGER DEFAULT 0,
    turns_created INTEGER DEFAULT 0,
    entities_extracted INTEGER DEFAULT 0,
    error_message TEXT
);

-- Track which turns have been processed by the pipeline
CREATE TABLE IF NOT EXISTS pipeline_turn_status (
    turn_id INTEGER PRIMARY KEY REFERENCES turn_turns(id) ON DELETE CASCADE,
    processed_at TEXT NOT NULL DEFAULT (datetime('now')),
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id)
);

-- Track pipeline progress for Flutter UI
CREATE TABLE IF NOT EXISTS pipeline_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,  -- 'pipeline', 'profiler', 'wiki'
    civ_id INTEGER REFERENCES civ_civilizations(id),
    civ_name TEXT,
    total_units INTEGER NOT NULL,
    current_unit INTEGER NOT NULL,
    unit_type TEXT NOT NULL,  -- 'turn', 'entity', 'page'
    status TEXT NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pipeline_run_id, phase, civ_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_raw_messages_channel ON turn_raw_messages(discord_channel_id);
CREATE INDEX IF NOT EXISTS idx_raw_messages_timestamp ON turn_raw_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_turns_civ ON turn_turns(civ_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entity_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_civ ON entity_entities(civ_id);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_turn ON entity_mentions(turn_id);
CREATE INDEX IF NOT EXISTS idx_relations_source ON entity_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON entity_relations(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_turn_status_run ON pipeline_turn_status(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_progress_run ON pipeline_progress(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_progress_updated ON pipeline_progress(updated_at);
