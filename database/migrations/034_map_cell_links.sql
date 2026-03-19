-- Migration 034: Map cell links
-- Entities and subjects can be attached to map cells (many-to-many).
-- Notes gain a map_id / map_cell_q / map_cell_r FK for cell-level annotations.

CREATE TABLE IF NOT EXISTS map_cell_entities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id)        ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    entity_id   INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(map_id, q, r, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_map_cell_entities_cell   ON map_cell_entities(map_id, q, r);
CREATE INDEX IF NOT EXISTS idx_map_cell_entities_entity ON map_cell_entities(entity_id);

CREATE TABLE IF NOT EXISTS map_cell_subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id)          ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    subject_id  INTEGER NOT NULL REFERENCES subject_subjects(id)  ON DELETE CASCADE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(map_id, q, r, subject_id)
);
CREATE INDEX IF NOT EXISTS idx_map_cell_subjects_cell    ON map_cell_subjects(map_id, q, r);
CREATE INDEX IF NOT EXISTS idx_map_cell_subjects_subject ON map_cell_subjects(subject_id);

-- Notes attached to a specific map cell
ALTER TABLE notes ADD COLUMN map_id      INTEGER REFERENCES map_maps(id) ON DELETE CASCADE;
ALTER TABLE notes ADD COLUMN map_cell_q  INTEGER;
ALTER TABLE notes ADD COLUMN map_cell_r  INTEGER;
