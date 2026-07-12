"""Regression (feedback P3): a seeded canonical name must win the alias merge.

The alias resolver kept the entity with the most mentions as the surviving
"primary". On a seeded corpus that is wrong: a frequently-used epithet ("Sage")
would displace the real, ground-truth name ("Front-Levé") as the character's
canonical name in the glossary and mindmap. `_choose_survivor` fixes this: a
name present in the seed set beats a non-seeded one regardless of mention count;
with no seed (the civ path) the historical mention-count rule is preserved.
"""

from __future__ import annotations

from pipeline.alias_resolver import _choose_survivor
from pipeline.entity_profiler import EntityProfile


def _prof(entity_id: int, name: str, mentions: int) -> EntityProfile:
    """Minimal EntityProfile fixture — only the fields the survivor rule reads."""
    return EntityProfile(
        entity_id=entity_id,
        canonical_name=name,
        entity_type="person",
        civ_id=1,
        mention_count=mentions,
    )


def test_seeded_name_beats_more_frequent_epithet():
    # The epithet is mentioned more often, yet the seeded real name must survive.
    real = _prof(1, "Front-Levé", mentions=3)
    epithet = _prof(2, "Sage", mentions=20)
    seed = {"Front-Levé"}

    primary, alias_ent = _choose_survivor(epithet, real, seed)
    assert primary.canonical_name == "Front-Levé"
    assert alias_ent.canonical_name == "Sage"

    # Order-independent: same outcome whichever side is passed first.
    primary2, _ = _choose_survivor(real, epithet, seed)
    assert primary2.canonical_name == "Front-Levé"


def test_both_seeded_falls_back_to_mention_count():
    a = _prof(1, "Oracle", mentions=5)
    b = _prof(2, "Cendre", mentions=12)
    seed = {"Oracle", "Cendre"}
    primary, _ = _choose_survivor(a, b, seed)
    assert primary.canonical_name == "Cendre"  # more mentions wins the tie


def test_neither_seeded_uses_mention_count():
    a = _prof(1, "Alpha", mentions=2)
    b = _prof(2, "Beta", mentions=9)
    seed = {"SomeoneElse"}
    primary, _ = _choose_survivor(a, b, seed)
    assert primary.canonical_name == "Beta"


def test_civ_path_no_seed_is_unchanged():
    # civ passes no seed set (None or empty) → pure mention-count behaviour,
    # byte-identical to the historical rule. Ties keep the first argument (>=).
    a = _prof(1, "Confluence", mentions=10)
    b = _prof(2, "Les Confluents", mentions=10)
    for seed in (None, set()):
        primary, alias_ent = _choose_survivor(a, b, seed)
        assert primary.canonical_name == "Confluence"      # a wins the >= tie
        assert alias_ent.canonical_name == "Les Confluents"
