-- Migration 025: per-field GM lock
-- Allows the GM to protect individual fields from being overwritten by the pipeline.
-- gm_fields is a JSON array of field names, e.g. ["description", "tags"].
-- The pipeline reads this column before any UPDATE and skips listed fields.

ALTER TABLE entity_entities ADD COLUMN gm_fields TEXT;
ALTER TABLE subject_subjects ADD COLUMN gm_fields TEXT;
