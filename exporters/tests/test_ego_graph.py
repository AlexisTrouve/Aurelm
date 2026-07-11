"""Tests for ego-graph construction and radial layout."""

from __future__ import annotations

from exporters import db
from exporters.ego_graph import build_ego_graph


def test_person_filter_depth2(sample_db):
    conn = db.get_connection(sample_db)
    ego = build_ego_graph(conn, center_id=1, depth=2, entity_type="person")
    # persons only: Oracle(1, d0), 云隐(2, d1), Front-Levé(3, d2); Rivière(place) excluded
    depths = {n.id: n.depth for n in ego.nodes}
    assert depths == {1: 0, 2: 1, 3: 2}
    names = {n.id: n.name for n in ego.nodes}
    assert names[2] == "云隐"


def test_center_kept_even_if_not_of_filter_type(sample_db):
    # Center is a place; filter=person must still keep the center node.
    conn = db.get_connection(sample_db)
    ego = build_ego_graph(conn, center_id=4, depth=1, entity_type="person")
    assert ego.node(4) is not None
    assert ego.node(4).depth == 0


def test_edge_dedup_keeps_distinct_relation_types(sample_db):
    conn = db.get_connection(sample_db)
    ego = build_ego_graph(conn, center_id=1, depth=1)
    # pair (1,2) has both allied_with and worships -> two distinct edges kept
    pair_types = sorted(e.relation_type for e in ego.edges
                        if {e.source_id, e.target_id} == {1, 2})
    assert pair_types == ["allied_with", "worships"]


def test_layout_center_at_origin_and_ring_radii(sample_db):
    conn = db.get_connection(sample_db)
    ego = build_ego_graph(conn, center_id=1, depth=2, entity_type="person")
    center = ego.node(1)
    assert (center.x, center.y) == (0.0, 0.0)
    # depth-1 node sits on the unit ring (r1 = 1.0)
    d1 = ego.node(2)
    assert abs((d1.x ** 2 + d1.y ** 2) ** 0.5 - 1.0) < 1e-9
    # depth-2 node sits further out than depth-1
    d2 = ego.node(3)
    assert (d2.x ** 2 + d2.y ** 2) ** 0.5 > 1.0
