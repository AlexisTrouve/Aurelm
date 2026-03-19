-- Migration 032: Map assets
-- Asset library (WebP blobs) + per-cell asset placement with z_order slots (max 7).

CREATE TABLE IF NOT EXISTS map_assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    -- WebP encoded bytes at user-defined resolution
    data            BLOB    NOT NULL,
    original_format TEXT    NOT NULL DEFAULT 'unknown',
    stored_width    INTEGER NOT NULL,
    stored_height   INTEGER NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS map_cell_assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id)   ON DELETE CASCADE,
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    asset_id    INTEGER NOT NULL REFERENCES map_assets(id) ON DELETE CASCADE,
    -- Slot index 0-6: determines icon position within the cell
    z_order     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    -- Same asset can only appear once per cell
    UNIQUE(map_id, q, r, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_map_cell_assets_cell
    ON map_cell_assets(map_id, q, r);

CREATE INDEX IF NOT EXISTS idx_map_cell_assets_asset
    ON map_cell_assets(asset_id);
