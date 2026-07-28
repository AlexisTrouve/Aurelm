"""Generic narrative writes: recordEvent + annotate — the chronicle.

Same socle discipline as foundSettlement: semantic anchor, validate, log to
map_cell_events, echo the province. Via the real dispatch path.
"""
from __future__ import annotations

from bot.map_ingestion import ingest_world
from bot.tests.fixtures.world_fixture import build_world
from bot.tools import dispatch_tool

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "terrain_type", "encoding": "uint", "bits": 8},
    {"name": "feature", "encoding": "uint", "bits": 8},
]
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "feature": 1},
    (1, 0): {"elevation": 30.0, "biome": 1, "terrain_type": 1, "feature": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 4, "name": "plain"}],
    "features.json": [{"id": 1, "name": "old_oak", "display_name": "Vieux Chêne",
                       "category": "forest_features", "description": "Un chêne millénaire."}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 9,
    "grid": {"width": 2, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"cell_area_km2": 400.0}, "resources": {"layers": []},
}


def _seed(db, tmp_path):
    w = build_world(tmp_path / "w", width=2, height=1, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    return ingest_world(db, w, "Terre")["map_id"]


def _events(db, map_id, q, r):
    return db.execute(
        "SELECT event_type, description FROM map_cell_events "
        "WHERE map_id = ? AND q = ? AND r = ? ORDER BY id", (map_id, q, r)).fetchall()


def test_record_event_logs_the_chronicle(db, tmp_path):
    map_id = _seed(db, tmp_path)
    out = dispatch_tool(db, "recordEvent",
                        {"kind": "battle", "at": "Vieux Chêne", "mapName": "Terre",
                         "description": "Les Confluents repoussent un raid.",
                         "civName": "Confluence"})
    assert "[battle]" in out and "repoussent" in out
    ev = _events(db, map_id, 0, 0)
    assert ("battle", "Les Confluents repoussent un raid. (Civilisation de la Confluence)") in ev


def test_record_event_rejects_an_unknown_kind(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "recordEvent",
                        {"kind": "wedding", "at": "Vieux Chêne", "mapName": "Terre",
                         "description": "x"})
    assert "inconnu" in out.lower()


def test_annotate_sets_a_label(db, tmp_path):
    map_id = _seed(db, tmp_path)
    out = dispatch_tool(db, "annotate",
                        {"at": "Vieux Chêne", "label": "Champ de Bataille", "mapName": "Terre"})
    assert "label" in out.lower()
    lbl = db.execute(
        "SELECT label FROM map_cells WHERE map_id = ? AND q = 0 AND r = 0", (map_id,)).fetchone()[0]
    assert lbl == "Champ de Bataille"


def test_annotate_attaches_a_note(db, tmp_path):
    map_id = _seed(db, tmp_path)
    dispatch_tool(db, "annotate",
                  {"at": "Vieux Chêne", "note": "Lieu sacré des anciens.", "mapName": "Terre"})
    ev = _events(db, map_id, 0, 0)
    assert ("note", "Lieu sacré des anciens.") in ev


def test_annotate_needs_something_to_write(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "annotate", {"at": "Vieux Chêne", "mapName": "Terre"})
    assert "label" in out.lower() and "note" in out.lower()
