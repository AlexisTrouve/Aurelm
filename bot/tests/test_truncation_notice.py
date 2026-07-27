"""A truncated list must SAY it is truncated.

Every list tool caps with a bare LIMIT. Silently returning a slice is the worst kind of
failure here: the agent believes it holds everything and answers "voici toutes les
entites militaires" from a subset -- confidently wrong, and the GM has no way to notice.
This does not lose data, it manufactures false certainty.
"""
from __future__ import annotations

from bot.tools import dispatch_tool


def _many_entities(db, n=8):
    for i in range(n):
        db.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, description)"
            " VALUES (?, 'person', 1, 'garde')", (f"Garde {i}",))
    db.commit()


def test_search_lore_says_when_it_truncated(db):
    _many_entities(db)  # 8 "Garde" + whatever the fixture seeds
    out = dispatch_tool(db, "searchLore", {"query": "Garde", "limit": 3})
    assert "tronquee" in out.lower(), "a capped list must announce it is incomplete"
    assert "limit" in out, "and tell the agent how to get more"
    # The REAL total must appear, not just "there are more" — otherwise the agent
    # invents a count (measured live: it answered "41 entites" from a 20-row slice).
    assert "sur 8 au total" in out, f"the true total must be surfaced: {out[-200:]}"
    assert "extrapole" in out.lower(), "and it must be told not to guess the rest"


def test_search_lore_stays_silent_when_complete(db):
    _many_entities(db, n=2)
    out = dispatch_tool(db, "searchLore", {"query": "Garde", "limit": 20})
    assert "tronquee" not in out.lower(), "no false alarm on a complete list"


def test_exactly_at_the_limit_is_not_flagged(db):
    """The off-by-one that a naive `len(rows) == limit` check would get wrong."""
    _many_entities(db, n=3)
    out = dispatch_tool(db, "searchLore", {"query": "Garde", "limit": 3})
    assert "tronquee" not in out.lower(), "3 results with limit 3 is complete, not truncated"


def test_timeline_and_subjects_also_announce_truncation(db):
    for i in range(3):
        db.execute(
            "INSERT INTO subject_subjects (civ_id, source_turn_id, title, category,"
            " direction, status) VALUES (1, 1, ?, 'choice', 'mj_to_pj', 'open')",
            (f"Decision en attente {i}",))
    db.commit()

    tl = dispatch_tool(db, "timeline", {"limit": 1})
    assert "tronquee" in tl.lower(), "timeline must announce its cut too"

    subj = dispatch_tool(db, "listSubjects", {"limit": 1})
    assert "tronquee" in subj.lower(), "a missed pending decision is the costliest silence"
