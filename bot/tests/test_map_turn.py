"""Turn transactionality (option A): map writes are atomic with Demiurgos's turn.

Within beginTurn…commitTurn, writes accumulate but don't commit; abortTurn rolls
them back so a failed turn leaves NO orphan canon (the exact shadow-DB trap Demiurgos
flagged). Reads inside the turn see the pending writes (same connection), so dependent
actions and the echo work.
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
CELLS = {  # plain | coast+river (the best spawn)
    (0, 0): {"elevation": 100.0, "biome": 1, "terrain_type": 4, "flow_accum": 0.0},
    (1, 0): {"elevation": 40.0, "biome": 1, "terrain_type": 1, "flow_accum": 2000.0},
}
SIDECARS = {"terrain_types.json": [{"id": 1, "name": "coast"}, {"id": 4, "name": "plain"}]}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 13,
    "grid": {"width": 2, "height": 1, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "cell_area_km2": 400.0},
    "resources": {"layers": []},
}


def _seed(db, tmp_path):
    w = build_world(tmp_path / "w", width=2, height=1, chunk=4, fields=FIELDS,
                    cell_fn=lambda gx, gy, k: CELLS[(gx, gy)][k],
                    world_json=WORLD_JSON, sidecars=SIDECARS)
    return ingest_world(db, w, "Terre")["map_id"]  # commits the baseline


def _control(db, mid, q, r):
    return db.execute("SELECT controlling_civ_id FROM map_cells WHERE map_id=? AND q=? AND r=?",
                      (mid, q, r)).fetchone()[0]


def _found(db):
    dispatch_tool(db, "foundSettlement",
                  {"civName": "Confluence", "at": "spawn 1", "mapName": "Terre"})


def test_abort_rolls_back_the_write_no_orphan(db, tmp_path):
    mid = _seed(db, tmp_path)
    dispatch_tool(db, "beginTurn", {})
    _found(db)
    assert _control(db, mid, 1, 0) == 1          # visible inside the turn
    dispatch_tool(db, "abortTurn", {})
    assert _control(db, mid, 1, 0) is None        # the turn failed → nothing persists


def test_commit_persists_the_write(db, tmp_path):
    mid = _seed(db, tmp_path)
    dispatch_tool(db, "beginTurn", {})
    _found(db)
    dispatch_tool(db, "commitTurn", {})
    assert _control(db, mid, 1, 0) == 1           # committed with the turn


def test_reads_see_pending_writes_within_the_turn(db, tmp_path):
    _seed(db, tmp_path)
    dispatch_tool(db, "beginTurn", {})
    _found(db)
    out = dispatch_tool(db, "groundCivTerrain", {"civName": "Confluence"})
    assert "(siège)" in out                       # the uncommitted seat is groundable
    dispatch_tool(db, "abortTurn", {})


def test_dependent_writes_share_the_turn_then_abort_together(db, tmp_path):
    """Demiurgos's exact model: a 2nd write sees the 1st (uncommitted) within the turn,
    and abort discards BOTH — nothing half-applied."""
    mid = _seed(db, tmp_path)
    dispatch_tool(db, "beginTurn", {})
    _found(db)                                    # settlement at (1,0), uncommitted
    # expandTerritory reads controlling_civ_id to find the frontier -> it must SEE the
    # uncommitted settlement (same connection) to claim its neighbour (0,0).
    dispatch_tool(db, "expandTerritory",
                  {"civName": "Confluence", "toward": "O", "mapName": "Terre"})
    assert _control(db, mid, 0, 0) == 1           # the dependent write worked on pending state
    dispatch_tool(db, "abortTurn", {})
    assert _control(db, mid, 1, 0) is None and _control(db, mid, 0, 0) is None  # both gone


def test_without_a_turn_writes_commit_immediately(db, tmp_path):
    mid = _seed(db, tmp_path)
    _found(db)                                    # no beginTurn → committed now
    db.rollback()                                 # a stray rollback must NOT undo it
    assert _control(db, mid, 1, 0) == 1
