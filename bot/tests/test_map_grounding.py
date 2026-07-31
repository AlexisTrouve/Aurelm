"""groundCivTerrain: the structured local terrain served to the Demiurgos GM.

Ingest a small rich world, place a civ, and assert the grounding (via the real
dispatch path — how an MCP consumer reaches it) renders the seat + the ring of
provinces with biome, water regime, the v2 point-budget element set (labels +
signed points), and resource potential. 1 cell = 1 province (empire-scale).
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
    # v2 point-budget element set: a count + uint16 id slots (was deposit + feature).
    {"name": "element_count", "encoding": "uint", "bits": 8},
    {"name": "element_0", "encoding": "uint", "bits": 16},
    {"name": "element_1", "encoding": "uint", "bits": 16},
    {"name": "flow_accum", "encoding": "float32"},
    {"name": "res_iron", "encoding": "unorm8"},
    {"name": "res_coal", "encoding": "unorm8"},
]
CELLS = {
    (0, 0): {"elevation": 120.0, "biome": 1, "temperature": 15.0, "terrain_type": 4,
             "element_count": 0, "element_0": 0, "element_1": 0,
             "flow_accum": 0.0, "res_iron": 0, "res_coal": 0},
    (1, 0): {"elevation": 40.0, "biome": 1, "temperature": 16.0, "terrain_type": 1,
             "element_count": 1, "element_0": 1, "element_1": 0,  # coal deposit
             "flow_accum": 2000.0, "res_iron": 50, "res_coal": 255},
    (2, 0): {"elevation": 2600.0, "biome": 2, "temperature": -5.0, "terrain_type": 2,
             "element_count": 2, "element_0": 2, "element_1": 3,  # iron deposit + glacial cirque
             "flow_accum": 0.0, "res_iron": 250, "res_coal": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 2, "name": "mountain"},
                           {"id": 4, "name": "plain"}],
    "elements.json": [
        {"id": 1, "name": "coal_outcrop", "display_name": "Coal Outcrop", "family": "deposit",
         "category": "coal", "formation_type": "exposed_carboniferous_forest",
         "points": 1, "hidden_level": 0},
        {"id": 2, "name": "rich_iron_ore", "display_name": "Rich Iron Ore", "family": "deposit",
         "category": "iron", "formation_type": "banded_iron_formation",
         "points": 2, "hidden_level": 0},
        {"id": 3, "name": "glacial_cirque", "display_name": "Glacial Cirque", "family": "landmark",
         "category": "geological_formations", "points": 1, "hidden_level": 0},
    ],
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
    # Seat (1,0): coast + river + coal deposit element + coal>iron potential.
    assert "coast" in out and "temperate_forest" in out
    assert "fleuve" in out and "800 000 km²" in out
    assert "Coal Outcrop" in out                  # the v2 element display name (+1)
    # Neighbour (2,0): the element SET is surfaced as facts + labels (display name +
    # signed points), NOT prose — v2 elements carry no description, so none can leak.
    assert "éléments" in out
    assert "Glacial Cirque" in out and "Rich Iron Ore" in out


def test_grounding_radius_limits_the_ring(db, tmp_path):
    _placed(db, tmp_path)
    # radius 0 → only the seat province, no neighbours.
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 0})
    assert "Coal Outcrop" in out                 # the seat element
    assert "Glacial Cirque" not in out           # (2,0) is out of range


def test_grounding_needs_a_placed_civ(db, tmp_path):
    _placed(db, tmp_path)
    # A civ with no seat gets a clear pointer, not a crash.
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Cheveux de Sang"})
    assert "pas de position" in out


def test_grounding_reads_back_the_chronicle(db, tmp_path):
    """A chronicle event written on the seat resurfaces in the grounding (the
    write→read loop, Demiurgos Scribe Increment 2). This also exercises the new
    anchor: recordEvent at='Confluence' targets the CIV's seat, not "spawn 1"."""
    _placed(db, tmp_path)   # Confluence seat = (1,0)
    dispatch_tool(db, "recordEvent",
                  {"kind": "battle", "at": "Confluence",
                   "description": "Grande bataille du fleuve", "mapName": "Terre"})

    # The event landed on the seat cell — the civ-name anchor resolved to (1,0).
    ev = db.execute(
        "SELECT q, r FROM map_cell_events mce JOIN map_maps m ON m.id = mce.map_id "
        "WHERE m.name = 'Terre' AND mce.event_type = 'battle'").fetchone()
    assert ev == (1, 0)

    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 1})
    assert "chronique" in out
    assert "[battle]" in out and "Grande bataille du fleuve" in out


def test_events_per_cell_zero_silences_the_chronicle(db, tmp_path):
    """eventsPerCell=0 → the grounding carries terrain only, no chronicle."""
    _placed(db, tmp_path)
    dispatch_tool(db, "recordEvent",
                  {"kind": "note", "at": "Confluence", "description": "un secret",
                   "mapName": "Terre"})
    out = dispatch_tool(db, "groundCivTerrain",
                        {"civName": "Confluence", "radius": 1, "eventsPerCell": 0})
    assert "chronique" not in out and "un secret" not in out


def test_game_time_is_stored_and_ages_the_read_back(db, tmp_path):
    """Demiurgos stamps events with an in-game year (gameTime) and passes a cutoff
    (sinceGameTime); Aurelm stores the stamp and filters mechanically — no aging policy
    of its own. An old event drops out of the grounding, a recent one stays."""
    _placed(db, tmp_path)
    dispatch_tool(db, "recordEvent",
                  {"kind": "discovery", "at": "Confluence", "gameTime": 5,
                   "description": "un homme taille le silex", "mapName": "Terre"})
    dispatch_tool(db, "recordEvent",
                  {"kind": "battle", "at": "Confluence", "gameTime": 200,
                   "description": "la guerre des fonderies", "mapName": "Terre"})

    # The stamp is stored verbatim on the row.
    stamps = {d: gt for d, gt in db.execute(
        "SELECT description, game_time FROM map_cell_events "
        "WHERE description LIKE '%silex%' OR description LIKE '%fonderies%'")}
    assert stamps["un homme taille le silex"] == 5
    assert stamps["la guerre des fonderies"] == 200

    # Cutoff at year 100: the neolithic discovery ages out, the recent war stays.
    out = dispatch_tool(db, "groundCivTerrain",
                        {"civName": "Confluence", "radius": 0, "sinceGameTime": 100})
    assert "guerre des fonderies" in out
    assert "silex" not in out


def test_unstamped_events_are_never_time_filtered(db, tmp_path):
    """An event with no gameTime (NULL) can't be compared to a cutoff — Aurelm lets it
    through and leaves unknown-time handling to Demiurgos."""
    _placed(db, tmp_path)
    dispatch_tool(db, "recordEvent",
                  {"kind": "note", "at": "Confluence",
                   "description": "événement sans date", "mapName": "Terre"})  # no gameTime
    out = dispatch_tool(db, "groundCivTerrain",
                        {"civName": "Confluence", "radius": 0, "sinceGameTime": 100})
    assert "événement sans date" in out
