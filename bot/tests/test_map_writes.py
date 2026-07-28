"""The WRITE socle: proposeSpawnPositions (read) + foundSettlement (write).

Enforces the design (docs/map-tools-design.md): the LLM targets by SEMANTIC anchor
(a spawn rank or a named feature), never (q,r); a write validates (no city in the
ocean), applies, logs a `settlement` event, and echoes the new local state with
RELATIVE directions. All through the real dispatch path.
"""
from __future__ import annotations

from bot.map_ingestion import ingest_world
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import dispatch_tool

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "temperature", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "deposit", "encoding": "uint", "bits": 8},
    {"name": "feature", "encoding": "uint", "bits": 8},
    {"name": "flow_accum", "encoding": "float32"},
]
# 4x1: ocean | coast+river (best) | plain | mountain+feature
CELLS = {
    (0, 0): {"elevation": -1000.0, "biome": 0, "temperature": 16.0, "terrain_type": 0, "deposit": 0, "feature": 0, "flow_accum": 0.0},
    (1, 0): {"elevation": 40.0, "biome": 1, "temperature": 16.0, "terrain_type": 1, "deposit": 1, "feature": 0, "flow_accum": 2000.0},
    (2, 0): {"elevation": 150.0, "biome": 1, "temperature": 15.0, "terrain_type": 4, "deposit": 0, "feature": 0, "flow_accum": 0.0},
    (3, 0): {"elevation": 2600.0, "biome": 2, "temperature": -5.0, "terrain_type": 2, "deposit": 0, "feature": 1, "flow_accum": 0.0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 0, "name": "ocean"}, {"id": 1, "name": "coast"},
                           {"id": 2, "name": "mountain"}, {"id": 4, "name": "plain"}],
    "deposits.json": [{"id": 1, "name": "coal_outcrop", "catalog": "coal", "tier": "standard"}],
    "features.json": [{"id": 1, "name": "glacial_cirque", "display_name": "Glacial Cirque",
                       "category": "geological_formations", "description": "A cirque carved by ice."}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 3,
    "grid": {"width": 4, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0, "cell_area_km2": 400.0},
    "resources": {"log_decades": 8.0, "floor01": 1.0 / 255.0, "layers": []},
}


def _seed(db, tmp_path):
    """Returns the ingested map_id — the conftest already seeds OTHER maps, so every
    query below must scope to this one."""
    w = build_world(tmp_path / "w", width=4, height=1, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    return ingest_world(db, w, "Terre")["map_id"]


def _control(db, map_id, q, r):
    return db.execute(
        "SELECT controlling_civ_id FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (map_id, q, r)).fetchone()[0]


def test_propose_renders_ranks_and_the_found_hint(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "proposeSpawnPositions", {"mapName": "Terre"})
    assert "1." in out and "coast" in out          # best spawn = the coastal river
    assert 'at="spawn N"' in out                    # tells the agent HOW to found
    assert "ocean" not in out.lower()               # ocean is never proposed


def test_found_at_spawn_sets_control_logs_event_and_gives_feedback(db, tmp_path):
    map_id = _seed(db, tmp_path)
    out = dispatch_tool(db, "foundSettlement",
                        {"civName": "Confluence", "at": "spawn 1", "mapName": "Terre",
                         "name": "Rivepont"})
    assert "Rivepont" in out and "fondée" in out
    assert "Voisinage" in out and ("E :" in out or "O :" in out)   # relative directions

    # Best spawn is the coastal river province (1,0): control + a settlement event.
    assert _control(db, map_id, 1, 0) == 1           # Confluence = civ id 1
    ev = db.execute(
        "SELECT event_type, description FROM map_cell_events WHERE map_id = ? AND q = 1 AND r = 0 "
        "ORDER BY id DESC LIMIT 1", (map_id,)).fetchone()
    assert ev[0] == "settlement" and "Rivepont" in ev[1]


def test_found_at_a_named_feature(db, tmp_path):
    map_id = _seed(db, tmp_path)
    out = dispatch_tool(db, "foundSettlement",
                        {"civName": "Confluence", "at": "Glacial Cirque", "mapName": "Terre"})
    assert "fondée" in out
    assert _control(db, map_id, 3, 0) == 1           # the feature province (3,0)


def test_found_in_the_ocean_is_refused(db, tmp_path):
    map_id = _seed(db, tmp_path)
    db.execute("UPDATE map_cells SET label = 'Mer du Nord' WHERE map_id = ? AND q = 0 AND r = 0",
               (map_id,))
    db.commit()
    out = dispatch_tool(db, "foundSettlement",
                        {"civName": "Confluence", "at": "Mer du Nord", "mapName": "Terre"})
    assert "mer" in out.lower() and "impossible" in out.lower()
    assert _control(db, map_id, 0, 0) is None       # no write happened


def test_found_with_an_unknown_anchor_points_the_agent(db, tmp_path):
    map_id = _seed(db, tmp_path)
    out = dispatch_tool(db, "foundSettlement",
                        {"civName": "Confluence", "at": "Atlantide", "mapName": "Terre"})
    assert "introuvable" in out.lower()
    assert _control(db, map_id, 1, 0) is None       # nothing placed anywhere
