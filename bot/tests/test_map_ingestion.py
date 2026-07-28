"""Ingest a full-contract Theomen world into a game DB and check the semantic record.

The reader test proves the binary decode; this proves the MAPPING: index→name via
sidecars, the log resource inversion + top-K ranking (SPEC §5), the three water
cases, crop-on-ingest, idempotency, and that the existing read tools still work on
the ingested map (non-regression is a hard constraint of the brief).
"""
from __future__ import annotations

import json

from bot.map_ingestion import ingest_world
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import get_map_overview

# Full contract shape — every field Theomen will ship, byte-aligned.
FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "temperature", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "deposit", "encoding": "uint", "bits": 8},
    {"name": "feature", "encoding": "uint", "bits": 8},
    {"name": "flow_accum", "encoding": "float32"},
    {"name": "lake_depth", "encoding": "float32"},
    {"name": "budget", "encoding": "int", "bits": 8},
    {"name": "res_iron", "encoding": "unorm8"},
    {"name": "res_coal", "encoding": "unorm8"},
]

# (x,y) -> raw per-field values (indices/raws exactly as the decoder reads them).
_P = {"elevation": 100.0, "biome": 1, "temperature": 15.0, "terrain_type": 2,
      "deposit": 0, "feature": 0, "flow_accum": 0.0, "lake_depth": 0.0,
      "budget": 0, "res_iron": 0, "res_coal": 0}
CELLS = {
    (0, 0): {"elevation": -1840.0, "biome": 0, "temperature": 18.4, "terrain_type": 0,
             "deposit": 0, "feature": 0, "flow_accum": 0.0, "lake_depth": 0.0,
             "budget": 0, "res_iron": 0, "res_coal": 0},
    (1, 0): {"elevation": 48.0, "biome": 1, "temperature": 21.7, "terrain_type": 1,
             "deposit": 1, "feature": 0, "flow_accum": 2000.0, "lake_depth": 0.0,
             "budget": 3, "res_iron": 50, "res_coal": 255},
    (2, 0): {"elevation": 2610.0, "biome": 2, "temperature": -4.2, "terrain_type": 3,
             "deposit": 2, "feature": 1, "flow_accum": 1200.0, "lake_depth": 20.0,
             "budget": 6, "res_iron": 250, "res_coal": 0},
    (0, 1): dict(_P), (1, 1): dict(_P), (2, 1): dict(_P),
}

SIDECARS = {
    "terrain_types.json": [
        {"id": 0, "name": "ocean"}, {"id": 1, "name": "coast"},
        {"id": 2, "name": "forest"}, {"id": 3, "name": "mountain"},
    ],
    "deposits.json": [
        {"id": 1, "name": "coal_outcrop", "display_name": "Coal Outcrop", "catalog": "coal",
         "tier": "standard", "formation_type": "exposed_carboniferous_forest"},
        {"id": 2, "name": "rich_iron_ore", "display_name": "Rich Iron Ore", "catalog": "iron",
         "tier": "premium", "formation_type": "banded_iron_formation"},
    ],
    "features.json": [
        {"id": 1, "name": "glacial_cirque", "display_name": "Glacial Cirque",
         "category": "geological_formations",
         "description": "A bowl-shaped valley carved by a glacier."},
    ],
}

WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 42,
    "grid": {"width": 3, "height": 2, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": True, "clamp_y": True},
    "elevation": {"datum": "relative_to_sea_level", "sea_level_value": 0.0, "unit": "m"},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0,
                   "cell_area_km2": 400.0},
    "resources": {
        "encoding": "log10_per_type", "log_decades": 8.0, "floor01": 1.0 / 255.0,
        "layers": [
            {"field": "res_iron", "type": "iron", "max_mass": 3.71e17},
            {"field": "res_coal", "type": "coal", "max_mass": 9.02e15},
        ],
    },
    "sidecars": ["biomes.json", "terrain_types.json", "deposits.json", "features.json"],
}


def _world(tmp_path):
    return build_world(
        tmp_path / "w", width=3, height=2, chunk=4, fields=FIELDS,
        cell_fn=lambda gx, gy, name: CELLS[(gx, gy)][name],
        world_json=WORLD_JSON, sidecars=SIDECARS,
    )


def _cells_by_qr(db, map_id):
    rows = db.execute(
        "SELECT q, r, terrain_type, metadata FROM map_cells WHERE map_id = ?", (map_id,)
    ).fetchall()
    return {(q, r): (terr, json.loads(meta) if meta else {}) for q, r, terr, meta in rows}


def test_ingest_populates_map_and_metadata(db, tmp_path):
    res = ingest_world(db, _world(tmp_path), "Terre du Milieu")
    assert res["cells"] == 6

    mrow = db.execute(
        "SELECT grid_type, grid_cols, grid_rows, metadata FROM map_maps WHERE id = ?",
        (res["map_id"],)).fetchone()
    assert mrow[0] == "square" and (mrow[1], mrow[2]) == (3, 2)
    mmeta = json.loads(mrow[3])
    assert mmeta["cell_km"] == 20.0 and mmeta["wrap_x"] is True
    assert mmeta["biome_palette"]["temperate_forest"] == "#3f8f43"

    cells = _cells_by_qr(db, res["map_id"])

    # Ocean cell: terrain from elevation, no biome, no deposit, no resources.
    terr, meta = cells[(0, 0)]
    assert terr == "ocean"
    assert meta["water"]["is_ocean"] is True
    assert "biome" not in meta and "deposit" not in meta and "resource_potential" not in meta

    # River + coal deposit + iron/coal potential (coal ranks first — unambiguous raws).
    terr, meta = cells[(1, 0)]
    assert terr == "coast" and meta["biome"] == "temperate_forest"
    assert meta["water"]["is_river"] is True
    assert meta["water"]["river_catchment_km2"] == 800000   # 2000 * 400
    assert meta["deposit"]["name"] == "coal_outcrop" and meta["deposit"]["tier"] == "standard"
    assert meta["deposit"]["formation_type"] == "exposed_carboniferous_forest"
    assert meta["resource_potential"] == ["coal", "iron"]
    assert meta["budget_score"] == 3 and meta["temperature_c"] == 21.7

    # Mountain + lake + premium iron + a feature carrying GM prose.
    terr, meta = cells[(2, 0)]
    assert terr == "mountain" and meta["biome"] == "alpine"
    assert meta["water"]["is_lake"] is True and meta["water"]["lake_depth_m"] == 20.0
    assert meta["water"]["is_river"] is False                # 1200 < 1500 threshold
    assert meta["deposit"]["name"] == "rich_iron_ore"
    assert meta["feature"]["name"] == "glacial_cirque"
    assert "glacier" in meta["feature"]["description"]
    assert meta["resource_potential"] == ["iron"]            # coal absent (raw 0)
    assert meta["budget_score"] == 6


def test_existing_read_tool_still_works_on_ingested_map(db, tmp_path):
    res = ingest_world(db, _world(tmp_path), "Terre du Milieu")
    out = get_map_overview(db, res["map_id"], "Terre du Milieu")
    assert "Terre du Milieu" in out
    assert "mountain" in out and "coast" in out   # terrains render in the overview table


def test_reingest_is_idempotent(db, tmp_path):
    w = _world(tmp_path)
    r1 = ingest_world(db, w, "Terre du Milieu")
    r2 = ingest_world(db, w, "Terre du Milieu")
    assert r1["map_id"] == r2["map_id"]            # same map, updated in place
    n = db.execute("SELECT COUNT(*) FROM map_cells WHERE map_id = ?", (r1["map_id"],)).fetchone()[0]
    assert n == 6                                  # replaced, not doubled
    nmaps = db.execute("SELECT COUNT(*) FROM map_maps WHERE name = 'Terre du Milieu'").fetchone()[0]
    assert nmaps == 1


def test_window_crop_only_ingests_the_window(db, tmp_path):
    # Window = the right 2x2 block (global x in [1,3)); local q = gx-1.
    res = ingest_world(db, _world(tmp_path), "Fenetre", window=(1, 0, 2, 2))
    assert res["cells"] == 4
    cells = _cells_by_qr(db, res["map_id"])
    assert set(cells) == {(0, 0), (1, 0), (0, 1), (1, 1)}
    assert cells[(0, 0)][0] == "coast"      # was global (1,0)
    assert cells[(1, 0)][0] == "mountain"   # was global (2,0)
