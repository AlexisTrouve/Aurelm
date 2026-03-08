-- Migration 006: Subject tracking (MJ↔PJ open/resolved subjects)
-- Tracks choices proposed by GM, player initiatives, and their resolutions.

CREATE TABLE IF NOT EXISTS subject_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
    source_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    direction TEXT NOT NULL CHECK (direction IN ('mj_to_pj', 'pj_to_mj')),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL CHECK (category IN ('choice', 'question', 'initiative', 'request')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'superseded', 'abandoned')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(civ_id, source_turn_id, title)
);

CREATE TABLE IF NOT EXISTS subject_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
    option_number INTEGER NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    is_libre INTEGER NOT NULL DEFAULT 0,
    UNIQUE(subject_id, option_number)
);

CREATE TABLE IF NOT EXISTS subject_resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
    resolved_by_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    chosen_option_id INTEGER REFERENCES subject_options(id),
    resolution_text TEXT NOT NULL,
    is_libre INTEGER NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_subjects_civ ON subject_subjects(civ_id);
CREATE INDEX IF NOT EXISTS idx_subjects_status ON subject_subjects(status);
CREATE INDEX IF NOT EXISTS idx_subjects_source_turn ON subject_subjects(source_turn_id);
CREATE INDEX IF NOT EXISTS idx_options_subject ON subject_options(subject_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_subject ON subject_resolutions(subject_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_turn ON subject_resolutions(resolved_by_turn_id);
