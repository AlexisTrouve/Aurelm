"""Validate the reader + ingestion against a REAL Theomen `.world` export.

Opt-in: skips unless a real export is present (env AURELM_WORLD_DIR, or the default
dev path). Fixtures are spec-faithful but the encoder/decoder share the same reading
of the spec — only a real file settles ambiguities. THIS test is what caught the
chunk-coord bug (coord.x is a CHUNK INDEX, not a cell origin): the fixtures encoded
the same wrong assumption and passed; the real 384x256 export collapsed to x<=129.

The available export predates theomen.world.v1 (elevation + ~52 res_ layers, no
biome / world.json / sidecars), so it also exercises graceful degradation on a
PARTIAL export.
"""
from __future__ import annotations

import os
import sqlite3

import pytest

from bot.map_ingestion import ingest_world
from bot.world_reader import read_world

_DEFAULT = r"C:\Users\alexi\Documents\projects\theomen-worlds\seed42.world"
_WORLD = os.environ.get("AURELM_WORLD_DIR", _DEFAULT)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(_WORLD, "chunks")),
    reason=f"no real .world export at {_WORLD} (set AURELM_WORLD_DIR)",
)

_MAP_SCHEMA = """
CREATE TABLE map_maps (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
  image_path TEXT, grid_type TEXT DEFAULT 'hex', grid_cols INTEGER, grid_rows INTEGER,
  parent_map_id INTEGER, parent_cell_q INTEGER, parent_cell_r INTEGER, metadata TEXT,
  created_at TEXT);
CREATE TABLE map_cells (map_id INTEGER, q INTEGER, r INTEGER, terrain_type TEXT DEFAULT 'plain',
  controlling_civ_id INTEGER, entity_id INTEGER, label TEXT, child_map_id INTEGER, metadata TEXT,
  PRIMARY KEY (map_id, q, r));
"""


def test_decodes_the_whole_real_grid_without_collision():
    w = read_world(_WORLD)
    h = w.header
    xs, ys, n = set(), set(), 0
    emin, emax = 1e18, -1e18
    for c in w.cells():
        xs.add(c["x"]); ys.add(c["y"]); n += 1
        e = c.get("elevation")
        if e is not None:
            emin, emax = min(emin, e), max(emax, e)
    # Every cell placed exactly once across the FULL grid (the chunk-index regression).
    assert (min(xs), max(xs)) == (0, h.width - 1)
    assert (min(ys), max(ys)) == (0, h.height - 1)
    assert n == h.width * h.height == len(xs) * len(ys)
    # Elevation is physical: real ocean trenches and mountains, not garbage floats.
    assert emin < -1000 and emax > 3000


def test_ingests_a_window_of_the_real_export():
    conn = sqlite3.connect(":memory:")
    conn.executescript(_MAP_SCHEMA)
    res = ingest_world(conn, _WORLD, "Seed42", window=(0, 0, 8, 8))
    assert res["cells"] == 64                       # 8x8, no collisions

    rows = conn.execute(
        "SELECT terrain_type, metadata FROM map_cells WHERE map_id = ?", (res["map_id"],)
    ).fetchall()
    assert all(t for t, _ in rows), "every province has a terrain"
    # Partial export: no biome/resources, but elevation + water regime always land.
    import json
    for _, meta_json in rows:
        meta = json.loads(meta_json)
        assert "elevation_m" in meta and "water" in meta
