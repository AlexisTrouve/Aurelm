-- Migration 019: notes system
-- Allows GM to annotate entities, subjects, and turns with titled notes.
-- Exactly one of entity_id / subject_id / turn_id must be non-null per row.

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id   INTEGER REFERENCES entity_entities(id) ON DELETE CASCADE,
    subject_id  INTEGER REFERENCES subject_subjects(id) ON DELETE CASCADE,
    turn_id     INTEGER REFERENCES turn_turns(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_notes_entity  ON notes(entity_id)  WHERE entity_id  IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_subject ON notes(subject_id) WHERE subject_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_turn    ON notes(turn_id)    WHERE turn_id    IS NOT NULL;
