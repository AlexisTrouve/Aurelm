"""Semantic spatial reads: findNearest + whatIsBetween.

Both hide the geometry (Chebyshev distance, Bresenham line) and answer in relative
directions + province counts — the GM's real questions ("do the Confluents have iron
nearby?", "is there a mountain range between them?"). Via the real dispatch path.
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
    {"name": "element_count", "encoding": "uint", "bits": 8},
    {"name": "element_0", "encoding": "uint", "bits": 16},
    {"name": "flow_accum", "encoding": "float32"},
]
# 5x1: A@plain | mountain | coast+iron | mountain | B@plain
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "temperature": 15.0, "terrain_type": 4, "element_count": 0, "element_0": 0, "flow_accum": 0.0},
    (1, 0): {"elevation": 2600.0, "biome": 2, "temperature": 0.0, "terrain_type": 2, "element_count": 0, "element_0": 0, "flow_accum": 0.0},
    (2, 0): {"elevation": 50.0, "biome": 1, "temperature": 16.0, "terrain_type": 1, "element_count": 1, "element_0": 1, "flow_accum": 0.0},
    (3, 0): {"elevation": 2500.0, "biome": 2, "temperature": 0.0, "terrain_type": 2, "element_count": 0, "element_0": 0, "flow_accum": 0.0},
    (4, 0): {"elevation": 120.0, "biome": 1, "temperature": 15.0, "terrain_type": 4, "element_count": 0, "element_0": 0, "flow_accum": 0.0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 2, "name": "mountain"}, {"id": 4, "name": "plain"}],
    "elements.json": [{"id": 1, "name": "rich_iron_ore", "display_name": "Rich Iron Ore",
                       "family": "deposit", "category": "iron", "points": 2, "hidden_level": 0}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 5,
    "grid": {"width": 5, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0, "cell_area_km2": 400.0},
    "resources": {"log_decades": 8.0, "floor01": 1.0 / 255.0, "layers": []},
}


def _seed(db, tmp_path):
    w = build_world(tmp_path / "w", width=5, height=1, chunk=8, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    mid = ingest_world(db, w, "Terre")["map_id"]
    db.execute("UPDATE map_cells SET controlling_civ_id = 1 WHERE map_id = ? AND q = 0 AND r = 0", (mid,))
    db.execute("UPDATE map_cells SET controlling_civ_id = 2 WHERE map_id = ? AND q = 4 AND r = 0", (mid,))
    db.commit()
    return mid


def test_find_nearest_resource_from_a_civ(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "findNearest",
                        {"from": "Confluence", "what": "iron", "mapName": "Terre"})
    assert "Rich Iron Ore" in out                # matched by element category "iron"
    assert "E à 2 provinces" in out              # direction + distance, no (q,r)


def test_find_nearest_terrain(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "findNearest",
                        {"from": "Confluence", "what": "mountain", "mapName": "Terre"})
    assert "E à 1 province" in out               # the mountain at (1,0)


def test_find_nearest_none(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "findNearest",
                        {"from": "Confluence", "what": "gold", "mapName": "Terre"})
    assert "Rien correspondant" in out


def test_what_is_between_reports_the_mountain_barrier(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "whatIsBetween",
                        {"civA": "Confluence", "civB": "Cheveux de Sang", "mapName": "Terre"})
    assert "Distance : 4 provinces" in out
    assert "mountain" in out
    assert "Barrière" in out                     # the two mountains between them


def test_what_is_between_needs_both_placed(db, tmp_path):
    mid = _seed(db, tmp_path)
    db.execute("UPDATE map_cells SET controlling_civ_id = NULL WHERE map_id = ? AND q = 4", (mid,))
    db.commit()
    out = dispatch_tool(db, "whatIsBetween",
                        {"civA": "Confluence", "civB": "Cheveux de Sang", "mapName": "Terre"})
    assert "pas placée" in out
