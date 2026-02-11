-- Migration 002: Add structured summary fields to turn_turns
-- These columns store the full LLM summary output previously discarded.

ALTER TABLE turn_turns ADD COLUMN detailed_summary TEXT;
ALTER TABLE turn_turns ADD COLUMN key_events TEXT;
ALTER TABLE turn_turns ADD COLUMN choices_made TEXT;
