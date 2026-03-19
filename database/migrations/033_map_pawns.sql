-- Migration 033: Map entity pawns
-- Movable entity tokens on the map. One pawn per entity per map.

CREATE TABLE IF NOT EXISTS map_entity_pawns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id)       ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    entity_id   INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    -- Optional custom icon from the asset library
    asset_id    INTEGER REFERENCES map_assets(id) ON DELETE SET NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    -- An entity can only be on one cell per map
    UNIQUE(map_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_map_pawns_cell
    ON map_entity_pawns(map_id, q, r);
