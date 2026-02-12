-- Migration 004: Add incremental tracking tables
-- Allows tracking which turns have been processed and pipeline progress for UI

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

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_turn_status_run ON pipeline_turn_status(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_progress_run ON pipeline_progress(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_progress_updated ON pipeline_progress(updated_at);
