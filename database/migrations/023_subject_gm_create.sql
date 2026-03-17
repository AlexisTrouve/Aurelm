-- Migration 023: make source_turn_id nullable in subject_subjects
-- to support GM-created subjects that are not tied to a specific pipeline turn.
-- SQLite doesn't support ALTER COLUMN — recreate the table.

PRAGMA foreign_keys = OFF;

CREATE TABLE subject_subjects_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id      INTEGER NOT NULL,
    source_turn_id INTEGER,           -- nullable: NULL for GM-created subjects
    direction   TEXT NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    source_quote TEXT,
    category    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    tags        TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

INSERT INTO subject_subjects_new
    SELECT id, civ_id, source_turn_id, direction, title, description,
           source_quote, category, status, tags, created_at, updated_at
    FROM subject_subjects;

DROP TABLE subject_subjects;
ALTER TABLE subject_subjects_new RENAME TO subject_subjects;

PRAGMA foreign_keys = ON;
