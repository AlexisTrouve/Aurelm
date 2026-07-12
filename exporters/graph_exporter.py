"""Graph exporter — renders a laid-out ego-graph to PNG + SVG.

WHAT: Takes a center entity, builds its ego-graph (ego_graph.py), and draws it
with matplotlib: nodes coloured by entity_type, edges coloured & labelled by
relation_type, a centred hub with rings by depth, plus a small legend.

WHY matplotlib (not a headless browser): self-contained, pure-Python, embeds a
CJK-capable font so Chinese names render, and produces both a raster (PNG) and a
vector (SVG) artefact. SVG text is exported as paths so the file is portable
even without the font installed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless: render to files, never open a window

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

from . import db  # noqa: E402
from .ego_graph import build_ego_graph  # noqa: E402
from .models import EgoGraph  # noqa: E402
from .style import ExportStyle  # noqa: E402

# Node radii (data units) per depth — proportional to ego_painter.dart's 28/20/14 px.
_NODE_RADIUS = {0: 0.13, 1: 0.09}
_NODE_RADIUS_DEEP = 0.065  # depth >= 2


def _node_radius(depth: int) -> float:
    return _NODE_RADIUS.get(depth, _NODE_RADIUS_DEEP)


def _font(style: ExportStyle) -> FontProperties:
    """Resolve a FontProperties, CJK-capable when a font is available."""
    path = style.resolve_font_path()
    return FontProperties(fname=path) if path else FontProperties()


def render_ego_graph(
    ego: EgoGraph,
    out_base: str,
    formats: tuple[str, ...] = ("png", "svg"),
    title: str | None = None,
    style: ExportStyle | None = None,
) -> dict[str, str]:
    """Render a pre-built ego-graph to <out_base>.<fmt> for each format.

    Returns {format: path}. Splitting build from render keeps the layout
    testable without matplotlib.
    """
    style = style or ExportStyle()
    fp = _font(style)
    # Export SVG text as vector paths so CJK renders without the font present.
    matplotlib.rcParams["svg.fonttype"] = "path"

    fig, ax = plt.subplots(figsize=(11, 11))
    fig.set_facecolor(style.background)
    ax.set_facecolor(style.background)
    ax.set_aspect("equal")
    ax.axis("off")

    pos = {n.id: (n.x, n.y) for n in ego.nodes}

    # --- edges (drawn first, under the nodes) ---
    for e in ego.edges:
        if e.source_id not in pos or e.target_id not in pos:
            continue
        x1, y1 = pos[e.source_id]
        x2, y2 = pos[e.target_id]
        # trim endpoints to the node borders so lines don't stab through discs
        dx, dy = x2 - x1, y2 - y1
        dist = (dx * dx + dy * dy) ** 0.5 or 1.0
        ux, uy = dx / dist, dy / dist
        r1 = _node_radius(ego.node(e.source_id).depth)
        r2 = _node_radius(ego.node(e.target_id).depth)
        sx, sy = x1 + ux * r1, y1 + uy * r1
        tx, ty = x2 - ux * r2, y2 - uy * r2
        color = style.relation_color(e.relation_type)
        ax.plot([sx, tx], [sy, ty], color=color, alpha=0.5, linewidth=1.5, zorder=1)
        # relation label at the midpoint, on a light pill for legibility
        mx, my = (sx + tx) / 2, (sy + ty) / 2
        ax.text(
            mx, my, e.relation_type.replace("_", " "),
            fontproperties=fp, fontsize=6.5, color="#333333", ha="center", va="center",
            zorder=2, bbox=dict(boxstyle="round,pad=0.15", fc=style.background, ec="none", alpha=0.75),
        )

    # --- nodes ---
    for n in ego.nodes:
        rad = _node_radius(n.depth)
        color = style.entity_color(n.entity_type)
        alpha = 0.9 if n.depth == 0 else 0.7
        lw = 2.5 if n.depth == 0 else 1.5
        ax.add_patch(Circle((n.x, n.y), rad, facecolor=color, edgecolor=color,
                            linewidth=lw, alpha=alpha, zorder=3))
        # label below the node
        fs = 11 if n.depth == 0 else (9 if n.depth == 1 else 7.5)
        weight = "bold" if n.depth == 0 else "normal"
        ax.text(
            n.x, n.y - rad - 0.05, n.name,
            fontproperties=fp, fontsize=fs, fontweight=weight, color="#111111",
            ha="center", va="top", zorder=4,
            bbox=dict(boxstyle="round,pad=0.12", fc=style.background, ec="none", alpha=0.8),
        )

    _add_legend(ax, ego, style, fp)
    if title:
        ax.set_title(title, fontproperties=fp, fontsize=15, fontweight="bold", color="#111111")

    # frame the drawing with a margin around the node extent
    xs = [n.x for n in ego.nodes] or [0.0]
    ys = [n.y for n in ego.nodes] or [0.0]
    margin = 0.6
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin - 0.3, max(ys) + margin)

    out_base_path = Path(out_base)
    out_base_path.parent.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for fmt in formats:
        path = f"{out_base}.{fmt}"
        fig.savefig(path, format=fmt, dpi=150, facecolor=style.background, bbox_inches="tight")
        written[fmt] = path
    plt.close(fig)
    return written


def _add_legend(ax, ego: EgoGraph, style: ExportStyle, fp: FontProperties) -> None:
    """Draw a compact legend of the entity types and relation types present."""
    from matplotlib.lines import Line2D

    types = sorted({n.entity_type for n in ego.nodes})
    rels = sorted({e.relation_type for e in ego.edges})
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=style.entity_color(t),
               markersize=9, label=t)
        for t in types
    ] + [
        Line2D([0], [0], color=style.relation_color(r), linewidth=2, label=r.replace("_", " "))
        for r in rels
    ]
    if handles:
        leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0),
                        fontsize=8, frameon=True, title="Legend")
        leg.get_title().set_fontproperties(fp)
        for txt in leg.get_texts():
            txt.set_fontproperties(fp)


def export_graph(
    db_path: str,
    center: str | int,
    out_base: str,
    depth: int = 1,
    entity_type: str | None = None,
    formats: tuple[str, ...] = ("png", "svg"),
    title: str | None = None,
    style: ExportStyle | None = None,
) -> dict[str, str]:
    """Top-level: resolve center, build the ego-graph, render it to files.

    ``center`` may be an entity id (int) or a name (str, resolved via aliases).
    """
    conn = db.get_connection(db_path)
    center_id = center if isinstance(center, int) else db.resolve_entity_id(conn, center)
    ego = build_ego_graph(conn, center_id, depth=depth, entity_type=entity_type)
    if title is None:
        center_node = ego.node(center_id)
        title = center_node.name if center_node else None
    result = render_ego_graph(ego, out_base, formats=formats, title=title, style=style)
    result["nodes"] = str(len(ego.nodes))
    result["edges"] = str(len(ego.edges))
    return result
