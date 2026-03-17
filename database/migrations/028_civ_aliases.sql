-- Civ alias mappings: one entity name → one canonical civ
-- Used by detection and the UI resolver.
CREATE TABLE IF NOT EXISTS civ_aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id      INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    alias_name  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_civ_aliases_name
    ON civ_aliases(alias_name);

-- Dismissed false positives: LLM-extracted names that are NOT civs.
-- Prevents them from reappearing in the resolver after each pipeline run.
CREATE TABLE IF NOT EXISTS civ_alias_dismissed (
    alias_name  TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
