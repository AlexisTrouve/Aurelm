"""Tests for the graph (image) exporter.

These are the E2E "the render actually happens" tests: they invoke matplotlib
and assert real PNG/SVG files are produced, including on the CJK node — a tofu
regression on Chinese text still writes a file, so we also assert the file is
non-trivial in size (a real drawing, not an empty canvas).
"""

from __future__ import annotations

from pathlib import Path

from exporters.graph_exporter import export_graph


def _png_signature(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(8) == b"\x89PNG\r\n\x1a\n"


def test_graph_renders_png_and_svg(sample_db, tmp_path):
    base = tmp_path / "g"
    result = export_graph(sample_db, center="Oracle", out_base=str(base), depth=2)
    png, svg = result["png"], result["svg"]
    assert _png_signature(png)
    assert Path(png).stat().st_size > 3000          # a real drawing
    svg_text = Path(svg).read_text(encoding="utf-8")
    assert "<svg" in svg_text
    assert int(result["nodes"]) >= 3


def test_graph_renders_with_cjk_center(sample_db, tmp_path):
    # Centering on the Chinese-named node must not crash and must draw.
    base = tmp_path / "gcjk"
    result = export_graph(sample_db, center="云隐", out_base=str(base), depth=1)
    assert _png_signature(result["png"])
    assert Path(result["png"]).stat().st_size > 3000


def test_graph_person_filter(sample_db, tmp_path):
    base = tmp_path / "gp"
    result = export_graph(sample_db, center="Oracle", out_base=str(base),
                          depth=2, entity_type="person")
    # Rivière (place) excluded -> 3 person nodes
    assert result["nodes"] == "3"


def test_graph_single_format(sample_db, tmp_path):
    base = tmp_path / "gonly"
    result = export_graph(sample_db, center="Oracle", out_base=str(base),
                          depth=1, formats=("png",))
    assert "png" in result and "svg" not in result
