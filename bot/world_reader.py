"""Read a Theomen `.world` (GMVC) export — pure stdlib, no numpy.

WHAT: decode the binary world-document Theomen produces (`manifest.json` +
`chunks/c_x_y_0.gmvc` + the `world.json` business sidecar) into per-cell records.
Contract + byte layout: `Gamedesigner/theomen/docs/SPEC_WORLD_FORMAT.md`.

WHY stdlib and not numpy: the shipped bot runtime has only 5 deps (discord/openai/
aiohttp/httpx/ollama). Theomen guarantees every field is BYTE-ALIGNED (float32=32,
unorm8=8, future indices as uint bits=8), so the spec's bit-packing degenerates to
contiguous arrays and `struct`/`array` decode them directly — no bit unpacker, no
new dependency.

COMMENT: the decoder is GENERIC over `manifest.fields` — it decodes whatever fields
are declared, so Theomen can add `feature`/`deposit`/`terrain_type`/hydrology layers
incrementally without a reader change. The blob header (coord + cellCount) is the
source of truth for cell placement, never the filename (SPEC §3.3).
"""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Iterator

MAGIC = b"GMVC"
BYTE_ALIGNED_ENC = {"float32", "unorm8", "unorm16"}


@dataclass
class WorldHeader:
    """Business + technical metadata, merged from world.json and manifest.json."""
    contract_version: str
    seed: int | None
    width: int
    height: int
    cell_km: float
    wrap_x: bool
    clamp_y: bool
    sea_level_m: float
    thresholds: dict
    # res_<field> -> {"type","max_mass","total_mass"} for the log inversion (SPEC §5).
    resource_layers: dict[str, dict]
    # Global params of the log10-per-type resource encoding (SPEC §5 inversion).
    res_floor01: float
    res_log_decades: float
    # manifest field name -> its manifest dict ({"name","encoding",["bits","scale","offset"]}).
    fields: dict[str, dict]
    chunk_dims: tuple[int, int]
    # id -> {"name","color"} from biomes.json (empty if the sidecar is absent).
    biomes: dict[int, dict] = dc_field(default_factory=dict)
    # other name sidecars: {"deposits": {id: {...}}, "features": {...}, "terrain_types": {...}}
    name_maps: dict[str, dict] = dc_field(default_factory=dict)


class World:
    """A decoded `.world`: its header plus a per-cell iterator."""

    def __init__(self, world_dir: str | Path):
        self.dir = Path(world_dir)
        self._manifest = json.loads((self.dir / "manifest.json").read_text("utf-8"))
        if self._manifest.get("formatVersion") != 1:
            raise ValueError(
                f"unsupported manifest formatVersion {self._manifest.get('formatVersion')!r} "
                "(reader speaks formatVersion 1)"
            )
        self.header = self._build_header()

    # -- header assembly -----------------------------------------------------

    def _build_header(self) -> WorldHeader:
        wj_path = self.dir / "world.json"
        wj = json.loads(wj_path.read_text("utf-8")) if wj_path.exists() else {}
        coord = self._manifest["coordinate"]
        bounds = coord["bounds"]
        # bounds.max is INCLUSIVE (SPEC §2): width = max.x - min.x + 1.
        width = bounds["max"][0] - bounds["min"][0] + 1
        height = bounds["max"][1] - bounds["min"][1] + 1
        cdx, cdy = coord["chunkDims"][0], coord["chunkDims"][1]

        grid = wj.get("grid", {})
        topo = wj.get("topology", {})
        elev = wj.get("elevation", {})
        res = wj.get("resources", {})
        res_layers = {L["field"]: L for L in res.get("layers", []) if "field" in L}

        fields = {f["name"]: f for f in self._manifest.get("fields", [])}

        # Name sidecars: a list of {id, name, ...}. Theomen's real biomes.json wraps it
        # as {"biomes": [...]} (verified on a real export), so accept both a bare list
        # and a dict wrapping the list under `wrap_key` (or any list-valued key).
        def _entries(path: Path, wrap_key: str) -> dict:
            if not path.exists():
                return {}
            data = json.loads(path.read_text("utf-8"))
            if isinstance(data, dict):
                data = (data.get(wrap_key)
                        or next((v for v in data.values() if isinstance(v, list)), []))
            return {int(e["id"]): e for e in data if isinstance(e, dict) and "id" in e}

        biomes = _entries(self.dir / "biomes.json", "biomes")
        name_maps: dict[str, dict] = {}
        for key, fname in (("features", "features.json"),
                           ("deposits", "deposits.json"),
                           ("terrain_types", "terrain_types.json")):
            entries = _entries(self.dir / fname, key)
            if entries:
                name_maps[key] = entries

        return WorldHeader(
            contract_version=wj.get("contract_version", ""),
            seed=wj.get("seed"),
            # world.json grid is authoritative for physical scale; fall back to the
            # manifest bounds for the raw dimensions if world.json is absent.
            width=grid.get("width", width),
            height=grid.get("height", height),
            cell_km=float(grid.get("cell_km", 0.0)),  # SPEC §world.json rule 1: NOT manifest.cellSize
            wrap_x=bool(topo.get("wrap_x", False)),
            clamp_y=bool(topo.get("clamp_y", True)),
            sea_level_m=float(elev.get("sea_level_value", 0.0)),
            thresholds=wj.get("thresholds", {}),  # top-level in world.json v1
            resource_layers=res_layers,
            res_floor01=float(res.get("floor01", 1.0 / 255.0)),
            res_log_decades=float(res.get("log_decades", 8.0)),
            fields=fields,
            chunk_dims=(cdx, cdy),
            biomes=biomes,
            name_maps=name_maps,
        )

    # -- cell decoding -------------------------------------------------------

    def cells(self) -> Iterator[dict]:
        """Yield one dict per cell: {"x","y", <present field decoded>, ...}.

        x,y are GLOBAL cell coordinates. Only fields PRESENT in a cell's chunk
        appear in its dict (absence ≠ 0, SPEC §3.4) — callers test membership.
        Values are the physical decode (SPEC §3.2): float32→float, unorm8→raw/255
        (u01), uint/int bits=N→int*scale+offset.
        """
        schema = self._manifest["coordinate"]
        cdx, cdy = schema["chunkDims"][0], schema["chunkDims"][1]
        field_list = self._manifest.get("fields", [])
        n_fields = len(field_list)
        mask_bytes = (n_fields + 7) // 8
        width = self.header.width

        for blob_path in sorted((self.dir / "chunks").glob("c_*_*_*.gmvc")):
            buf = blob_path.read_bytes()
            off = 0

            def take(fmt: str):
                nonlocal off
                sz = struct.calcsize(fmt)
                vals = struct.unpack_from("<" + fmt, buf, off)
                off += sz
                return vals

            if buf[off:off + 4] != MAGIC:
                raise ValueError(f"{blob_path.name}: bad magic {buf[:4]!r}")
            off += 4
            (version,) = take("H")
            if version != 1:
                raise ValueError(f"{blob_path.name}: unsupported chunk version {version}")
            # coord.x/coord.y are CHUNK INDICES (verified against a real Theomen export:
            # coords are 0,1,2..., not 0,128,256...). Cell origin = index * chunkDims.
            (cix,) = take("i")
            (ciy,) = take("i")
            (_z0,) = take("h")
            x0, y0 = cix * cdx, ciy * cdy
            (cell_count,) = take("I")
            (blob_nfields,) = take("H")
            if blob_nfields != n_fields:
                raise ValueError(
                    f"{blob_path.name}: chunk declares {blob_nfields} fields, "
                    f"manifest has {n_fields}"
                )
            mask = buf[off:off + mask_bytes]
            off += mask_bytes
            (compression,) = take("B")
            if compression != 0:
                raise ValueError(
                    f"{blob_path.name}: compressed chunks are not supported "
                    "(Theomen writes flag 0)"
                )

            # Real chunk width from the manifest + this chunk's origin (SPEC §3.3).
            lw = min(cdx, width - x0)
            if lw <= 0 or cell_count % lw != 0:
                raise ValueError(
                    f"{blob_path.name}: inconsistent cellCount {cell_count} for width {lw}"
                )
            lh = cell_count // lw

            # Decode each PRESENT field's cellCount values (schema order).
            decoded: dict[str, list] = {}
            for i, f in enumerate(field_list):
                present = bool(mask[i >> 3] & (1 << (i & 7)))  # LSB-first
                if not present:
                    continue
                (packed_len,) = take("I")
                body = buf[off:off + packed_len]
                off += packed_len
                decoded[f["name"]] = _decode_field(f, body, cell_count)

            for ly in range(lh):
                for lx in range(lw):
                    idx = ly * lw + lx
                    cell = {"x": x0 + lx, "y": y0 + ly}
                    for name, arr in decoded.items():
                        cell[name] = arr[idx]
                    yield cell


def _decode_field(f: dict, body: bytes, cell_count: int) -> list:
    """Decode one field's byte-aligned body into physical values (SPEC §3.1-§3.2)."""
    enc = f["encoding"]
    scale = float(f.get("scale", 1.0))
    offset = float(f.get("offset", 0.0))

    if enc == "float32":
        return list(struct.unpack_from("<%df" % cell_count, body, 0))
    if enc == "unorm8":
        return [r / 255.0 for r in struct.unpack_from("<%dB" % cell_count, body, 0)]
    if enc == "unorm16":
        return [r / 65535.0 for r in struct.unpack_from("<%dH" % cell_count, body, 0)]
    if enc in ("uint", "int"):
        bits = int(f.get("bits", 8))
        if bits % 8 != 0:
            raise ValueError(
                f"field {f['name']!r}: {bits}-bit {enc} is not byte-aligned; "
                "Theomen guarantees uint/int fields are declared bits=8/16/32"
            )
        code = {8: "B", 16: "H", 32: "I"}[bits] if enc == "uint" else {8: "b", 16: "h", 32: "i"}[bits]
        raw = struct.unpack_from("<%d%s" % (cell_count, code), body, 0)
        return [r * scale + offset for r in raw]
    raise ValueError(f"field {f['name']!r}: unsupported encoding {enc!r}")


def read_world(world_dir: str | Path) -> World:
    """Open a `.world` directory for decoding."""
    return World(world_dir)
