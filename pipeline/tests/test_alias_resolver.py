"""Tests for alias_resolver — fuzzy name matching, description overlap, candidate detection."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pipeline.alias_resolver import (
    _normalize_tokens,
    _token_overlap,
    _description_overlap,
    _decide_by_score,
    find_alias_candidates,
    get_confirm_version,
    list_confirm_versions,
    AliasCandidate,
    ConfirmedAlias,
)
from pipeline.entity_profiler import EntityProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    entity_id: int,
    name: str,
    entity_type: str = "caste",
    description: str = "",
    aliases_suggested: list[str] | None = None,
    mention_count: int = 1,
    mention_contexts: list[str] | None = None,
) -> EntityProfile:
    return EntityProfile(
        entity_id=entity_id,
        canonical_name=name,
        entity_type=entity_type,
        civ_id=1,
        description=description,
        history=[],
        aliases_suggested=aliases_suggested or [],
        raw_relations=[],
        mention_count=mention_count,
        mention_contexts=mention_contexts or [],
    )


# ---------------------------------------------------------------------------
# _normalize_tokens
# ---------------------------------------------------------------------------

class TestNormalizeTokens:
    def test_simple_name(self):
        assert _normalize_tokens("Sans-ciels") == {"san", "ciel"}

    def test_plural_stemmed(self):
        # "ciels" → "ciel", "sages" → "sage"
        assert "ciel" in _normalize_tokens("Ciels-clairs")
        assert "sage" in _normalize_tokens("Cercle des Sages")

    def test_accent_stripped(self):
        # "Nés" → "ne" after accent strip + lowercase; but "nes" stripped of 's' → "ne"
        tokens = _normalize_tokens("Nés-sans-ciel")
        assert "ciel" in tokens
        assert "san" in tokens  # "sans" → stem "san"

    def test_stopwords_removed(self):
        tokens = _normalize_tokens("Cercle des Sages")
        assert "des" not in tokens
        assert "cercle" in tokens
        assert "sage" in tokens

    def test_articles_removed(self):
        tokens = _normalize_tokens("Le Cercle des Sages")
        assert "le" not in tokens
        assert "des" not in tokens

    def test_empty_string(self):
        assert _normalize_tokens("") == set()

    def test_single_word(self):
        tokens = _normalize_tokens("Rhombes")
        assert "rhombe" in tokens

    def test_compound_name(self):
        tokens = _normalize_tokens("Peuple du Ciel")
        assert "peuple" in tokens
        assert "ciel" in tokens
        assert "du" not in tokens


# ---------------------------------------------------------------------------
# _token_overlap
# ---------------------------------------------------------------------------

class TestTokenOverlap:
    def test_identical_names(self):
        assert _token_overlap("Sans-ciels", "Sans-ciels") == 1.0

    def test_clear_variant_ciel(self):
        # "Ciels-clairs" tokens: {ciel, clair}; "Ciels-libres": {ciel, libre}
        # Intersection: {ciel}; min(2,2)=2 → 0.5
        assert _token_overlap("Ciels-clairs", "Ciels-libres") == pytest.approx(0.5)

    def test_clear_variant_sans_ciel(self):
        # "Sans-ciels" → {san, ciel}; "Nés-sans-ciel" → {ne/nes, san, ciel}
        # Intersection: {san, ciel}; min(2,3)=2 → 1.0
        result = _token_overlap("Sans-ciels", "Nés-sans-ciel")
        assert result >= 0.5  # at least half the shorter name matches

    def test_cercle_sages_typo(self):
        # "Cercle des Sages" → {cercle, sage}; "Cercle de ses sages" → {cercle, sage}
        # Both reduce to {cercle, sage} → overlap 1.0
        assert _token_overlap("Cercle des Sages", "Cercle de ses sages") == pytest.approx(1.0)

    def test_rhombe_variant(self):
        # "Rhombes" → {rhombe}; "Rhombe sacré" → {rhombe, sacre}
        # Intersection: {rhombe}; min(1,2)=1 → 1.0
        assert _token_overlap("Rhombes", "Rhombe sacré") == pytest.approx(1.0)

    def test_unrelated_names(self):
        # Completely unrelated names should have zero or very low overlap
        result = _token_overlap("Sans-ciels", "Cercle des Sages")
        assert result < 0.5

    def test_empty_name(self):
        assert _token_overlap("", "Sans-ciels") == 0.0

    def test_peuple_ciel_variants(self):
        # "Peuple du ciel" → {peuple, ciel}; "Peuple des cieux" → {peuple, cieux→cieu}
        # "cieux" ends with 'x', not 's' → no stem → "cieux" ≠ "ciel"
        # Still "peuple" matches → 0.5
        result = _token_overlap("Peuple du ciel", "Peuple des cieux")
        assert result >= 0.5  # "peuple" token is shared


# ---------------------------------------------------------------------------
# find_alias_candidates — Signal 4 (fuzzy name)
# ---------------------------------------------------------------------------

class TestFindAliasCandidatesFuzzyName:
    def test_detects_ciel_variants(self):
        """Signal 4 should flag Ciels-clairs / Ciels-libres as candidates."""
        profiles = [
            _make_profile(1, "Ciels-clairs", "civilization"),
            _make_profile(2, "Ciels-libres", "civilization"),
            _make_profile(3, "Faucons Chasseurs", "caste"),  # unrelated, no noise
        ]
        candidates = find_alias_candidates(profiles)
        fuzzy = [c for c in candidates if c.source == "fuzzy_name"]
        names = {(c.entity_a.canonical_name, c.entity_b.canonical_name) for c in fuzzy}
        names |= {(b, a) for a, b in names}  # both directions
        assert ("Ciels-clairs", "Ciels-libres") in names

    def test_detects_sans_ciel_variant(self):
        """Signal 4 should flag Sans-ciels / Nés-sans-ciel as candidates."""
        profiles = [
            _make_profile(1, "Sans-ciels", "caste"),
            _make_profile(2, "Nés-sans-ciel", "caste"),
        ]
        candidates = find_alias_candidates(profiles)
        fuzzy = [c for c in candidates if c.source == "fuzzy_name"]
        assert len(fuzzy) >= 1

    def test_detects_cercle_typo(self):
        """Signal 4 should flag Cercle des Sages / Cercle de ses sages."""
        profiles = [
            _make_profile(1, "Cercle des Sages", "institution"),
            _make_profile(2, "Cercle de ses sages", "institution"),
        ]
        candidates = find_alias_candidates(profiles)
        fuzzy = [c for c in candidates if c.source == "fuzzy_name"]
        assert len(fuzzy) >= 1

    def test_does_not_flag_unrelated(self):
        """Signal 4 should not flag clearly unrelated names."""
        profiles = [
            _make_profile(1, "Sans-ciels", "caste"),
            _make_profile(2, "Faucons Chasseurs", "caste"),
            _make_profile(3, "Fleuve Perle", "place"),
        ]
        candidates = find_alias_candidates(profiles)
        fuzzy = [c for c in candidates if c.source == "fuzzy_name"]
        assert len(fuzzy) == 0

    def test_no_duplicate_pairs(self):
        """Each pair should appear at most once across all signals."""
        profiles = [
            _make_profile(1, "Sans-ciels", "caste"),
            _make_profile(2, "Nés-sans-ciel", "caste"),
        ]
        candidates = find_alias_candidates(profiles)
        pairs = [_pair(c) for c in candidates]
        assert len(pairs) == len(set(pairs)), "Duplicate pairs found"

    def test_cross_type_flagged(self):
        """Signal 4 should flag cross-type variants (same name, different type).

        The cross-type guard was removed: same entity can be classified
        differently across turns. LLM confirmation handles false positives.
        """
        profiles = [
            _make_profile(1, "Ciels-libres", "civilization"),
            _make_profile(2, "Ciels-libres", "caste"),  # same name, different type
        ]
        candidates = find_alias_candidates(profiles)
        # Same normalized name → 100% overlap → should be flagged
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# find_alias_candidates — Signal 1 cross-type relaxed
# ---------------------------------------------------------------------------

class TestFindAliasCandidatesCrossType:
    def test_signal1_cross_type_no_longer_blocked(self):
        """Signal 1 should flag cross-type aliases (guard removed)."""
        profiles = [
            _make_profile(
                1, "Ciels-clairs", entity_type="civilization",
                aliases_suggested=["Ciels-libres"],
            ),
            _make_profile(2, "Ciels-libres", entity_type="caste"),
        ]
        candidates = find_alias_candidates(profiles)
        llm_suggested = [c for c in candidates if c.source == "llm_suggested"]
        assert len(llm_suggested) >= 1

    def test_signal1_same_type_still_works(self):
        """Signal 1 continues to work for same-type pairs."""
        profiles = [
            _make_profile(
                1, "Sans-ciels", entity_type="caste",
                aliases_suggested=["Nés-sans-ciel"],
            ),
            _make_profile(2, "Nés-sans-ciel", entity_type="caste"),
        ]
        candidates = find_alias_candidates(profiles)
        llm_suggested = [c for c in candidates if c.source == "llm_suggested"]
        assert len(llm_suggested) >= 1


# ---------------------------------------------------------------------------
# Score-based confirm versions
# ---------------------------------------------------------------------------

class TestScoreVersions:
    def test_v4_score10_registered(self):
        """v4-score-10 must be in the registry with score_scale=10."""
        v = get_confirm_version("v4-score-10")
        assert v.score_scale == 10
        assert v.json_mode is False

    def test_v5_score_pct_registered(self):
        """v5-score-pct must be in the registry with score_scale=100."""
        v = get_confirm_version("v5-score-pct")
        assert v.score_scale == 100
        assert v.json_mode is False

    def test_all_versions_listed(self):
        versions = list_confirm_versions()
        assert "v4-score-10" in versions
        assert "v5-score-pct" in versions

    def test_prompt_has_required_placeholders(self):
        """Score prompts must contain all format placeholders."""
        required = ["{name_a}", "{type_a}", "{desc_a}", "{name_b}", "{type_b}", "{desc_b}", "{reason}"]
        for vname in ("v4-score-10", "v5-score-pct"):
            v = get_confirm_version(vname)
            for ph in required:
                assert ph in v.prompt, f"{vname} prompt missing {ph}"

    def test_binary_versions_have_no_scale(self):
        """Binary versions must have score_scale=None."""
        for vname in ("v1-llama", "v2-qwen3", "v3-nemo"):
            v = get_confirm_version(vname)
            assert v.score_scale is None


class TestDecideByScore:
    def test_score_10_above_threshold(self):
        """Score 8/10 with threshold 0.7 → confirmed, norm=0.8."""
        confirmed, norm = _decide_by_score({"score": 8}, 10, 0.7, "A", "B")
        assert confirmed is True
        assert norm == pytest.approx(0.8)

    def test_score_10_below_threshold(self):
        """Score 6/10 with threshold 0.7 → rejected, norm=0.6."""
        confirmed, norm = _decide_by_score({"score": 6}, 10, 0.7, "A", "B")
        assert confirmed is False
        assert norm == pytest.approx(0.6)

    def test_score_10_at_threshold(self):
        """Score exactly at threshold → confirmed."""
        confirmed, norm = _decide_by_score({"score": 7}, 10, 0.7, "A", "B")
        assert confirmed is True
        assert norm == pytest.approx(0.7)

    def test_score_pct_above_threshold(self):
        """Score 80% with threshold 0.7 → confirmed, norm=0.8."""
        confirmed, norm = _decide_by_score({"score": 80}, 100, 0.7, "A", "B")
        assert confirmed is True
        assert norm == pytest.approx(0.8)

    def test_score_pct_below_threshold(self):
        """Score 50% with threshold 0.7 → rejected."""
        confirmed, norm = _decide_by_score({"score": 50}, 100, 0.7, "A", "B")
        assert confirmed is False
        assert norm == pytest.approx(0.5)

    def test_missing_score_returns_false(self):
        """No 'score' field → (False, None)."""
        confirmed, norm = _decide_by_score({}, 10, 0.7, "A", "B")
        assert confirmed is False
        assert norm is None

    def test_invalid_score_returns_false(self):
        """Non-numeric score → (False, None)."""
        confirmed, norm = _decide_by_score({"score": "high"}, 10, 0.7, "A", "B")
        assert confirmed is False
        assert norm is None

    def test_score_clamped_above(self):
        """Score above scale (e.g. 12/10) → clamped to 1.0, still confirmed."""
        confirmed, norm = _decide_by_score({"score": 12}, 10, 0.7, "A", "B")
        assert confirmed is True
        assert norm == pytest.approx(1.0)

    def test_score_clamped_below(self):
        """Negative score → clamped to 0.0, rejected."""
        confirmed, norm = _decide_by_score({"score": -5}, 10, 0.7, "A", "B")
        assert confirmed is False
        assert norm == pytest.approx(0.0)

    def test_float_score(self):
        """LLM may return float (7.5/10) — should work."""
        confirmed, norm = _decide_by_score({"score": 7.5}, 10, 0.7, "A", "B")
        assert confirmed is True
        assert norm == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _pair(c: AliasCandidate) -> tuple[int, int]:
    a, b = c.entity_a.entity_id, c.entity_b.entity_id
    return (min(a, b), max(a, b))
