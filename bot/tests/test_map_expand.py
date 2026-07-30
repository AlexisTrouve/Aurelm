"""Richer writes: expandTerritory (frontier growth, ocean-blocked) + moveEntity (pawn).

Same discipline: semantic direction/anchor, validate (no ocean, no other civ's land),
log migration events, echo. Via the real dispatch path.
"""
from __future__ import annotations

from bot.map_ingestion import ingest_world
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import dispatch_tool

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "element_count", "encoding": "uint", "bits": 8},
    {"name": "element_0", "encoding": "uint", "bits": 16},
]
# 3x1: plain (seat) | plain+landmark | ocean (a hard frontier)
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "element_count": 0, "element_0": 0},
    (1, 0): {"elevation": 90.0, "biome": 1, "terrain_type": 4, "element_count": 1, "element_0": 1},
    (2, 0): {"elevation": -500.0, "biome": 0, "terrain_type": 0, "element_count": 0, "element_0": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 0, "name": "ocean"}, {"id": 4, "name": "plain"}],
    "elements.json": [{"id": 1, "name": "gue", "display_name": "Gué", "family": "landmark",
                       "category": "water_features", "points": 1, "hidden_level": 0}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 11,
    "grid": {"width": 3, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"cell_area_km2": 400.0}, "resources": {"layers": []},
}


def _seed(db, tmp_path):
    w = build_world(tmp_path / "w", width=3, height=1, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    mid = ingest_world(db, w, "Terre")["map_id"]
    db.execute("UPDATE map_cells SET controlling_civ_id = 1 WHERE map_id = ? AND q = 0 AND r = 0", (mid,))
    db.commit()
    return mid


def _control(db, mid, q, r):
    return db.execute("SELECT controlling_civ_id FROM map_cells WHERE map_id=? AND q=? AND r=?",
                      (mid, q, r)).fetchone()[0]


def test_expand_claims_land_and_stops_at_the_ocean(db, tmp_path):
    mid = _seed(db, tmp_path)
    out = dispatch_tool(db, "expandTerritory",
                        {"civName": "Confluence", "toward": "E", "amount": 5, "mapName": "Terre"})
    assert "annexe 1 province" in out and "Territoire total : 2" in out
    assert _control(db, mid, 1, 0) == 1          # the land was claimed
    assert _control(db, mid, 2, 0) is None       # the ocean was NOT


def test_expand_needs_existing_territory(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "expandTerritory",
                        {"civName": "Cheveux de Sang", "toward": "O", "mapName": "Terre"})
    assert "fonde une cité d'abord" in out


def test_move_entity_places_a_pawn(db, tmp_path):
    mid = _seed(db, tmp_path)
    out = dispatch_tool(db, "moveEntity",
                        {"entityName": "Argile", "to": "Gué", "mapName": "Terre"})
    assert "déplacé" in out
    pawn = db.execute(
        "SELECT q, r FROM map_entity_pawns WHERE map_id = ? "
        "AND entity_id = (SELECT id FROM entity_entities WHERE canonical_name LIKE '%Argile%' LIMIT 1)",
        (mid,)).fetchone()
    assert pawn == (1, 0)                          # the Gué feature province


def test_move_entity_unknown(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "moveEntity",
                        {"entityName": "Balrog", "to": "Gué", "mapName": "Terre"})
    assert "introuvable" in out.lower()
