"""Tests for NER entity extraction with game-specific patterns."""

import pytest

from pipeline.ner import EntityExtractor, ALIAS_MAP


@pytest.fixture(scope="module")
def extractor():
    """Shared extractor instance — spaCy model loading is expensive."""
    try:
        return EntityExtractor()
    except OSError:
        pytest.skip("spaCy model fr_core_news_lg not available")


class TestEntityRulerPatterns:
    """Test that custom EntityRuler patterns detect game entities."""

    def test_detects_caste_faucons_chasseurs(self, extractor):
        entities = extractor.extract("Les Faucons Chasseurs partent en mission.")
        names = [e.text for e in entities]
        assert "Faucons Chasseurs" in names

    def test_detects_caste_enfants_des_echos(self, extractor):
        entities = extractor.extract("Les Enfants des Échos creusent de nouvelles galeries.")
        names = [e.text for e in entities]
        assert "Enfants des Échos" in names

    def test_detects_place_gouffre_humide(self, extractor):
        entities = extractor.extract("Le voyage vers Gouffre Humide est long.")
        names = [e.text for e in entities]
        assert "Gouffre Humide" in names

    def test_detects_place_la_confluence(self, extractor):
        entities = extractor.extract("Ils retournent à la Confluence.")
        names = [e.text for e in entities]
        assert "La Confluence" in names

    def test_detects_civilization_nanzagouets(self, extractor):
        entities = extractor.extract("Les Nanzagouets sont un peuple de la mer.")
        names = [e.text for e in entities]
        assert "Nanzagouets" in names

    def test_detects_tech_argile_vivante(self, extractor):
        entities = extractor.extract("L'Argile Vivante durcit au contact de l'air.")
        names = [e.text for e in entities]
        assert "Argile Vivante" in names

    def test_detects_institution_cercle_des_sages(self, extractor):
        entities = extractor.extract("Le Cercle des Sages se réunit.")
        names = [e.text for e in entities]
        assert "Cercle des Sages" in names

    def test_detects_institution_tribunal_des_moeurs(self, extractor):
        entities = extractor.extract("Le Tribunal des Mœurs doit statuer.")
        names = [e.text for e in entities]
        assert "Tribunal des Mœurs" in names

    def test_detects_institution_assemblee_des_chefs(self, extractor):
        entities = extractor.extract("L'Assemblée des Chefs est informée.")
        names = [e.text for e in entities]
        assert "Assemblée des Chefs" in names

    def test_detects_caste_sans_ciel(self, extractor):
        entities = extractor.extract("Un Sans-ciel arrivé comme envoyé de la confluence.")
        names = [e.text for e in entities]
        assert "Sans-ciels" in names  # canonicalized

    def test_detects_tech_rhombes(self, extractor):
        entities = extractor.extract("Ils communiquent avec des rhombes.")
        names = [e.text for e in entities]
        assert "Rhombes" in names

    def test_detects_civ_cheveux_de_sang(self, extractor):
        entities = extractor.extract("L'observation des cheveux de sang se fait plus régulière.")
        names = [e.text for e in entities]
        assert "Cheveux de Sang" in names


class TestDeduplication:
    """Test that duplicate entities within a text are merged."""

    def test_same_entity_mentioned_twice(self, extractor):
        text = "Les Nanzagouets arrivent. Les Nanzagouets sont nombreux."
        entities = extractor.extract(text)
        nanz = [e for e in entities if e.text == "Nanzagouets"]
        assert len(nanz) == 1


class TestCanonicalization:
    """Test alias resolution."""

    def test_alias_map_completeness(self):
        # Ensure key aliases exist
        assert ALIAS_MAP["faucons"] == "Faucons Chasseurs"
        assert ALIAS_MAP["gouffre humide"] == "Gouffre Humide"
        assert ALIAS_MAP["nanzagouet"] == "Nanzagouets"
        assert ALIAS_MAP["la confluence"] == "La Confluence"

    def test_canonicalize_method(self, extractor):
        assert extractor._canonicalize("faucons") == "Faucons Chasseurs"
        assert extractor._canonicalize("Gouffre Humide") == "Gouffre Humide"
        assert extractor._canonicalize("Unknown Entity") == "Unknown Entity"


class TestEntityLabels:
    """Test that entities get correct labels."""

    def test_caste_label(self, extractor):
        entities = extractor.extract("Les Faucons Chasseurs partent.")
        faucons = [e for e in entities if e.text == "Faucons Chasseurs"]
        assert faucons and faucons[0].label == "caste"

    def test_place_label(self, extractor):
        entities = extractor.extract("Ils arrivent à Gouffre Humide.")
        gh = [e for e in entities if e.text == "Gouffre Humide"]
        assert gh and gh[0].label == "place"

    def test_civilization_label(self, extractor):
        entities = extractor.extract("Les Nanzagouets sont arrivés.")
        nanz = [e for e in entities if e.text == "Nanzagouets"]
        assert nanz and nanz[0].label == "civilization"

    def test_tech_label(self, extractor):
        entities = extractor.extract("L'Argile Vivante est une merveille.")
        av = [e for e in entities if e.text == "Argile Vivante"]
        assert av and av[0].label == "technology"
