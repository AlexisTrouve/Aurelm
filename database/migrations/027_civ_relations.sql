-- Migration 027: inter-civ relations tracking
--
-- civ_mentions  — one row per "civ B was mentioned in civ A's turn"
--                 detected automatically from entity_mentions (type=civilization)
-- civ_relations — LLM-profiled unilateral opinion A→B
--                 (A→B and B→A are distinct rows — perspectives can differ)

CREATE TABLE IF NOT EXISTS civ_mentions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    target_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    turn_id         INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
    context         TEXT,   -- turn summary used as LLM input context
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One mention-per-turn per pair (dedup at insert time)
CREATE UNIQUE INDEX IF NOT EXISTS idx_civ_mentions_unique
    ON civ_mentions(source_civ_id, target_civ_id, turn_id);

CREATE TABLE IF NOT EXISTS civ_relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    target_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    opinion         TEXT NOT NULL DEFAULT 'unknown',
    -- allied | friendly | neutral | suspicious | hostile | unknown
    description     TEXT,       -- LLM narrative summary of the relationship
    treaties        TEXT,       -- JSON array of treaty/agreement names detected
    last_turn_id    INTEGER REFERENCES turn_turns(id),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_civ_id, target_civ_id)
);
