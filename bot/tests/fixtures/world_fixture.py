"""Build a spec-faithful `.world` (GMVC) directory for tests — WITHOUT the reader.

WHY this exists: Theomen's real export does not exist yet, and testing the GMVC
decoder against data produced by the decoder itself would hide a shared bug. This
builder writes the bytes by literally following `Gamedesigner/theomen/docs/
SPEC_WORLD_FORMAT.md` §2-§3 (magic, LE header, LSB-first presence mask, per-field
packedLen + byte-aligned arrays), so the encoder and the decoder are independent
implementations of the same written spec. The real Theomen export remains the
ultimate validation.

Byte-aligned only (float32=32b, unorm8=8b): at widths that are multiples of 8 the
spec's bit-packing degenerates to a contiguous array, so we pack with `struct`.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Callable


def _pack_field(f: dict, values: list[float]) -> bytes:
    """Byte-aligned pack of one field's cell values (schema order, row-major).

    unorm8 / uint / int callers supply the RAW integer directly (the fixture writes
    exactly what the decoder will read back), matching the spec's storage.
    """
    enc = f["encoding"]
    n = len(values)
    if enc == "float32":
        return struct.pack("<%df" % n, *values)
    if enc == "unorm8":
        return struct.pack("<%dB" % n, *[int(v) & 0xFF for v in values])
    if enc in ("uint", "int"):
        bits = int(f.get("bits", 8))
        if bits != 8:
            raise ValueError("fixture only emits uint/int at bits=8")
        code = "B" if enc == "uint" else "b"
        return struct.pack("<%d%s" % (n, code), *[int(v) for v in values])
    raise ValueError(f"fixture: unsupported encoding {enc!r}")


def build_world(
    out_dir: str | Path,
    *,
    width: int,
    height: int,
    chunk: int = 4,
    fields: list[dict],
    cell_fn: Callable[[int, int, str], float | None],
    world_json: dict | None = None,
    biomes: list[dict] | None = None,
    sidecars: dict[str, list] | None = None,
) -> Path:
    """Write a `.world` dir: manifest.json + chunks/*.gmvc + world.json + biomes.json.

    fields:   [{"name","encoding"}] in SCHEMA ORDER (presence mask indexes this).
    cell_fn:  (gx, gy, field_name) -> value, or None to mark the field ABSENT for
              that cell's whole chunk (used to exercise sparsity — a field is
              emitted for a chunk only if at least one of its cells is non-None).
    """
    out = Path(out_dir)
    (out / "chunks").mkdir(parents=True, exist_ok=True)

    field_names = [f["name"] for f in fields]
    n_fields = len(fields)
    mask_bytes = (n_fields + 7) // 8

    # --- manifest.json (GroveEngine schema; bounds.max INCLUSIVE) ---
    manifest = {
        "formatVersion": 1,
        "coordinate": {
            "topology": "square",
            "cellSize": [1.0, 1.0],
            "bounds": {"min": [0, 0, 0], "max": [width - 1, height - 1, 0]},
            "chunkDims": [chunk, chunk, 1],
        },
        "fields": fields,
        "chunks": "chunks",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # --- one blob per chunk ---
    for y0 in range(0, height, chunk):
        for x0 in range(0, width, chunk):
            lw = min(chunk, width - x0)
            lh = min(chunk, height - y0)
            cell_count = lw * lh

            # Gather values per field in row-major (stride = lw). A field is present
            # in this chunk iff any of its cells is non-None.
            present: list[bool] = []
            packed_per_field: list[bytes] = []
            for f in fields:
                name, enc = f["name"], f["encoding"]
                vals: list[float] = []
                any_present = False
                for gy in range(y0, y0 + lh):
                    for gx in range(x0, x0 + lw):
                        v = cell_fn(gx, gy, name)
                        if v is None:
                            vals.append(0.0)  # placeholder; only used if field present
                        else:
                            any_present = True
                            vals.append(v)
                present.append(any_present)
                packed_per_field.append(_pack_field(f, vals) if any_present else b"")

            mask = bytearray(mask_bytes)
            for i, p in enumerate(present):
                if p:
                    mask[i >> 3] |= 1 << (i & 7)  # LSB-first

            blob = bytearray()
            blob += b"GMVC"
            blob += struct.pack("<H", 1)              # version u16
            blob += struct.pack("<i", x0 // chunk)    # coord.x = CHUNK INDEX (not cell origin)
            blob += struct.pack("<i", y0 // chunk)    # coord.y = CHUNK INDEX
            blob += struct.pack("<h", 0)              # coord.z i16
            blob += struct.pack("<I", cell_count)  # cellCount u32
            blob += struct.pack("<H", n_fields)   # nFields u16
            blob += bytes(mask)                    # presence mask
            blob += struct.pack("<B", 0)          # compressionFlag u8 = 0
            for i, f in enumerate(fields):
                if not present[i]:
                    continue
                body = packed_per_field[i]
                blob += struct.pack("<I", len(body))  # packedLen u32
                blob += body

            (out / "chunks" / f"c_{x0}_{y0}_0.gmvc").write_bytes(bytes(blob))

    # --- sidecars ---
    wj = world_json or {
        "contract_version": "theomen.world.v1",
        "generator": "theomen",
        "seed": 42,
        "grid": {"width": width, "height": height, "downsample": 1, "cell_km": 20.0},
        "topology": {"wrap_x": True, "clamp_y": True},
        "elevation": {"datum": "relative_to_sea_level", "sea_level_value": 0.0, "unit": "m"},
        "thresholds": {
            "river_min_catchment_cells": 1500.0,
            "lake_min_depth_m": 15.0,
            "cell_area_km2": 400.0,
        },
        "resources": {
            "encoding": "log10_per_type",
            "log_decades": 8.0,
            "floor01": 1.0 / 255.0,
            "absence_value": 0,
            "layers": [],
        },
        "sidecars": ["biomes.json"],
    }
    (out / "world.json").write_text(json.dumps(wj, indent=2), encoding="utf-8")

    bj = biomes if biomes is not None else [
        {"id": 0, "name": "ocean", "color": "#1a3d6b"},
        {"id": 1, "name": "temperate_forest", "color": "#3f8f43"},
        {"id": 2, "name": "alpine", "color": "#c9d6e0"},
    ]
    # Real Theomen ships biomes.json WRAPPED as {"biomes": [...]}, not a bare list
    # (verified on a real export). Mirror that shape so tests exercise the real form.
    (out / "biomes.json").write_text(json.dumps({"biomes": bj}, indent=2), encoding="utf-8")

    # Extra name sidecars (terrain_types.json / deposits.json / features.json).
    for fname, entries in (sidecars or {}).items():
        (out / fname).write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return out
