-- Migration 036: per-civ province discovery (fog of war, spatial)
-- WHY: grounding must respect what a civ has actually EXPLORED. At turn 0 a neolithic
-- civ knows only its own province, not a 40 km neighbourhood, so groundCivTerrain must
-- reveal only discovered provinces. Discovery is per-civ (each knows different things),
-- granted on founding/expansion and grown by exploration.
-- NOTE the runner splits on the semicolon, so keep these comments free of them.
-- DEBT (feature discover): this is SPATIAL discovery only -- seeing a province. Knowing
-- what a province CONTAINS (its coal, etc.) is tech-gated (no coal in the neolithic) and
-- is a separate, smarter mechanic, parked for later.

CREATE TABLE IF NOT EXISTS map_cell_discovery (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id)          ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    civ_id      INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(map_id, q, r, civ_id)
);

CREATE INDEX IF NOT EXISTS idx_map_discovery_civ ON map_cell_discovery(map_id, civ_id);
