"""Ingest a Theomen `.world` export into a game DB's map_maps/map_cells.

WHAT: read a decoded world (bot.world_reader), resolve Theomen's index fields to
names via the export's sidecars, invert the log-encoded resource densities, and
upsert a rectangular WINDOW of cells into one game database. Aurelm is the canon
store; Theomen is the source; the resulting map feeds the grounding served to the
Demiurgos GM.

WHY crop-on-ingest: Theomen ships the whole planet (~1.8M cells); a Demiurgos game
plays on a region. We decode the full export but write only the window's cells, so
Aurelm never hosts a globe and Theomen needs no bbox-crop of its own.

Reference: docs/map-ingestion-plan.md, and (source side)
Gamedesigner/theomen/docs/{SPEC_WORLD_FORMAT.md, CONTRAT_EXPORT_AURELM.md}.

One cell = one 20 km province (Theomen is MACRO worldgen) — the grounding is
empire/region-scale geography, never village-scale terrain.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .world_reader import WorldHeader, read_world

# Coarse terrain fallback, used ONLY until Theomen ships its `terrain_type` layer
# (it owns the macro classification; this keeps the map paintable before then).
_MOUNTAIN_M = 2000.0
_HILLS_M = 500.0


def _resolve_idx(value, name_map: dict | None) -> dict | None:
    """Resolve a uint index field to its sidecar entry; index 0 = none (SPEC)."""
    if value is None or name_map is None:
        return None
    idx = int(round(value))
    if idx == 0:
        return None
    return name_map.get(idx)


def _pick(d: dict, keys: list[str]) -> dict:
    """Keep only the present keys of a sidecar entry (drop absent ones)."""
    return {k: d[k] for k in keys if k in d and d[k] is not None}


def _resource_potential(cell: dict, h: WorldHeader, top: int = 3) -> list[str]:
    """Top-K material types by ABSOLUTE mass at this cell (SPEC §5).

    The res_<type> layers are log10-normalized PER TYPE — comparing their raw u01
    across types is meaningless. We invert each to the single common (arbitrary)
    mass scale using the layer's max_mass, then rank. u01==0 is absence, never mass.
    Returns ordered type names only: the mass unit is internal, used to order, not
    surfaced to the GM (Theomen's rule 4).
    """
    masses: list[tuple[float, str]] = []
    for fname, layer in h.resource_layers.items():
        if fname not in cell:
            continue
        u01 = cell[fname]  # reader already decoded unorm8 as raw/255
        if u01 <= 0:
            continue  # absence, not a zero-mass deposit
        max_mass = layer.get("max_mass")
        if not max_mass:
            continue  # no max_type → cannot invert → skip cross-material ranking
        d01 = (u01 - h.res_floor01) / (1.0 - h.res_floor01)
        mass = float(max_mass) * (10.0 ** ((d01 - 1.0) * h.res_log_decades))
        masses.append((mass, layer.get("type", fname)))
    masses.sort(reverse=True)
    return [t for _, t in masses[:top]]


def _resolve_terrain(cell: dict, h: WorldHeader, biome_name: str | None,
                     is_ocean: bool, is_lake: bool) -> str:
    """map_cells.terrain_type: Theomen's macro class when present, else a fallback."""
    tt = _resolve_idx(cell.get("terrain_type"), h.name_maps.get("terrain_types"))
    if tt:
        return tt.get("name") or str(tt.get("id"))
    if is_ocean:
        return "ocean"
    if is_lake:
        return "lake"
    elev = cell.get("elevation", 0.0)
    if elev >= _MOUNTAIN_M:
        return "mountain"
    if elev >= _HILLS_M:
        return "hills"
    return biome_name or "plain"


def cell_to_record(cell: dict, h: WorldHeader) -> tuple[str, dict]:
    """Turn one decoded cell into (terrain_type, metadata dict).

    metadata only carries keys that are actually present — a field Theomen has not
    shipped yet simply doesn't appear, so ingest works on today's partial export
    and on the full one unchanged.
    """
    meta: dict = {}

    elev = cell.get("elevation")
    if elev is not None:
        meta["elevation_m"] = round(elev, 1)
    if "temperature" in cell:
        meta["temperature_c"] = round(cell["temperature"], 1)

    biome_name = None
    if "biome" in cell:
        idx = int(round(cell["biome"]))
        if idx:  # 0 = ocean / unclassified (SPEC §4)
            biome_name = h.biomes.get(idx, {}).get("name")
    if biome_name:
        meta["biome"] = biome_name

    # Water — three independent cases, never squashed into one flag (Theomen §3).
    thr = h.thresholds
    is_ocean = elev is not None and elev <= h.sea_level_m
    water = {"is_ocean": is_ocean, "is_lake": False, "is_river": False}
    ld = cell.get("lake_depth")
    if ld is not None and ld > thr.get("lake_min_depth_m", 15.0):
        water["is_lake"] = True
        water["lake_depth_m"] = round(ld, 1)
    fa = cell.get("flow_accum")
    if fa is not None and fa > thr.get("river_min_catchment_cells", 1500.0):
        water["is_river"] = True
        water["river_catchment_km2"] = round(fa * thr.get("cell_area_km2", 400.0))
    meta["water"] = water

    dep = _resolve_idx(cell.get("deposit"), h.name_maps.get("deposits"))
    if dep:
        meta["deposit"] = _pick(dep, ["name", "display_name", "catalog", "tier",
                                     "yield", "extraction_difficulty", "formation_type"])
    feat = _resolve_idx(cell.get("feature"), h.name_maps.get("features"))
    if feat:
        meta["feature"] = _pick(feat, ["name", "display_name", "category", "description"])

    pot = _resource_potential(cell, h)
    if pot:
        meta["resource_potential"] = pot

    if "budget" in cell:
        meta["budget_score"] = int(round(cell["budget"]))
    for k in ("soil_type", "soil_depth", "forest_density", "humidity"):
        if k in cell:
            v = cell[k]
            meta[k] = round(v, 3) if isinstance(v, float) else v

    terrain = _resolve_terrain(cell, h, biome_name, is_ocean, water["is_lake"])
    return terrain, meta


def ingest_world(
    conn: sqlite3.Connection,
    world_dir: str | Path,
    map_name: str,
    window: tuple[int, int, int, int] | None = None,
) -> dict:
    """Ingest a `.world` export into one game DB as a `map_maps` + its `map_cells`.

    window = (x, y, w, h) in GLOBAL cell coords; None → the whole world. Local cell
    coords are (q, r) = (gx - x, gy - y). Idempotent: re-ingesting the same map_name
    replaces its cells. The caller owns transactions elsewhere; we commit once here.
    """
    w = read_world(world_dir)
    h = w.header
    wx, wy, ww, wh = window if window else (0, 0, h.width, h.height)

    map_meta = {
        "contract_version": h.contract_version,
        "seed": h.seed,
        "cell_km": h.cell_km,
        "wrap_x": h.wrap_x,          # cylinder: grounding neighbourhoods wrap in X
        "bbox": {"x": wx, "y": wy, "w": ww, "h": wh},
        "biome_palette": {b["name"]: b.get("color")
                         for b in h.biomes.values() if b.get("name")},
    }

    row = conn.execute("SELECT id FROM map_maps WHERE name = ?", (map_name,)).fetchone()
    if row:
        map_id = row[0]
        conn.execute(
            "UPDATE map_maps SET grid_type='square', grid_cols=?, grid_rows=?, metadata=? "
            "WHERE id = ?",
            (ww, wh, json.dumps(map_meta, ensure_ascii=False), map_id),
        )
        conn.execute("DELETE FROM map_cells WHERE map_id = ?", (map_id,))  # replace
    else:
        cur = conn.execute(
            "INSERT INTO map_maps (name, grid_type, grid_cols, grid_rows, metadata) "
            "VALUES (?, 'square', ?, ?, ?)",
            (map_name, ww, wh, json.dumps(map_meta, ensure_ascii=False)),
        )
        map_id = cur.lastrowid

    n = 0
    for cell in w.cells():
        gx, gy = cell["x"], cell["y"]
        if not (wx <= gx < wx + ww and wy <= gy < wy + wh):
            continue
        terrain, meta = cell_to_record(cell, h)
        conn.execute(
            "INSERT INTO map_cells (map_id, q, r, terrain_type, metadata) VALUES (?, ?, ?, ?, ?)",
            (map_id, gx - wx, gy - wy, terrain,
             json.dumps(meta, ensure_ascii=False) if meta else None),
        )
        n += 1

    conn.commit()
    return {"map_id": map_id, "map_name": map_name, "cells": n,
            "window": {"x": wx, "y": wy, "w": ww, "h": wh}}


def main(argv=None) -> int:
    """CLI: ingest a Theomen `.world` export into a game DB.

        python -m bot.map_ingestion --db game.aurelm.db --world seed42.world \
            --map-name "Terre" [--window x,y,w,h]

    The DB must already carry the map schema (created by `bot --migrate-only`); this is
    an offline batch step, never an agent tool.
    """
    import argparse

    ap = argparse.ArgumentParser(prog="python -m bot.map_ingestion",
                                 description="Ingest a Theomen .world export into a game DB.")
    ap.add_argument("--db", required=True, help="path to the game's .aurelm.db")
    ap.add_argument("--world", required=True, help="path to the .world export directory")
    ap.add_argument("--map-name", required=True, help="name for the ingested map")
    ap.add_argument("--window", help="crop 'x,y,w,h' in global cells (default: whole world)")
    args = ap.parse_args(argv)

    window = None
    if args.window:
        try:
            parts = tuple(int(v) for v in args.window.split(","))
        except ValueError:
            ap.error("--window must be four integers 'x,y,w,h'")
        if len(parts) != 4:
            ap.error("--window must be 'x,y,w,h'")
        window = parts

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        res = ingest_world(conn, args.world, args.map_name, window=window)
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print(f"error: the DB has no map schema — run `bot --migrate-only --db {args.db}` "
                  f"first. ({e})")
            return 1
        raise
    finally:
        conn.close()
    print(f"Ingested {res['cells']} provinces into map '{res['map_name']}' "
          f"(id {res['map_id']}) — window {res['window']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
