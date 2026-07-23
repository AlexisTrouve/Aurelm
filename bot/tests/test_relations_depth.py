"""Relations: the WHY of each link, and multi-hop chains.

Two defects this locks:
1. get_entity_detail SELECTed the relation description and unpacked it into `_desc` --
   deliberately unused. The agent saw "A -allied_with-> B" and could never say why.
2. explore_relations (depth<=3) sat in dispatch but was ADVERTISED nowhere, so the model
   could not call it: "trace how A relates to C through B" was unanswerable. It is now
   reachable as getEntityDetail(relationDepth=2..3), keeping one entity tool.
"""
from __future__ import annotations

from bot.tools import dispatch_tool


def _link(db, src, tgt, rel_type, desc):
    db.execute(
        "INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type,"
        " description, turn_id) VALUES (?,?,?,?,1)", (src, tgt, rel_type, desc))
    db.commit()


def test_relation_detail_is_shown_not_dropped(db):
    _link(db, 1, 2, "member_of", "liee a la caste depuis la decouverte des ruines")
    out = dispatch_tool(db, "getEntityDetail",
                        {"entityName": "Argile Vivante", "relations": True})
    assert "member_of" in out
    assert "decouverte des ruines" in out, "the WHY of the link must reach the agent"


def test_relation_detail_survives_a_pipe_in_the_text(db):
    # A raw '|' would break the Markdown table and silently mangle the row.
    _link(db, 1, 2, "member_of", "avant | apres")
    out = dispatch_tool(db, "getEntityDetail",
                        {"entityName": "Argile Vivante", "relations": True})
    rows = [l for l in out.splitlines() if "member_of" in l]
    assert rows, "the relation row must render"
    assert rows[0].count("|") == 7, f"table row must keep its 6 columns: {rows[0]}"


def test_relation_depth_reaches_indirect_chains(db):
    # 1 -> 2 -> 3 : entity 3 is invisible at depth 1, reachable at depth 2.
    _link(db, 1, 2, "member_of", "lien direct")
    _link(db, 2, 3, "worships", "lien indirect")

    shallow = dispatch_tool(db, "getEntityDetail",
                            {"entityName": "Argile Vivante", "relations": True})
    deep = dispatch_tool(db, "getEntityDetail",
                         {"entityName": "Argile Vivante", "relationDepth": 2})

    assert "Caste du Feu" not in shallow, "depth 1 must not reach the second hop"
    assert "Caste du Feu" in deep, "depth 2 must surface the indirect chain"


def test_relation_depth_is_capped_and_tolerates_garbage(db):
    _link(db, 1, 2, "member_of", "x")
    assert "Erreur" not in dispatch_tool(
        db, "getEntityDetail", {"entityName": "Argile Vivante", "relationDepth": 99})
    # A non-numeric depth must fall back to the normal detail view, not crash.
    out = dispatch_tool(db, "getEntityDetail",
                        {"entityName": "Argile Vivante", "relationDepth": "abc"})
    assert "Argile Vivante" in out
