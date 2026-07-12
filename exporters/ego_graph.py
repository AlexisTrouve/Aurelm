"""Ego-graph construction + radial layout.

WHAT: Given a center entity, build its neighbourhood up to a given depth
(BFS over the relation graph), optionally restricted to one entity type, then
assign each node a radial (x, y) position.

WHY radial + rings-by-depth: this reproduces Aurelm's in-app ego-graph look
(gui/.../ego_painter.dart) — a centred hub, a first ring evenly spaced from 12
o'clock, and deeper rings clustered near their parent — so headless exports feel
like the GUI. We recompute the layout in Python (no Dart reuse) in abstract
data units; the renderer scales them to pixels.

WHY filter-then-BFS: for a "persons only" mindmap we want the network of
same-type entities, so we drop other types BEFORE traversing (the center is
always kept even if it fails the filter) — otherwise a person reachable only
through a place would vanish or the graph would fragment confusingly.
"""

from __future__ import annotations

import math

import networkx as nx

from . import db
from .models import EgoGraph, GraphEdge, GraphNode

# Layout constants — chosen so ring2/ring1 ≈ 1.7 (mirrors ego_painter.dart's
# 0.48/0.30 ratio). Units are abstract; the renderer maps them to pixels.
_R1 = 1.0          # radius of the first ring (direct neighbours)
_RING_GAP = 0.7    # extra radius per deeper ring
_WEDGE = math.pi / 4  # ±45° spread for clustering children under a parent


def build_ego_graph(
    conn,
    center_id: int,
    depth: int = 1,
    entity_type: str | None = None,
    active_relations_only: bool = False,
) -> EgoGraph:
    """Build (unlaid) the ego graph around ``center_id`` up to ``depth`` hops.

    ``entity_type`` restricts neighbours to that type (center always kept).
    """
    entities = {e.id: e for e in db.fetch_all_entities(conn)}
    if center_id not in entities:
        raise LookupError(f"Center entity id {center_id} not found")
    relations = db.fetch_all_relations(conn, active_only=active_relations_only)

    # Allowed node set: everything of the wanted type, plus the center itself.
    if entity_type is not None:
        allowed = {eid for eid, e in entities.items() if e.entity_type == entity_type}
        allowed.add(center_id)
    else:
        allowed = set(entities)

    # Undirected graph over allowed nodes only (so BFS stays within the type).
    g = nx.Graph()
    g.add_nodes_from(allowed)
    for r in relations:
        if r.source_id in allowed and r.target_id in allowed and r.source_id != r.target_id:
            g.add_edge(r.source_id, r.target_id)

    # BFS depth from the center (bounded by ``depth``).
    depths = nx.single_source_shortest_path_length(g, center_id, cutoff=depth)

    nodes = [
        GraphNode(
            id=eid,
            name=entities[eid].canonical_name,
            entity_type=entities[eid].entity_type,
            depth=d,
        )
        for eid, d in depths.items()
    ]
    kept = set(depths)

    # Keep every distinct (pair, relation_type) whose endpoints are both in view.
    seen: set[tuple[int, int, str]] = set()
    edges: list[GraphEdge] = []
    for r in relations:
        if r.source_id in kept and r.target_id in kept and r.source_id != r.target_id:
            key = (min(r.source_id, r.target_id), max(r.source_id, r.target_id), r.relation_type)
            if key in seen:
                continue
            seen.add(key)
            edges.append(GraphEdge(r.source_id, r.target_id, r.relation_type, r.description))

    ego = EgoGraph(center_id=center_id, nodes=nodes, edges=edges)
    layout_radial(ego)
    return ego


def _radius_for_depth(d: int) -> float:
    """Ring radius for a given BFS depth (0 at center)."""
    if d <= 0:
        return 0.0
    if d == 1:
        return _R1
    return _R1 + (d - 1) * _RING_GAP


def layout_radial(ego: EgoGraph) -> None:
    """Fill node.x / node.y with a radial layout (mutates ego in place).

    COMMENT: center at origin; ring 1 evenly spaced starting at 12 o'clock
    (angle = 2πi/n − π/2, matching ego_painter.dart); deeper rings cluster each
    child within ±45° of its parent's angle, falling back to even spacing when a
    node has no positioned parent. Ordering by id keeps the layout deterministic.
    """
    center = ego.node(ego.center_id)
    if center is not None:
        center.x, center.y = 0.0, 0.0

    # adjacency for parent lookup
    adj: dict[int, set[int]] = {}
    for e in ego.edges:
        adj.setdefault(e.source_id, set()).add(e.target_id)
        adj.setdefault(e.target_id, set()).add(e.source_id)

    # Ring 1: even distribution from the top.
    ring1 = sorted((n for n in ego.nodes if n.depth == 1), key=lambda n: n.id)
    for i, n in enumerate(ring1):
        ang = 2 * math.pi * i / max(len(ring1), 1) - math.pi / 2
        n.x, n.y = _R1 * math.cos(ang), _R1 * math.sin(ang)

    # Deeper rings: cluster near a parent at depth-1.
    max_depth = max((n.depth for n in ego.nodes), default=0)
    for d in range(2, max_depth + 1):
        r = _radius_for_depth(d)
        ring = sorted((n for n in ego.nodes if n.depth == d), key=lambda n: n.id)
        by_parent: dict[int, list[GraphNode]] = {}
        orphans: list[GraphNode] = []
        for n in ring:
            parents = [p for p in adj.get(n.id, ()) if (ego.node(p) and ego.node(p).depth == d - 1)]
            if parents:
                by_parent.setdefault(min(parents), []).append(n)
            else:
                orphans.append(n)

        for pid, children in by_parent.items():
            pnode = ego.node(pid)
            pang = math.atan2(pnode.y, pnode.x)
            k = len(children)
            for i, ch in enumerate(children):
                off = 0.0 if k == 1 else (-_WEDGE / 2 + _WEDGE * i / (k - 1))
                ang = pang + off
                ch.x, ch.y = r * math.cos(ang), r * math.sin(ang)

        for i, ch in enumerate(orphans):
            ang = 2 * math.pi * i / max(len(orphans), 1) - math.pi / 2
            ch.x, ch.y = r * math.cos(ang), r * math.sin(ang)
