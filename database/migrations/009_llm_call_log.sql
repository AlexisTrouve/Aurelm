CREATE TABLE IF NOT EXISTS pipeline_llm_calls (
    -- Stores every prompt sent to an LLM during pipeline execution.
    -- Allows post-hoc inspection of what was sent for each turn/stage,
    -- debugging of missed entities, and prompt quality analysis.
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    turn_id     INTEGER REFERENCES turn_turns(id) ON DELETE CASCADE,
    stage       TEXT NOT NULL,   -- fact_extraction|entity_extraction|focus_extraction|validation|summarization|profiling|alias|subject_*
    model       TEXT NOT NULL,
    system_prompt TEXT,
    user_prompt TEXT NOT NULL,
    response    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_run  ON pipeline_llm_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_turn ON pipeline_llm_calls(turn_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_stage ON pipeline_llm_calls(stage);
