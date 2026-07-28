"""Drive a REAL LLM through the map tools, end-to-end, on a semantically rich world.

Not a pytest test — a probe (costs real LLM turns). It builds a full-contract
`theomen.world.v1` stub world (biome + graded deposits + features + a river + a
mountain barrier), ingests it via the real pipeline, founds two civs, boots
`python -m bot`, and POSTs GM questions to /chat. It prints which map tools the agent
actually chose and its answers — the only way to see whether the tools are usable by a
real model (as opposed to "the dispatch works" in a unit test). It is the live proof
the map system works with an agent, pending Theomen's real v1 export.

    PYTHONIOENCODING=utf-8 py -3.12 bot/tests/live_map_probe.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE_DB = REPO / "gui" / "integration_test" / "fixtures" / "e2e.db"  # has the civs + lore
KEY = os.environ.get("ETHERYALE_API_KEY") or "eai_ESu-8usnN17_6I09zZ2F5A15rGnrZVfQ"

sys.path.insert(0, str(REPO))
from bot.tests.fixtures.world_fixture import build_world  # noqa: E402
from bot.map_ingestion import ingest_world  # noqa: E402
from bot.tools import found_settlement, resolve_civ_name  # noqa: E402

# ---------------------------------------------------------------------------
# A small but full-contract world: a Confluence river valley (west) and a Cheveux
# grassland (east), separated by an alpine mountain barrier (q=3). Coal in the west,
# iron in the east, features scattered.
# ---------------------------------------------------------------------------
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
TERRAINS = {0: "ocean", 1: "coast", 2: "mountain", 3: "plain", 4: "forest", 6: "grassland"}
BIOMES = [
    {"id": 0, "name": "ocean", "color": "#1a3d6b"},
    {"id": 1, "name": "temperate_forest", "color": "#3f8f43"},
    {"id": 2, "name": "alpine", "color": "#c9d6e0"},
    {"id": 3, "name": "grassland", "color": "#9fbf5a"},
]
SIDECARS = {
    "terrain_types.json": [{"id": i, "name": n} for i, n in TERRAINS.items()],
    "deposits.json": [
        {"id": 1, "name": "coal_outcrop", "display_name": "Coal Outcrop", "catalog": "coal",
         "tier": "standard", "formation_type": "exposed_carboniferous_forest"},
        {"id": 2, "name": "rich_iron_ore", "display_name": "Rich Iron Ore", "catalog": "iron",
         "tier": "premium", "formation_type": "banded_iron_formation"},
    ],
    "features.json": [
        {"id": 1, "name": "glacial_cirque", "display_name": "Cirque Glaciaire",
         "category": "geological_formations", "description": "x"},
        {"id": 2, "name": "ancient_grove", "display_name": "Bosquet Ancien",
         "category": "forest_features", "description": "x"},
        {"id": 3, "name": "great_oak", "display_name": "Grand Chêne",
         "category": "natural_landmarks", "description": "x"},
    ],
}
WORLD_JSON = {
    "contract_version": "theomen.world.v1", "seed": 42,
    "grid": {"width": 7, "height": 3, "downsample": 1, "cell_km": 20.0},
    "topology": {"wrap_x": False}, "elevation": {"sea_level_value": 0.0},
    "thresholds": {"river_min_catchment_cells": 1500.0, "lake_min_depth_m": 15.0,
                   "cell_area_km2": 400.0},
    "resources": {"encoding": "log10_per_type", "log_decades": 8.0, "floor01": 1.0 / 255.0,
                  "layers": [{"field": "res_iron", "type": "iron", "max_mass": 3.71e17},
                             {"field": "res_coal", "type": "coal", "max_mass": 9.02e15}]},
}
# defaults, then per-cell overrides (q, r) -> field patches
_DEF = {"elevation": 150.0, "biome": 3, "temperature": 15.0, "terrain_type": 3,
        "deposit": 0, "feature": 0, "flow_accum": 0.0, "res_iron": 0, "res_coal": 0}
_OVR = {
    (3, 0): {"elevation": 2900.0, "biome": 2, "temperature": -4.0, "terrain_type": 2, "feature": 1},
    (3, 1): {"elevation": 2800.0, "biome": 2, "temperature": -3.0, "terrain_type": 2},
    (3, 2): {"elevation": 2700.0, "biome": 2, "temperature": -3.0, "terrain_type": 2},
    (1, 1): {"elevation": 45.0, "biome": 1, "temperature": 16.0, "terrain_type": 1,
             "flow_accum": 2200.0, "res_coal": 150},   # Confluence cradle: coast + river
    (0, 1): {"terrain_type": 3, "deposit": 1, "res_coal": 240},                 # coal west
    (1, 0): {"biome": 1, "terrain_type": 4, "feature": 2},                      # ancient grove
    (5, 1): {"terrain_type": 6, "feature": 3},                                  # Cheveux cradle: great oak
    (6, 1): {"terrain_type": 3, "deposit": 2, "res_iron": 220},                 # iron east
}


def _cell(gx, gy, name):
    return _OVR.get((gx, gy), {}).get(name, _DEF[name])


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _setup_db(tmp: Path) -> Path:
    """Copy the civ fixture, migrate, ingest the world, found the two civs."""
    game = tmp / "game.aurelm.db"
    shutil.copy(FIXTURE_DB, game)
    subprocess.run([sys.executable, "-m", "bot", "--db", str(game), "--migrate-only"],
                   cwd=str(REPO), capture_output=True, text=True)

    world = tmp / "seed42v1.world"
    build_world(world, width=7, height=3, chunk=8, fields=FIELDS, cell_fn=_cell,
                world_json=WORLD_JSON, biomes=BIOMES, sidecars=SIDECARS)

    conn = sqlite3.connect(game)
    res = ingest_world(conn, world, "Terre du Milieu")
    print(f"[setup] ingested {res['cells']} provinces")
    for name, at in (("Confluence", "spawn 1"), ("Cheveux de Sang", "Grand Chêne")):
        r = resolve_civ_name(conn, name)
        if "error" in r:
            print(f"[setup] !! civ {name} not found: {r['error']}")
            continue
        out = found_settlement(conn, r["civ"]["id"], r["civ"]["name"], "Terre du Milieu", at)
        print(f"[setup] {name}: {out.splitlines()[0]}")
    conn.close()
    return game


def ask(port: int, q: str) -> tuple[list[str], str]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/chat",
        data=json.dumps({"message": q}).encode(),
        headers={"Content-Type": "application/json"})
    tools, answer = [], ""
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "tool_start":
                tools.append(f"{ev.get('name')}({ev.get('input_summary', '')})")
            elif ev.get("type") == "text":
                answer = ev.get("content", "")
            elif ev.get("type") == "error":
                answer = f"[ERROR] {ev.get('message')}"
    return tools, answer


QUESTIONS = [
    "Décris-moi le terrain autour de la civilisation de la Confluence.",
    "La Confluence a-t-elle accès à du fer ou du charbon à proximité ?",
    "Qu'y a-t-il entre la Confluence et les Cheveux de Sang ? Une barrière naturelle ?",
    "Sur la carte, quelles seraient de bonnes positions de départ pour une nouvelle civ ?",
]


def main() -> int:
    tmp = Path(os.environ.get("TEMP", "/tmp")) / "aurelm_map_probe"
    tmp.mkdir(parents=True, exist_ok=True)
    game = _setup_db(tmp)

    port = _free_port()
    env = {**os.environ, "ETHERYALE_API_KEY": KEY}
    proc = subprocess.Popen(
        [sys.executable, "-m", "bot", "--db", str(game), "--port", str(port)],
        cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            print("[!] server never healthy:")
            proc.terminate()
            print((proc.communicate(timeout=10)[0] or "")[-2000:])
            return 1
        print(f"[server] up on :{port}\n")

        for q in QUESTIONS:
            print("=" * 80)
            print(f"[Q] {q}")
            tools, answer = ask(port, q)
            print(f"  tools : {tools}")
            print(f"  answer: {answer.strip()[:900]}\n")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
