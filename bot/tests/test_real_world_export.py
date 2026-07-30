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

_DEFAULT = r"C:\Users\alexi\Documents\projects\Gamedesigner\theomen\blog\world_aurelm_seed42.world"
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


def test_header_reads_the_producer_block_and_sidecars():
    """The v2 export puts business metadata in manifest["producer"] (not world.json)
    and ships wrapped sidecars — both real-data shapes the fixtures mirror. v2 merged
    features+deposits into a single elements.json point-budget registry."""
    h = read_world(_WORLD).header
    assert h.width > 1000 and h.height > 500          # a real planet
    assert h.cell_km == 20.0 and h.wrap_x is True      # from the producer block
    assert len(h.biomes) >= 20                          # biomes.json {"biomes":[...]}
    assert h.resource_layers                            # res_ max_mass for the inversion
    # v2: the single elements.json registry (deposits + landmarks + constraints).
    assert len(h.name_maps.get("elements", {})) >= 100


def test_ingests_a_land_window_with_full_semantics():
    """Ingest a real LAND window and prove the whole v2 semantic path resolves on real
    data: terrain + biome names, and a point-budget element SET whose signed points sum
    to budget_score (Theomen's core v2 contract)."""
    import json
    conn = sqlite3.connect(":memory:")
    conn.executescript(_MAP_SCHEMA)
    res = ingest_world(conn, _WORLD, "Seed42", window=(9, 30, 8, 8))  # a coastal-plain region
    assert res["cells"] == 64

    mmeta = json.loads(conn.execute(
        "SELECT metadata FROM map_maps WHERE id = ?", (res["map_id"],)).fetchone()[0])
    assert mmeta["cell_km"] == 20.0 and mmeta["wrap_x"] is True

    metas = [json.loads(m) for (m,) in conn.execute(
        "SELECT metadata FROM map_cells WHERE map_id = ?", (res["map_id"],)) if m]
    assert any(mt.get("biome") for mt in metas), "biome names resolve on real data"

    with_elements = [mt for mt in metas if mt.get("elements")]
    assert with_elements, "a point-budget element set resolves in the window"
    # Every resolved element carries the v2 facts (family in the known trichotomy,
    # signed points, hidden_level), and — the invariant — the points sum to the budget.
    for mt in with_elements:
        els = mt["elements"]
        assert all(e.get("family") in ("deposit", "landmark", "constraint") for e in els)
        assert all(isinstance(e.get("points"), int) for e in els)
        if isinstance(mt.get("budget_score"), int):
            assert sum(e["points"] for e in els) == mt["budget_score"], \
                "element points must sum to budget_score (v2 point-budget contract)"
