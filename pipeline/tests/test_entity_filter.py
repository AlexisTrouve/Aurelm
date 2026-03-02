"""Tests for entity noise filtering (structural + semantic)."""

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

    def test_accepts_non_generic_single_words(self):
        # Non-generic single words pass through (could be game-specific)
        assert not is_noise_entity("farouche")
        assert not is_noise_entity("Rhombes")
        assert not is_noise_entity("Confluence")
        assert not is_noise_entity("Nantons")

    def test_rejects_generic_single_words(self):
        # Generic French nouns are noise when standing alone
        assert is_noise_entity("village")
        assert is_noise_entity("Montagne")
        assert is_noise_entity("Créature")
        assert is_noise_entity("Sculpteurs")

    def test_accepts_compound_names_with_generic_root(self):
        # Compound names built from generic roots are game-specific — keep them
        assert not is_noise_entity("Montagne-Blanche")    # hyphenated
        assert not is_noise_entity("Tailleurs de pierres")  # 3+ words
        assert not is_noise_entity("Cercle des Sages")
        assert not is_noise_entity("Ciels-clairs")         # hyphenated


class TestExtractedEntity:
    """Test ExtractedEntity dataclass."""

    def test_creation(self):
        ent = ExtractedEntity(text="Nanzagouets", label="civilization", context="Les Nanzagouets arrivent")
        assert ent.text == "Nanzagouets"
        assert ent.label == "civilization"
        assert ent.context == "Les Nanzagouets arrivent"

    def test_certainty_default(self):
        """Certainty defaults to 0 (not set) for backward compatibility."""
        ent = ExtractedEntity(text="Test", label="place", context="")
        assert ent.certainty == 0

    def test_certainty_explicit(self):
        """Certainty can be set explicitly."""
        ent = ExtractedEntity(text="Test", label="place", context="", certainty=3)
        assert ent.certainty == 3


class TestValidEntityTypes:
    """Test valid entity type constants."""

    def test_all_types_present(self):
        expected = {"person", "place", "technology", "institution", "resource",
                    "creature", "event", "civilization", "caste", "belief"}
        assert VALID_ENTITY_TYPES == expected
