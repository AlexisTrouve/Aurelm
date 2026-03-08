CREATE TABLE IF NOT EXISTS pipeline_turn_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('gm', 'pj')),
    text_chars INTEGER NOT NULL DEFAULT 0,
    sys_prompt_chars INTEGER NOT NULL DEFAULT 0,
    chunks INTEGER NOT NULL DEFAULT 0,
    raw_entities INTEGER NOT NULL DEFAULT 0,
    after_dedup INTEGER NOT NULL DEFAULT 0,
    final_entities INTEGER NOT NULL DEFAULT 0,
    est_tokens INTEGER NOT NULL DEFAULT 0,
    est_cost_usd REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(run_id, turn_id, source)
);

CREATE INDEX IF NOT EXISTS idx_turn_stats_run ON pipeline_turn_stats(run_id);

CREATE INDEX IF NOT EXISTS idx_turn_stats_turn ON pipeline_turn_stats(turn_id);

ALTER TABLE pipeline_runs ADD COLUMN total_tokens INTEGER DEFAULT 0;

ALTER TABLE pipeline_runs ADD COLUMN total_cost_usd REAL DEFAULT 0.0;
