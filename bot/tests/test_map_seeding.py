"""Seeding a game onto an ingested world: propose spawn provinces + place a civ.

Builds a world where one province is clearly the best start (coast + river +
temperate) and checks the ranking puts it first, oceans are never proposed, and
placing a civ there is visible through the existing getTerritory tool.
"""
from __future__ import annotations

import json

from bot.map_ingestion import ingest_world
from bot.map_seeding import place_civ, propose_spawn_positions
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import get_territory

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "temperature", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "flow_accum", "encoding": "float32"},
]
# terrain ids: 0 ocean,1 coast,2 mountain,3 desert,4 plain,5 grassland
SIDECARS = {"terrain_types.json": [
    {"id": 0, "name": "ocean"}, {"id": 1, "name": "coast"}, {"id": 2, "name": "mountain"},
    {"id": 3, "name": "desert"}, {"id": 4, "name": "plain"}, {"id": 5, "name": "grassland"},
]}
CELLS = {
    (0, 0): {"elevation": -1000.0, "biome": 0, "temperature": 16.0, "terrain_type": 0, "flow_accum": 0.0},
    (1, 0): {"elevation": 40.0, "biome": 1, "temperature": 16.0, "terrain_type": 1, "flow_accum": 2000.0},
    (2, 0): {"elevation": 2600.0, "biome": 2, "temperature": -5.0, "terrain_type": 2, "flow_accum": 0.0},
    (0, 1): {"elevation": 200.0, "biome": 1, "temperature": 40.0, "terrain_type": 3, "flow_accum": 0.0},
    (1, 1): {"elevation": 150.0, "biome": 1, "temperature": 15.0, "terrain_type": 4, "flow_accum": 0.0},
    (2, 1): {"elevation": 120.0, "biome": 1, "temperature": 14.0, "terrain_type": 5, "flow_accum": 0.0},
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 7,
    "grid": {"width": 3, "height": 2, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": True, "clamp_y": True},
    "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0, "cell_area_km2": 400.0},
    "resources": {"log_decades": 8.0, "floor01": 1.0 / 255.0, "layers": []},
}


def _seed(db, tmp_path, name="Terre"):
    w = build_world(tmp_path / "w", width=3, height=2, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    ingest_world(db, w, name)
    return name


def test_best_province_ranks_first_and_oceans_are_excluded(db, tmp_path):
    name = _seed(db, tmp_path)
    picks = propose_spawn_positions(db, name, n=3)

    assert (picks[0]["q"], picks[0]["r"]) == (1, 0), \
        f"coast+river+temperate must win, got {picks}"
    assert picks[0]["terrain"] == "coast"
    assert any("fleuve" in w for w in picks[0]["why"])       # the WHY is surfaced
    # No ocean province is ever proposed.
    assert all(p["terrain"] != "ocean" for p in picks)
    assert (0, 0) not in {(p["q"], p["r"]) for p in picks}


def test_min_spacing_spreads_the_picks(db, tmp_path):
    name = _seed(db, tmp_path)
    picks = propose_spawn_positions(db, name, n=3, min_spacing=2)
    for i, a in enumerate(picks):
        for b in picks[i + 1:]:
            assert max(abs(a["q"] - b["q"]), abs(a["r"] - b["r"])) >= 2, \
                "spaced picks must be at least 2 provinces apart"


def test_place_civ_shows_up_in_get_territory(db, tmp_path):
    name = _seed(db, tmp_path)
    best = propose_spawn_positions(db, name, n=1)[0]
    res = place_civ(db, "Confluence", name, best["q"], best["r"])

    got = db.execute(
        "SELECT controlling_civ_id FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
        (res["map_id"], best["q"], best["r"])).fetchone()
    assert got[0] == res["civ_id"]

    # The existing read tool must see the placement on the new map (non-regression).
    out = get_territory(db, res["civ_id"], "Civilisation de la Confluence")
    assert name in out
