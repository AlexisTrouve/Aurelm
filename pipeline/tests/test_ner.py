"""Tests for NER entity extraction with game-specific patterns."""

import pytest

from pipeline.ner import EntityExtractor


@pytest.fixture(scope="module")
def extractor():
    """Shared extractor instance -- spaCy model loading is expensive."""
    try:
        return EntityExtractor()
    except OSError:
        pytest.skip("spaCy model fr_core_news_lg not available")


class TestEntityRulerPatterns:
    """Test that custom EntityRuler patterns detect game entities."""

    def test_detects_caste_faucons_chasseurs(self, extractor):
        entities = extractor.extract("Les Faucons Chasseurs partent en mission.")
        names = [e.text.lower() for e in entities]
        assert "faucons chasseurs" in names

    def test_detects_caste_enfants_des_echos(self, extractor):
        entities = extractor.extract("Les Enfants des Échos creusent de nouvelles galeries.")
        names = [e.text.lower() for e in entities]
        assert "enfants des échos" in names

    def test_detects_place_gouffre_humide(self, extractor):
        entities = extractor.extract("Le voyage vers Gouffre Humide est long.")
        names = [e.text.lower() for e in entities]
        assert "gouffre humide" in names

    def test_detects_place_la_confluence(self, extractor):
        entities = extractor.extract("Ils retournent à la Confluence.")
        names = [e.text.lower() for e in entities]
        assert "la confluence" in names

    def test_detects_civilization_nanzagouets(self, extractor):
        entities = extractor.extract("Les Nanzagouets sont un peuple de la mer.")
        names = [e.text.lower() for e in entities]
        assert "nanzagouets" in names

    def test_detects_tech_argile_vivante(self, extractor):
        entities = extractor.extract("L'Argile Vivante durcit au contact de l'air.")
        names = [e.text.lower() for e in entities]
        assert "argile vivante" in names

    def test_detects_institution_cercle_des_sages(self, extractor):
        entities = extractor.extract("Le Cercle des Sages se réunit.")
        names = [e.text.lower() for e in entities]
        assert "cercle des sages" in names

    def test_detects_institution_tribunal_des_moeurs(self, extractor):
        entities = extractor.extract("Le Tribunal des Mœurs doit statuer.")
        names = [e.text.lower() for e in entities]
        assert "tribunal des mœurs" in names

    def test_detects_institution_assemblee_des_chefs(self, extractor):
        entities = extractor.extract("L'Assemblée des Chefs est informée.")
        names = [e.text.lower() for e in entities]
        assert "assemblée des chefs" in names

    def test_detects_caste_sans_ciel(self, extractor):
        entities = extractor.extract("Un Sans-ciel arrivé comme envoyé de la confluence.")
        names = [e.text.lower() for e in entities]
        assert "sans-ciel" in names

    def test_detects_tech_rhombes(self, extractor):
        entities = extractor.extract("Ils communiquent avec des rhombes.")
        names = [e.text.lower() for e in entities]
        assert "rhombes" in names

    def test_detects_civ_cheveux_de_sang(self, extractor):
        entities = extractor.extract("L'observation des cheveux de sang se fait plus régulière.")
        names = [e.text.lower() for e in entities]
        assert "cheveux de sang" in names


class TestDeduplication:
    """Test that duplicate entities within a text are merged."""

    def test_same_entity_mentioned_twice(self, extractor):
        text = "Les Nanzagouets arrivent. Les Nanzagouets sont nombreux."
        entities = extractor.extract(text)
        nanz = [e for e in entities if e.text == "Nanzagouets"]
        assert len(nanz) == 1


class TestNormalization:
    """Test programmatic normalization (case + plural dedup)."""

    def test_normalize_strips_plural_s(self):
        from pipeline.runner import _normalize_for_dedup
        assert _normalize_for_dedup("Faucons Chasseurs") == "faucon chasseur"

    def test_normalize_singular_matches_plural(self):
        from pipeline.runner import _normalize_for_dedup
        assert _normalize_for_dedup("Faucon Chasseur") == _normalize_for_dedup("Faucons Chasseurs")

    def test_normalize_case_insensitive(self):
        from pipeline.runner import _normalize_for_dedup
        assert _normalize_for_dedup("faucons chasseurs") == _normalize_for_dedup("Faucons Chasseurs")

    def test_normalize_hyphenated(self):
        from pipeline.runner import _normalize_for_dedup
        assert _normalize_for_dedup("Ciels-clairs") == _normalize_for_dedup("Ciel-clair")

    def test_normalize_autel_pluriel(self):
        from pipeline.runner import _normalize_for_dedup
        assert _normalize_for_dedup("Autels des Pionniers") == _normalize_for_dedup("Autel des Pionniers")


class TestEntityLabels:
    """Test that entities get correct labels."""

    def test_caste_label(self, extractor):
        entities = extractor.extract("Les Faucons Chasseurs partent.")
        faucons = [e for e in entities if "faucons chasseurs" in e.text.lower()]
        assert faucons and faucons[0].label == "caste"

    def test_place_label(self, extractor):
        entities = extractor.extract("Ils arrivent à Gouffre Humide.")
        gh = [e for e in entities if "gouffre humide" in e.text.lower()]
        assert gh and gh[0].label == "place"

    def test_civilization_label(self, extractor):
        entities = extractor.extract("Les Nanzagouets sont arrivés.")
        nanz = [e for e in entities if e.text == "Nanzagouets"]
        assert nanz and nanz[0].label == "civilization"

    def test_tech_label(self, extractor):
        entities = extractor.extract("L'Argile Vivante est une merveille.")
        av = [e for e in entities if "argile vivante" in e.text.lower()]
        assert av and av[0].label == "technology"
