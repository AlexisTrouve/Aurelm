"""The GMVC decoder must read back exactly what the spec-faithful fixture wrote.

The fixture (bot/tests/fixtures/world_fixture.py) encodes bytes straight from
SPEC_WORLD_FORMAT.md §2-§3; this test decodes them back. Encoder and decoder are
independent implementations of the same written spec, so agreement is evidence the
spec was read correctly on both sides (Theomen's real export is the final proof).

Exercises the three things that would silently corrupt an ingest: partial edge
chunks (stride = real width, not chunkDims), the LSB-first presence mask, and
field sparsity (absent ≠ 0).
"""
from __future__ import annotations

from bot.tests.fixtures.world_fixture import build_world
from bot.world_reader import read_world

FIELDS = [
    {"name": "elevation", "encoding": "float32"},
    {"name": "biome", "encoding": "float32"},
    {"name": "res_iron", "encoding": "unorm8"},
]


def _cell_fn(gx: int, gy: int, name: str):
    if name == "elevation":
        return float(gx * 100 + gy)          # unique per cell → proves placement
    if name == "biome":
        return float((gx + gy) % 3)          # index 0/1/2
    if name == "res_iron":
        # Present ONLY in chunk (0,0): every other chunk has it fully absent.
        return float((gx + gy) % 19 + 1) if (gx < 4 and gy < 4) else None
    return None


def _build(tmp_path):
    # 6x5, chunk 4 → chunks (0,0)=4x4, (4,0)=2x4, (0,4)=4x1, (4,4)=2x1: partial in both axes.
    return build_world(tmp_path / "w", width=6, height=5, chunk=4,
                       fields=FIELDS, cell_fn=_cell_fn)


def test_header_reads_world_json_and_biomes(tmp_path):
    w = read_world(_build(tmp_path))
    h = w.header
    assert h.contract_version == "theomen.world.v1"
    assert (h.width, h.height) == (6, 5)
    assert h.cell_km == 20.0            # from grid.cell_km, NOT manifest.cellSize
    assert h.wrap_x is True
    assert h.biomes[0]["name"] == "ocean"
    assert h.biomes[1]["name"] == "temperate_forest"


def test_decodes_every_cell_with_correct_placement(tmp_path):
    w = read_world(_build(tmp_path))
    cells = {(c["x"], c["y"]): c for c in w.cells()}

    # All 30 cells present exactly once (proves partial-edge stride is right).
    assert len(cells) == 6 * 5
    for gx in range(6):
        for gy in range(5):
            assert cells[(gx, gy)]["elevation"] == float(gx * 100 + gy)
            assert cells[(gx, gy)]["biome"] == float((gx + gy) % 3)


def test_field_sparsity_absent_is_not_zero(tmp_path):
    w = read_world(_build(tmp_path))
    cells = {(c["x"], c["y"]): c for c in w.cells()}

    # res_iron present in chunk (0,0): decoded as raw/255.
    assert cells[(2, 3)]["res_iron"] == (float((2 + 3) % 19 + 1)) / 255.0
    # ...and ABSENT (key missing, not 0) everywhere else — the sparsity contract.
    assert "res_iron" not in cells[(5, 4)]   # chunk (4,4)
    assert "res_iron" not in cells[(4, 0)]   # chunk (4,0)
    assert "res_iron" not in cells[(0, 4)]   # chunk (0,4)


def test_partial_edge_chunk_columns_are_not_shifted(tmp_path):
    """The classic bug: using chunkDims (4) as stride on a 2-wide edge chunk shifts
    every column. Spot-check cells that only decode right with stride = real width."""
    w = read_world(_build(tmp_path))
    cells = {(c["x"], c["y"]): c for c in w.cells()}
    assert cells[(5, 0)]["elevation"] == 500.0   # chunk (4,0), local (1,0)
    assert cells[(5, 4)]["elevation"] == 504.0   # chunk (4,4), local (1,0)
    assert cells[(0, 4)]["elevation"] == 4.0     # chunk (0,4), local (0,0)
