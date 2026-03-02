"""Tests for benchmark scoring logic."""

import pytest
from dataclasses import dataclass

from benchmark import normalize, filter_reference_by_text, score_extraction, parse_turn_arg


# --- normalize ---

class TestNormalize:
    def test_lowercase(self):
        assert normalize("Cercle des Sages") == "cercle des sages"

    def test_strip_accents(self):
        assert normalize("Epreuve du Feu") == "epreuve du feu"
        assert normalize("Caste de l'Ether") == "caste de l'ether"

    def test_strip_article_le(self):
        assert normalize("Le Gouffre") == "gouffre"

    def test_strip_article_la(self):
        assert normalize("La Confluence") == "confluence"

    def test_strip_article_les(self):
        assert normalize("Les Anciens") == "anciens"

    def test_strip_article_l_apostrophe(self):
        assert normalize("L'Oracle") == "oracle"
        # curly apostrophe
        assert normalize("L\u2019Oracle") == "oracle"

    def test_no_article(self):
        assert normalize("Gouffre Humide") == "gouffre humide"

    def test_empty(self):
        assert normalize("") == ""

    def test_whitespace(self):
        assert normalize("  Foo  ") == "foo"


# --- filter_reference_by_text ---

SAMPLE_REFERENCE = [
    {"name": "Cercle des Sages", "type": "institution", "aliases": ["Conseil des Sages"]},
    {"name": "Gouffre Humide", "type": "place", "aliases": []},
    {"name": "Rhombes", "type": "technology", "aliases": ["rhombe"]},
]


class TestFilterReference:
    def test_name_match(self):
        text = "Le Cercle des Sages se reunit."
        result = filter_reference_by_text(SAMPLE_REFERENCE, text)
        assert len(result) == 1
        assert result[0]["name"] == "Cercle des Sages"

    def test_alias_match(self):
        text = "Le Conseil des Sages decide."
        result = filter_reference_by_text(SAMPLE_REFERENCE, text)
        assert len(result) == 1
        assert result[0]["name"] == "Cercle des Sages"

    def test_case_insensitive(self):
        text = "les rhombes resonnent"
        result = filter_reference_by_text(SAMPLE_REFERENCE, text)
        assert len(result) == 1
        assert result[0]["name"] == "Rhombes"

    def test_no_match(self):
        text = "Rien de special."
        result = filter_reference_by_text(SAMPLE_REFERENCE, text)
        assert len(result) == 0

    def test_multiple_matches(self):
        text = "Le Cercle des Sages visite le Gouffre Humide."
        result = filter_reference_by_text(SAMPLE_REFERENCE, text)
        assert len(result) == 2


# --- score_extraction ---

@dataclass
class FakeEntity:
    text: str
    label: str


class TestScoreExtraction:
    def test_perfect_match(self):
        extracted = [FakeEntity("Cercle des Sages", "institution")]
        reference = [{"name": "Cercle des Sages", "type": "institution", "aliases": []}]
        scores = score_extraction(extracted, reference)
        assert scores["precision"] == 1.0
        assert scores["recall"] == 1.0
        assert scores["f1"] == 1.0
        assert scores["n_tp"] == 1
        assert scores["n_fp"] == 0
        assert scores["n_fn"] == 0

    def test_false_positive(self):
        extracted = [
            FakeEntity("Cercle des Sages", "institution"),
            FakeEntity("chasseurs", "person"),
        ]
        reference = [{"name": "Cercle des Sages", "type": "institution", "aliases": []}]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 1
        assert scores["n_fp"] == 1
        assert scores["n_fn"] == 0
        assert scores["precision"] == pytest.approx(0.5)
        assert scores["recall"] == 1.0

    def test_false_negative(self):
        extracted = []
        reference = [{"name": "Cercle des Sages", "type": "institution", "aliases": []}]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 0
        assert scores["n_fp"] == 0
        assert scores["n_fn"] == 1
        assert scores["precision"] == 0.0
        assert scores["recall"] == 0.0
        assert scores["f1"] == 0.0

    def test_alias_matching(self):
        extracted = [FakeEntity("Conseil des Sages", "institution")]
        reference = [
            {"name": "Cercle des Sages", "type": "institution", "aliases": ["Conseil des Sages"]}
        ]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 1
        assert scores["n_fn"] == 0

    def test_accent_normalization(self):
        extracted = [FakeEntity("Epreuve du Feu", "event")]
        reference = [{"name": "Epreuve du Feu", "type": "event", "aliases": []}]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 1

    def test_article_normalization(self):
        extracted = [FakeEntity("Le Gouffre", "place")]
        reference = [{"name": "Gouffre", "type": "place", "aliases": ["Le Gouffre"]}]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 1

    def test_no_double_count(self):
        """Same reference entity matched by two extracted entities -> only 1 TP."""
        extracted = [
            FakeEntity("Cercle des Sages", "institution"),
            FakeEntity("Conseil des Sages", "institution"),
        ]
        reference = [
            {"name": "Cercle des Sages", "type": "institution", "aliases": ["Conseil des Sages"]}
        ]
        scores = score_extraction(extracted, reference)
        assert scores["n_tp"] == 1
        assert scores["n_fp"] == 1  # second match becomes FP since ref already matched

    def test_empty_both(self):
        scores = score_extraction([], [])
        assert scores["precision"] == 0.0
        assert scores["recall"] == 0.0
        assert scores["f1"] == 0.0


# --- parse_turn_arg ---

class TestParseTurnArg:
    def test_last(self):
        assert parse_turn_arg("last", 14) == [13]

    def test_single(self):
        assert parse_turn_arg("5", 14) == [4]

    def test_multiple(self):
        assert parse_turn_arg("1,5,14", 14) == [0, 4, 13]

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_turn_arg("15", 14)

    def test_zero(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_turn_arg("0", 14)
