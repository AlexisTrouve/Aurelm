-- Migration 015: add source_quote to subjects and resolutions
--
-- source_quote = verbatim phrase from the source text extracted by the LLM
-- Used to auto-highlight the relevant passage when navigating from subject detail to a turn.

ALTER TABLE subject_subjects ADD COLUMN source_quote TEXT;
ALTER TABLE subject_resolutions ADD COLUMN source_quote TEXT;
