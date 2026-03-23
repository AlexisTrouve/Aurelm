-- Granular pipeline progress: LLM call tracking per stage
ALTER TABLE pipeline_progress ADD COLUMN stage_name TEXT;
ALTER TABLE pipeline_progress ADD COLUMN llm_calls_done INTEGER DEFAULT 0;
ALTER TABLE pipeline_progress ADD COLUMN llm_calls_total INTEGER DEFAULT 0;
ALTER TABLE pipeline_progress ADD COLUMN turn_number INTEGER;
