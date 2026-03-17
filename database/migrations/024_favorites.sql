-- Migration 024: user favorites — entities, subjects, turns

CREATE TABLE IF NOT EXISTS user_favorites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,       -- 'entity' | 'subject' | 'turn'
    entity_id   INTEGER,
    subject_id  INTEGER,
    turn_id     INTEGER,
    civ_id      INTEGER,             -- denormalized for fast filter
    created_at  TEXT NOT NULL
);

-- Unique index per type — prevents duplicate favorites
CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_entity
    ON user_favorites(entity_id)  WHERE entity_id  IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_subject
    ON user_favorites(subject_id) WHERE subject_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_turn
    ON user_favorites(turn_id)    WHERE turn_id    IS NOT NULL;
