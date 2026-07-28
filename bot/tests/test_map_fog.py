"""Fog of war (V2, spatial): groundCivTerrain reveals only DISCOVERED provinces.

A civ knows its cradle (founding discovers seat + immediate ring), the far ring stays
hidden until explored; discoverAround lifts the fog; fog=false is GM omniscience.
Content-knowledge gating (no coal in the neolithic) is the parked "feature discover"
debt — this is spatial only.
"""
from __future__ import annotations

from bot.map_ingestion import ingest_world
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import dispatch_tool

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "flow_accum", "encoding": "float32"},
]
# 5x1: plain | plain | coast+river (best spawn = seat) | plain | plain
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "flow_accum": 0.0},
    (1, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "flow_accum": 0.0},
    (2, 0): {"elevation": 40.0, "biome": 1, "terrain_type": 1, "flow_accum": 2000.0},
    (3, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "flow_accum": 0.0},
    (4, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "flow_accum": 0.0},
}
SIDECARS = {"terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 4, "name": "plain"}]}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 17,
    "grid": {"width": 5, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "cell_area_km2": 400.0},
    "resources": {"layers": []},
}


def _found(db, tmp_path):
    # The conftest seeds Confluence a seat on another map; clear it so grounding (which
    # walks ALL of a civ's seats) is isolated to the Terre map under test.
    db.execute("UPDATE map_cells SET controlling_civ_id = NULL WHERE controlling_civ_id = 1")
    db.commit()
    w = build_world(tmp_path / "w", width=5, height=1, chunk=8, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    ingest_world(db, w, "Terre")
    dispatch_tool(db, "foundSettlement",
                  {"civName": "Confluence", "at": "spawn 1", "mapName": "Terre"})  # seat = (2,0)


def _ground(db, **kw):
    return dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 2, **kw})


def test_fog_hides_undiscovered_far_provinces(db, tmp_path):
    _found(db, tmp_path)
    out = _ground(db)                              # fog on by default
    assert "à 1 province" in out                   # (1,0)/(3,0): discovered on founding
    assert "à 2 provinces" not in out              # (0,0)/(4,0): NOT yet explored
    assert "inexplorée" in out


def test_fog_false_is_gm_omniscience(db, tmp_path):
    _found(db, tmp_path)
    out = _ground(db, fog=False)
    assert "à 2 provinces" in out                  # the whole radius is revealed
    assert "inexplorée" not in out


def test_discover_around_lifts_the_fog(db, tmp_path):
    _found(db, tmp_path)
    exp = dispatch_tool(db, "discoverAround",
                        {"civName": "Confluence", "radius": 2, "mapName": "Terre"})
    assert "découvre" in exp
    out = _ground(db)                              # fog on, but now explored
    assert "à 2 provinces" in out and "inexplorée" not in out
