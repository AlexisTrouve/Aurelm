"""Feature-discover (content gating): groundCivTerrain hides an element whose
`hidden_level` exceeds the civ's prospecting depth.

Spatial fog says WHICH provinces a civ sees; this says WHAT it knows of a shown
province's contents. A neolithic civ standing on coal doesn't "know" the coal. Aurelm
carries hidden_level per element; the consumer (Demiurgos) passes the depth its tech
unlocks via maxHiddenLevel. Deeper elements are COUNTED ("à prospecter"), never named.
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
    {"name": "element_1", "encoding": "uint", "bits": 16},
]
# 3x1 coast. The middle province carries a SURFACE landmark (hidden 0) + a BURIED
# coal seam (hidden 2) — the civ founds here, so the seat is always shown; only the
# CONTENT gating varies.
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 1, "element_count": 0, "element_0": 0, "element_1": 0},
    (1, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 1, "element_count": 2, "element_0": 1, "element_1": 2},
    (2, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 1, "element_count": 0, "element_0": 0, "element_1": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 1, "name": "coast"}],
    "elements.json": [
        {"id": 1, "name": "grand_port", "display_name": "Grand Port", "family": "landmark",
         "category": "coastal_features", "points": 3, "hidden_level": 0},
        {"id": 2, "name": "coal_seam", "display_name": "Veine de Charbon", "family": "deposit",
         "category": "coal", "points": 2, "hidden_level": 2},
    ],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 21,
    "grid": {"width": 3, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"cell_area_km2": 400.0}, "resources": {"layers": []},
}


def _found(db, tmp_path):
    db.execute("UPDATE map_cells SET controlling_civ_id = NULL WHERE controlling_civ_id = 1")
    db.commit()
    w = build_world(tmp_path / "w", width=3, height=1, chunk=8, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    ingest_world(db, w, "Terre")
    # Found on the middle province via its surface landmark → seat = (1,0).
    dispatch_tool(db, "foundSettlement",
                  {"civName": "Confluence", "at": "Grand Port", "mapName": "Terre"})


def _ground(db, **kw):
    return dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence", "radius": 0, **kw})


def test_surface_shown_buried_only_counted_by_default(db, tmp_path):
    _found(db, tmp_path)
    out = _ground(db)                                  # fog on, maxHiddenLevel 0 (surface)
    assert "Grand Port" in out                         # the surface landmark is known
    assert "Veine de Charbon" not in out               # the buried coal is NOT named
    assert "1 élément à prospecter" in out             # but the civ senses something


def test_prospecting_depth_reveals_the_buried_element(db, tmp_path):
    _found(db, tmp_path)
    out = _ground(db, maxHiddenLevel=2)                # tech unlocks depth 2
    assert "Grand Port" in out and "Veine de Charbon" in out
    assert "à prospecter" not in out


def test_gm_omniscience_reveals_everything(db, tmp_path):
    _found(db, tmp_path)
    out = _ground(db, fog=False)                       # fog=false = see all content
    assert "Grand Port" in out and "Veine de Charbon" in out
    assert "à prospecter" not in out
