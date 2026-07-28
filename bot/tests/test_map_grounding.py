"""groundCivTerrain: the structured local terrain served to the Demiurgos GM.

Ingest a small rich world, place a civ, and assert the grounding (via the real
dispatch path — how an MCP consumer reaches it) renders the seat + the ring of
provinces with biome, water regime, graded deposits, resource potential, and the
feature prose Theomen ships. 1 cell = 1 province (empire-scale).
"""
from __future__ import annotations

from bot.map_ingestion import ingest_world
from bot.map_seeding import place_civ
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
    {"name": "res_iron", "encoding": "unorm8"},
    {"name": "res_coal", "encoding": "unorm8"},
]
CELLS = {
    (0, 0): {"elevation": 120.0, "biome": 1, "temperature": 15.0, "terrain_type": 4,
             "deposit": 0, "feature": 0, "flow_accum": 0.0, "res_iron": 0, "res_coal": 0},
    (1, 0): {"elevation": 40.0, "biome": 1, "temperature": 16.0, "terrain_type": 1,
             "deposit": 1, "feature": 0, "flow_accum": 2000.0, "res_iron": 50, "res_coal": 255},
    (2, 0): {"elevation": 2600.0, "biome": 2, "temperature": -5.0, "terrain_type": 2,
             "deposit": 2, "feature": 1, "flow_accum": 0.0, "res_iron": 250, "res_coal": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 2, "name": "mountain"},
                           {"id": 4, "name": "plain"}],
    "deposits.json": [
        {"id": 1, "name": "coal_outcrop", "catalog": "coal", "tier": "standard",
         "formation_type": "exposed_carboniferous_forest"},
        {"id": 2, "name": "rich_iron_ore", "catalog": "iron", "tier": "premium",
         "formation_type": "banded_iron_formation"},
    ],
    "features.json": [{"id": 1, "name": "glacial_cirque", "display_name": "Glacial Cirque",
                       "category": "geological_formations",
                       "description": "A bowl-shaped valley carved by a glacier."}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 1,
    "grid": {"width": 3, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": True, "clamp_y": True},
    "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0, "cell_area_km2": 400.0},
    "resources": {"log_decades": 8.0, "floor01": 1.0 / 255.0,
                  "layers": [{"field": "res_iron", "type": "iron", "max_mass": 3.71e17},
                             {"field": "res_coal", "type": "coal", "max_mass": 9.02e15}]},
}


def _placed(db, tmp_path):
    w = build_world(tmp_path / "w", width=3, height=1, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    ingest_world(db, w, "Terre")
    place_civ(db, "Confluence", "Terre", 1, 0)   # seat at the coastal river province


def test_grounding_describes_seat_and_ring(db, tmp_path):
    _placed(db, tmp_path)
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 1})

    assert "Terrain local" in out
    assert "(siège)" in out                      # the seat province is marked
    # Neighbours are given by RELATIVE direction + distance, never raw (q,r).
    assert "O à 1 province" in out and "E à 1 province" in out
    assert "(2,0)" not in out and "(0,0)" not in out
    # Seat (1,0): coast + river + coal deposit + coal>iron potential.
    assert "coast" in out and "temperate_forest" in out
    assert "fleuve" in out and "800 000 km²" in out
    assert "coal_outcrop" in out and "exposed_carboniferous_forest" in out
    # Neighbour (2,0): the feature is surfaced as a fact + label, NOT finished prose
    # (Demiurgos owns the voice) — its name/category appear, its description does not.
    assert "Glacial Cirque" in out and "geological_formations" in out
    assert "bowl-shaped valley" not in out
    assert "rich_iron_ore" in out


def test_grounding_radius_limits_the_ring(db, tmp_path):
    _placed(db, tmp_path)
    # radius 0 → only the seat province, no neighbours.
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 0})
    assert "coal_outcrop" in out                 # the seat
    assert "Glacial Cirque" not in out           # (2,0) is out of range


def test_grounding_needs_a_placed_civ(db, tmp_path):
    _placed(db, tmp_path)
    # A civ with no seat gets a clear pointer, not a crash.
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Cheveux de Sang"})
    assert "pas de position" in out
