-- Migration 039: agent memory store
-- The agent writes durable memories for ITSELF from GM feedback (corrections,
-- world rulings, answer preferences) via the saveMemory tool, and recalls the
-- relevant ones per request. Keyed by (mem_key, civ_id) so re-saving the same key
-- UPDATES instead of duplicating — a memory it maintains, not an append-log.
--   mem_type: 'fact' (a world ruling/correction, recalled by relevance) or
--             'preference' (how to answer, always injected).
--   civ_id NULL = global memory.
--   source_turn: optional "as of turn N" anchor (used by a later increment).
--   active=0 = forgotten (kept for the review trail, not recalled).

CREATE TABLE IF NOT EXISTS agent_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mem_key     TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    content     TEXT    NOT NULL DEFAULT '',
    civ_id      INTEGER REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    keywords    TEXT    NOT NULL DEFAULT '',
    mem_type    TEXT    NOT NULL DEFAULT 'fact',
    source_turn INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_active ON agent_memory(active) WHERE active = 1;
CREATE INDEX IF NOT EXISTS idx_agent_memory_civ    ON agent_memory(civ_id) WHERE civ_id IS NOT NULL;
