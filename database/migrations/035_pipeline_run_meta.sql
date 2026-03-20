-- Store pipeline run metadata: which version/model/provider was used
ALTER TABLE pipeline_runs ADD COLUMN extraction_version TEXT;
ALTER TABLE pipeline_runs ADD COLUMN llm_model TEXT;
ALTER TABLE pipeline_runs ADD COLUMN llm_provider TEXT;
