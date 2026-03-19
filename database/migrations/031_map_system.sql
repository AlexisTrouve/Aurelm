-- Migration 031: Map system
-- Interactive map layers with hex/square grid, terrain types, and cell event history.

CREATE TABLE IF NOT EXISTS map_maps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    image_path      TEXT,
    -- Grid type: 'hex' (pointy-top) or 'square'
    grid_type       TEXT    NOT NULL DEFAULT 'hex' CHECK(grid_type IN ('hex', 'square')),
    grid_cols       INTEGER NOT NULL DEFAULT 20,
    grid_rows       INTEGER NOT NULL DEFAULT 15,
    -- Self-ref: this map is a drill-down from a cell in parent_map_id
    parent_map_id   INTEGER REFERENCES map_maps(id) ON DELETE SET NULL,
    parent_cell_q   INTEGER,
    parent_cell_r   INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS map_cells (
    map_id              INTEGER NOT NULL REFERENCES map_maps(id) ON DELETE CASCADE,
    q                   INTEGER NOT NULL,
    r                   INTEGER NOT NULL,
    -- Terrain types for painter color mapping
    terrain_type        TEXT    NOT NULL DEFAULT 'plain',
    controlling_civ_id  INTEGER REFERENCES civ_civilizations(id) ON DELETE SET NULL,
    entity_id           INTEGER REFERENCES entity_entities(id) ON DELETE SET NULL,
    label               TEXT,
    -- Child map: clicking this cell drills into child_map_id
    child_map_id        INTEGER REFERENCES map_maps(id) ON DELETE SET NULL,
    -- JSON blob for arbitrary extra data (resources, notes, etc.)
    metadata            TEXT,
    PRIMARY KEY (map_id, q, r)
);

CREATE TABLE IF NOT EXISTS map_cell_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id) ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    turn_id     INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL,
    description TEXT    NOT NULL,
    -- Event type: settlement|battle|discovery|diplomatic|note|migration|disaster
    event_type  TEXT    NOT NULL DEFAULT 'note',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Fast lookup: events for a specific cell
CREATE INDEX IF NOT EXISTS idx_map_cell_events_cell
    ON map_cell_events(map_id, q, r);

-- Fast lookup: all cells controlled by a given civ
CREATE INDEX IF NOT EXISTS idx_map_cells_civ
    ON map_cells(controlling_civ_id) WHERE controlling_civ_id IS NOT NULL;

-- Fast lookup: cell linked to a specific entity
CREATE INDEX IF NOT EXISTS idx_map_cells_entity
    ON map_cells(entity_id) WHERE entity_id IS NOT NULL;
