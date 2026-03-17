-- Migration 026: per-field GM lock on turns
-- Same pattern as migration 025 (entities/subjects).
ALTER TABLE turn_turns ADD COLUMN gm_fields TEXT;
