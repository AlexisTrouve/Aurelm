-- Migration 040: links from an agent memory to database articles
-- A memory can point at the entities / turns / subjects it concerns, so the agent can
-- drill down (getEntityDetail...) and the GM can click through in the review UI.
-- Exactly one of entity_id / subject_id / turn_id is set per row.
--
-- NOTE on entity links: entity ids are NOT stable. alias_resolver merges entities and
-- deactivates the secondary, so these links are redirected to the surviving entity in
-- the same pass that redirects mentions and relations. Without that they would rot
-- onto dead articles.

CREATE TABLE IF NOT EXISTS agent_memory_links (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id  INTEGER NOT NULL REFERENCES agent_memory(id)      ON DELETE CASCADE,
    entity_id  INTEGER          REFERENCES entity_entities(id)   ON DELETE CASCADE,
    subject_id INTEGER          REFERENCES subject_subjects(id)  ON DELETE CASCADE,
    turn_id    INTEGER          REFERENCES turn_turns(id)        ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_links_memory ON agent_memory_links(memory_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_links_entity ON agent_memory_links(entity_id) WHERE entity_id IS NOT NULL;
