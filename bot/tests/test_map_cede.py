"""cedeTerritory: one civ hands provinces to another (diplomacy / conquest).

A TRANSFER, not a claim: validates the ceding civ owns the anchor province, flips
control, logs a 'diplomatic' event, and the RECIPIENT discovers what it gained.
amount>1 extends over the ceding civ's contiguous provinces. Semantic anchor only.
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
# 4x1 plain. Confluence will own (0,0)+(1,0); Cheveux owns (3,0). A named landmark on
# (1,0) is the cession anchor.
CELLS = {
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "element_count": 0, "element_0": 0},
    (1, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "element_count": 1, "element_0": 1},
    (2, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "element_count": 0, "element_0": 0},
    (3, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "element_count": 0, "element_0": 0},
}
SIDECARS = {
    "terrain_types.json": [{"id": 4, "name": "plain"}],
    "elements.json": [{"id": 1, "name": "col_frontalier", "display_name": "Col Frontalier",
                       "family": "landmark", "category": "geological_formations",
                       "points": 1, "hidden_level": 0}],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 23,
    "grid": {"width": 4, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"cell_area_km2": 400.0}, "resources": {"layers": []},
}


def _seed(db, tmp_path):
    # Isolate: drop any conftest-seeded control, then place the two civs by hand.
    db.execute("UPDATE map_cells SET controlling_civ_id = NULL")
    db.commit()
    w = build_world(tmp_path / "w", width=4, height=1, chunk=8, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    mid = ingest_world(db, w, "Terre")["map_id"]
    db.execute("UPDATE map_cells SET controlling_civ_id = 1 WHERE map_id = ? AND r = 0 AND q IN (0, 1)", (mid,))
    db.execute("UPDATE map_cells SET controlling_civ_id = 2 WHERE map_id = ? AND q = 3 AND r = 0", (mid,))
    db.commit()
    return mid


def _control(db, mid, q, r):
    return db.execute("SELECT controlling_civ_id FROM map_cells WHERE map_id=? AND q=? AND r=?",
                      (mid, q, r)).fetchone()[0]


def _discovered(db, mid, civ_id, q, r):
    return db.execute("SELECT 1 FROM map_cell_discovery WHERE map_id=? AND civ_id=? AND q=? AND r=?",
                      (mid, civ_id, q, r)).fetchone() is not None


def test_cede_transfers_control_logs_event_recipient_discovers(db, tmp_path):
    mid = _seed(db, tmp_path)
    out = dispatch_tool(db, "cedeTerritory",
                        {"fromCiv": "Confluence", "toCiv": "Cheveux de Sang",
                         "at": "Col Frontalier", "mapName": "Terre"})
    assert "cède" in out
    assert _control(db, mid, 1, 0) == 2               # (1,0) now belongs to Cheveux
    assert _control(db, mid, 0, 0) == 1               # (0,0) untouched (amount 1)
    ev = db.execute(
        "SELECT event_type FROM map_cell_events WHERE map_id=? AND q=1 AND r=0 ORDER BY id DESC LIMIT 1",
        (mid,)).fetchone()
    assert ev[0] == "diplomatic"
    assert _discovered(db, mid, 2, 1, 0)              # recipient discovers what it gained


def test_cede_amount_extends_to_contiguous(db, tmp_path):
    mid = _seed(db, tmp_path)
    dispatch_tool(db, "cedeTerritory",
                  {"fromCiv": "Confluence", "toCiv": "Cheveux de Sang",
                   "at": "Col Frontalier", "amount": 2, "mapName": "Terre"})
    # Both Confluence provinces (1,0)+(0,0) are contiguous → both cede.
    assert _control(db, mid, 1, 0) == 2 and _control(db, mid, 0, 0) == 2


def test_cede_rejects_non_owned_province(db, tmp_path):
    _seed(db, tmp_path)
    # (3,0) belongs to Cheveux; Confluence can't cede it.
    db.execute("UPDATE map_cells SET label = 'Port Rouge' WHERE controlling_civ_id = 2")
    db.commit()
    out = dispatch_tool(db, "cedeTerritory",
                        {"fromCiv": "Confluence", "toCiv": "Cheveux de Sang",
                         "at": "Port Rouge", "mapName": "Terre"})
    assert "ne contrôle pas" in out


def test_cede_rejects_self(db, tmp_path):
    _seed(db, tmp_path)
    out = dispatch_tool(db, "cedeTerritory",
                        {"fromCiv": "Confluence", "toCiv": "Confluence",
                         "at": "Col Frontalier", "mapName": "Terre"})
    assert "elle-même" in out
