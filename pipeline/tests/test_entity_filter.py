"""Tests for entity noise filtering (structural only)."""

from pipeline.entity_filter import is_noise_entity, ExtractedEntity, VALID_ENTITY_TYPES


class TestIsNoiseEntity:
    """Test structural noise detection for entity names."""

    def test_rejects_urls(self):
        assert is_noise_entity("https://example.com")

    def test_rejects_short_strings(self):
        assert is_noise_entity("ab")
        assert is_noise_entity("x")

    def test_rejects_markdown_artifacts(self):
        assert is_noise_entity("**bold text**")
        assert is_noise_entity("__underlined__")

    def test_rejects_pure_numbers(self):
        assert is_noise_entity("42")
        assert is_noise_entity("1234")

    def test_rejects_article_only(self):
        assert is_noise_entity("Le")
        assert is_noise_entity("Les")
        assert is_noise_entity("Du")

    def test_rejects_trailing_preposition(self):
        assert is_noise_entity("Chef du")
        assert is_noise_entity("Gardiens de")

    def test_rejects_colon(self):
        assert is_noise_entity("Choix: libre")

    def test_rejects_long_strings(self):
        assert is_noise_entity("a" * 51)

    def test_rejects_sentence_fragments(self):
        assert is_noise_entity("Mon combat fut long et difficile vraiment")
        assert is_noise_entity("Mon combat fut long, mais vain.")
        assert is_noise_entity("Je me suis rendu a l evidence.")
        assert is_noise_entity("Qu il s epanouisse par lui-meme.")

    def test_rejects_multiline(self):
        assert is_noise_entity("First\nSecond")

    def test_rejects_parenthesis_artifacts(self):
        assert is_noise_entity("(something")
        assert is_noise_entity("something)")

    def test_rejects_no_alpha(self):
        assert is_noise_entity("123!@#")

    def test_accepts_real_game_entities(self):
        assert not is_noise_entity("Faucons Chasseurs")
        assert not is_noise_entity("Argile Vivante")
        assert not is_noise_entity("Nanzagouets")
        assert not is_noise_entity("Gouffre Humide")
        assert not is_noise_entity("Cercle des Sages")
        assert not is_noise_entity("Cheveux de Sang")

    def test_accepts_single_words(self):
        # No word filtering -- prompt handles this
        assert not is_noise_entity("village")
        assert not is_noise_entity("farouche")
        assert not is_noise_entity("Rhombes")


class TestExtractedEntity:
    """Test ExtractedEntity dataclass."""

    def test_creation(self):
        ent = ExtractedEntity(text="Nanzagouets", label="civilization", context="Les Nanzagouets arrivent")
        assert ent.text == "Nanzagouets"
        assert ent.label == "civilization"
        assert ent.context == "Les Nanzagouets arrivent"


class TestValidEntityTypes:
    """Test valid entity type constants."""

    def test_all_types_present(self):
        expected = {"person", "place", "technology", "institution", "resource",
                    "creature", "event", "civilization", "caste", "belief"}
        assert VALID_ENTITY_TYPES == expected
