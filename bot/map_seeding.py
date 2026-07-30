"""Seed a game onto an ingested Theomen world: propose spawn provinces, place civs.

WHAT: after `map_ingestion` has loaded a world's cells, this proposes where civs
could spawn (ranking habitable provinces) and pins a civ to a chosen province
(`controlling_civ_id`). Alexi's design: "un système dans le seeding qui propose des
pos dans le world pour spawn" — the world is the source of truth, the seeding reads
it and suggests positions.

One cell = one 20 km province (Theomen is MACRO worldgen), so "spawn position" means
a starting REGION, not a village site.
"""
from __future__ import annotations

import json
import sqlite3

# Habitability weights — a first, defensible heuristic (tunable). Ocean is excluded
# outright; the rest scores land by how survivable/valuable a starting province is.
_TERRAIN_BASE = {
    "plain": 6, "grassland": 7, "coast": 7, "river_valley": 8, "forest": 6,
    "hills": 5, "plateau": 4, "wetland": 4, "jungle": 4, "desert": 2,
    "mountain": 2, "tundra": 2, "badlands": 1, "ice": 0, "lake": 3, "ocean": -99,
}


def neighbours8(q: int, r: int):
    """The 8 Chebyshev neighbours of a cell."""
    for dr in (-1, 0, 1):
        for dq in (-1, 0, 1):
            if dq or dr:
                yield q + dq, r + dr


def discover(conn: sqlite3.Connection, map_id: int, civ_id: int, cells) -> None:
    """Mark provinces as discovered by a civ (fog of war, spatial). Only real cells;
    idempotent. Does NOT commit — the enclosing write owns the transaction/turn."""
    for q, r in cells:
        if conn.execute("SELECT 1 FROM map_cells WHERE map_id = ? AND q = ? AND r = ?",
                        (map_id, q, r)).fetchone():
            conn.execute(
                "INSERT OR IGNORE INTO map_cell_discovery (map_id, q, r, civ_id) "
                "VALUES (?, ?, ?, ?)", (map_id, q, r, civ_id))


def discovered_set(conn: sqlite3.Connection, map_id: int, civ_id: int) -> set:
    """The provinces a civ has discovered on a map."""
    return {(q, r) for q, r in conn.execute(
        "SELECT q, r FROM map_cell_discovery WHERE map_id = ? AND civ_id = ?",
        (map_id, civ_id)).fetchall()}


def _resolve_map(conn: sqlite3.Connection, map_name: str) -> int:
    """Exact then unique-fuzzy map lookup (mirrors tools.resolve_map_name)."""
    row = conn.execute("SELECT id FROM map_maps WHERE name = ?", (map_name,)).fetchone()
    if row:
        return row[0]
    rows = conn.execute(
        "SELECT id FROM map_maps WHERE name LIKE ?", (f"%{map_name}%",)).fetchall()
    if len(rows) == 1:
        return rows[0][0]
    raise ValueError(f"map {map_name!r} not found (or ambiguous)")


def _habitability(terrain: str, meta: dict) -> tuple[float, list[str]]:
    """Score one land province + the reasons — the WHY the GM/seed can show."""
    why: list[str] = []
    score = float(_TERRAIN_BASE.get(terrain, 3))
    why.append(f"terrain {terrain}")

    water = meta.get("water", {})
    if water.get("is_river"):
        score += 3
        why.append("fleuve (eau + sols alluviaux)")
    if terrain == "coast" or water.get("is_lake"):
        score += 1
        why.append("accès à l'eau")

    # Temperate is survivable; extremes hurt.
    t = meta.get("temperature_c")
    if t is not None:
        score -= min(4.0, abs(t - 15.0) / 6.0)  # smooth penalty away from ~15°C

    # Agricultural potential (soil + forest cover), when Theomen ships those layers.
    fd = meta.get("forest_density")
    if isinstance(fd, (int, float)) and fd > 0.3:
        score += 1
        why.append("couvert forestier")

    # Resources are a bonus, not a requirement (a start doesn't NEED a deposit).
    # Theomen v2: a deposit is now an element of family "deposit" in the cell's set;
    # its category is the material (copper/iron/oil…).
    deposits = [e for e in (meta.get("elements") or []) if e.get("family") == "deposit"]
    if deposits:
        score += 1.5
        why.append(f"gisement {deposits[0].get('category', '?')}")
    pot = meta.get("resource_potential")
    if pot:
        score += 0.5
        why.append(f"potentiel {', '.join(pot[:2])}")

    # budget_score is the SIGNED sum of the element set — hazard-heavy provinces
    # (negative constraints) are naturally penalised, notable ones rewarded.
    b = meta.get("budget_score")
    if isinstance(b, int):
        score += b * 0.3

    return score, why


def propose_spawn_positions(
    conn: sqlite3.Connection, map_name: str, n: int = 5, min_spacing: int = 0
) -> list[dict]:
    """Rank the map's most habitable land provinces as candidate spawn positions.

    Oceans are never proposed. min_spacing (Chebyshev, in provinces) keeps the picks
    apart so several civs don't all get the same corner; 0 disables spacing.
    """
    map_id = _resolve_map(conn, map_name)
    rows = conn.execute(
        "SELECT q, r, terrain_type, metadata FROM map_cells WHERE map_id = ?", (map_id,)
    ).fetchall()

    scored: list[tuple[float, int, int, str, dict, list[str]]] = []
    for q, r, terrain, meta_json in rows:
        meta = json.loads(meta_json) if meta_json else {}
        if meta.get("water", {}).get("is_ocean") or terrain == "ocean":
            continue
        score, why = _habitability(terrain, meta)
        scored.append((score, q, r, terrain, meta, why))

    scored.sort(key=lambda x: (-x[0], x[1], x[2]))  # score desc, then stable by q,r

    picked: list[dict] = []
    for score, q, r, terrain, meta, why in scored:
        if min_spacing > 0 and any(
            max(abs(q - p["q"]), abs(r - p["r"])) < min_spacing for p in picked
        ):
            continue
        picked.append({
            "q": q, "r": r, "terrain": terrain, "biome": meta.get("biome"),
            "score": round(score, 2), "why": why,
        })
        if len(picked) >= n:
            break
    return picked


def place_civ(
    conn: sqlite3.Connection, civ_name: str, map_name: str, q: int, r: int
) -> dict:
    """Pin a civ to a province: set controlling_civ_id on (map_id, q, r).

    Resolves the civ and map by name. The cell must already exist (the world was
    ingested). Returns the resolved ids; commits.
    """
    map_id = _resolve_map(conn, map_name)
    crow = conn.execute(
        "SELECT id FROM civ_civilizations WHERE name = ? "
        "OR name LIKE ? LIMIT 1", (civ_name, f"%{civ_name}%")
    ).fetchone()
    if not crow:
        raise ValueError(f"civ {civ_name!r} not found")
    civ_id = crow[0]

    cell = conn.execute(
        "SELECT 1 FROM map_cells WHERE map_id = ? AND q = ? AND r = ?", (map_id, q, r)
    ).fetchone()
    if not cell:
        raise ValueError(f"cell ({q},{r}) does not exist on map {map_name!r}")

    conn.execute(
        "UPDATE map_cells SET controlling_civ_id = ? WHERE map_id = ? AND q = ? AND r = ?",
        (civ_id, map_id, q, r),
    )
    # A civ knows its seat + immediate surroundings (fog of war).
    discover(conn, map_id, civ_id, [(q, r), *neighbours8(q, r)])
    conn.commit()
    return {"civ_id": civ_id, "map_id": map_id, "q": q, "r": r}
