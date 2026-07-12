"""Regression: fuzzy entity matching must handle CJK names (cross-language seed).

The fuzzy prefilter skipped names shorter than 4 chars as noise — a latin-oriented
floor that dropped ALL Chinese aliases (2-3 chars), so a seeded ZH name like
煤灰 never resolved to its canonical FR entity. This locks the CJK-aware floor.
"""

from __future__ import annotations

from pipeline.fact_extractor import FactExtractor


def _fe() -> FactExtractor:
    # fuzzy_prefilter_entities doesn't touch the LLM, so skip __init__.
    return FactExtractor.__new__(FactExtractor)


def test_cjk_aliases_match_in_chinese_text():
    lookup = {
        "煤灰": {"canonical_name": "Grain-de-Suie", "entity_type": "person"},
        "神谕者": {"canonical_name": "Oracle", "entity_type": "person"},
        "细雨": {"canonical_name": "Pluie-Menue", "entity_type": "person"},
    }
    text = "在河边，煤灰看着神谕者，然后离开了。"   # has 煤灰 + 神谕者, not 细雨
    got = {m["canonical_name"] for m in _fe().fuzzy_prefilter_entities(text, lookup)}
    assert "Grain-de-Suie" in got     # 2-char CJK name resolved
    assert "Oracle" in got            # 3-char CJK name resolved
    assert "Pluie-Menue" not in got   # its alias is absent from the text


def test_short_latin_names_still_skipped():
    # The latin floor (>=4) is preserved: a 2-char latin alias stays filtered.
    lookup = {"ab": {"canonical_name": "Ab", "entity_type": "person"}}
    got = {m["canonical_name"] for m in _fe().fuzzy_prefilter_entities("ab cd ab", lookup)}
    assert got == set()
