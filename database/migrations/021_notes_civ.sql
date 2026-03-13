-- Migration 021: add civ_id FK to notes table
-- Allows GM to attach notes directly to a civilization (not just entity/subject/turn).

ALTER TABLE notes ADD COLUMN civ_id INTEGER REFERENCES civ_civilizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_notes_civ ON notes(civ_id) WHERE civ_id IS NOT NULL;
