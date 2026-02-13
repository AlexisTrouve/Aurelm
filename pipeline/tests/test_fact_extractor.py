"""Tests for the structured fact extractor."""

import json
import pytest
from pipeline.fact_extractor import FactExtractor, StructuredFacts


class TestMediaLinkExtraction:
    """Test extraction of media links from raw content."""

    def test_youtube_link_extraction(self):
        """Should extract YouTube video URLs."""
        extractor = FactExtractor()
        raw_content = """
        Arthur Ignatus
        03/09/2024 04:09
        https://www.youtube.com/watch?v=jURi-bCBhKQ
        YouTube
        Geiita
        9 The End of the Battle Shadow of the Colossus Remake OST
        """

        facts = extractor.extract_facts([], raw_content)

        assert len(facts.media_links) == 1
        assert facts.media_links[0]["type"] == "youtube"
        assert "jURi-bCBhKQ" in facts.media_links[0]["url"]
        assert facts.media_links[0]["video_id"] == "jURi-bCBhKQ"

    def test_youtube_short_link(self):
        """Should extract youtu.be short URLs."""
        extractor = FactExtractor()
        raw_content = "Check this: https://youtu.be/dQw4w9WgXcQ"

        facts = extractor.extract_facts([], raw_content)

        assert len(facts.media_links) == 1
        assert facts.media_links[0]["video_id"] == "dQw4w9WgXcQ"

    def test_discord_image_attachment(self):
        """Should extract Discord CDN image links."""
        extractor = FactExtractor()
        raw_content = "https://cdn.discordapp.com/attachments/123456/789012/image.png"

        facts = extractor.extract_facts([], raw_content)

        assert len(facts.media_links) == 1
        assert facts.media_links[0]["type"] == "image"

    def test_multiple_media_links(self):
        """Should extract multiple media links."""
        extractor = FactExtractor()
        raw_content = """
        https://www.youtube.com/watch?v=abc123
        Some text here
        https://cdn.discordapp.com/attachments/111/222/pic.jpg
        https://youtu.be/xyz789
        """

        facts = extractor.extract_facts([], raw_content)

        assert len(facts.media_links) == 3
        types = [link["type"] for link in facts.media_links]
        assert types.count("youtube") == 2
        assert types.count("image") == 1


class TestChoicesProposedExtraction:
    """Test extraction of choices proposed by GM."""

    def test_markdown_list_choices(self):
        """Should extract choices from markdown list."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "choice",
                "content": """Choix:
- comment chasser le gibier
- comment pêcher le poisson de rivière
- comment trouver des baies et des graines
- autres [libre]"""
            }
        ]

        facts = extractor.extract_facts(segments)

        assert len(facts.choices_proposed) == 4
        assert "comment chasser le gibier" in facts.choices_proposed
        assert "comment pêcher le poisson de rivière" in facts.choices_proposed

    def test_numbered_list_choices(self):
        """Should extract choices from numbered list."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "choice",
                "content": """1. Tu deviens leur chef
2. Tu deviens leur shaman
3. Tu refuse d'abuser de ton autorité
4. Autres [libre]"""
            }
        ]

        facts = extractor.extract_facts(segments)

        assert len(facts.choices_proposed) == 4
        assert "Tu deviens leur chef" in facts.choices_proposed

    def test_deduplication(self):
        """Should deduplicate identical choices."""
        extractor = FactExtractor()
        segments = [
            {"segment_type": "choice", "content": "- option A\n- option B"},
            {"segment_type": "choice", "content": "- option A\n- option C"}
        ]

        facts = extractor.extract_facts(segments)

        assert len(facts.choices_proposed) == 3
        assert facts.choices_proposed.count("option A") == 1


class TestLLMFactExtraction:
    """Test LLM-based fact extraction (integration test with Ollama)."""

    @pytest.mark.integration
    def test_extract_technologies(self):
        """Should extract technologies from narrative text."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "narrative",
                "content": """Opportunistes, ils chassent de petits animaux à l'aide de gourdins,
                attrapent quelques poissons en se servant de pieu et récoltent graines et baie
                dans les bois environnants."""
            }
        ]

        facts = extractor.extract_facts(segments)

        # Should extract tools/techniques
        assert len(facts.technologies) > 0
        tech_lower = [t.lower() for t in facts.technologies]
        assert any("gourdin" in t for t in tech_lower)

    @pytest.mark.integration
    def test_extract_resources(self):
        """Should extract resources from narrative text."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "narrative",
                "content": """Quelques mollusques par ci. Une poignée de baie par là.
                Un poisson coincé dans un remou. Les bêtes sont saignées et leur viande,
                fumé au-dessus d'un feu pour en faire des réserves."""
            }
        ]

        facts = extractor.extract_facts(segments)

        # Should extract food resources
        assert len(facts.resources) > 0
        resources_lower = [r.lower() for r in facts.resources]
        assert any("mollusque" in r for r in resources_lower)
        assert any("poisson" in r for r in resources_lower)

    @pytest.mark.integration
    def test_extract_geography(self):
        """Should extract geography from narrative text."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "narrative",
                "content": """La confluence de deux rivières cristallines, encaissé dans une large vallée.
                Les crêtes adjacentes. Le plus haut sommet visible depuis la fourche dans la rivière."""
            }
        ]

        facts = extractor.extract_facts(segments)

        # Should extract geographic features
        assert len(facts.geography) > 0
        geo_lower = [g.lower() for g in facts.geography]
        assert any("vallée" in g or "vallee" in g for g in geo_lower)
        assert any("rivière" in g or "riviere" in g for g in geo_lower)

    @pytest.mark.integration
    def test_extract_beliefs(self):
        """Should extract beliefs and rituals from narrative text."""
        extractor = FactExtractor()
        segments = [
            {
                "segment_type": "narrative",
                "content": """L'esprit s'élève et veille sur les vivants depuis le ciel,
                offrant une part de leur sagesse aux nouveau nés. Le corps retourne à la terre,
                se mêlant a la nature. Les oiseaux transportent les âmes vers le ciel."""
            }
        ]

        facts = extractor.extract_facts(segments)

        # Should extract beliefs
        assert len(facts.beliefs) > 0
        beliefs_lower = [b.lower() for b in facts.beliefs]
        assert any("esprit" in b or "âme" in b or "ame" in b for b in beliefs_lower)


class TestEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.integration
    def test_full_turn_extraction(self):
        """Should extract all categories from a complete turn."""
        extractor = FactExtractor()

        raw_content = """
        Arthur Ignatus
        03/09/2024 04:09
        https://www.youtube.com/watch?v=jURi-bCBhKQ

        Premier âge
        Blanc sur blanc. La neige devient rivières qui lacèrent la terre.
        """

        segments = [
            {
                "segment_type": "narrative",
                "content": """Ils chassent de petits animaux à l'aide de gourdins,
                attrapent quelques poissons en se servant de pieu."""
            },
            {
                "segment_type": "choice",
                "content": """Choix:
- comment chasser le gibier
- comment pêcher le poisson de rivière"""
            }
        ]

        facts = extractor.extract_facts(segments, raw_content)

        # Should have YouTube link
        assert len(facts.media_links) == 1
        assert facts.media_links[0]["type"] == "youtube"

        # Should have choices
        assert len(facts.choices_proposed) == 2

        # Should have some facts from LLM (if Ollama is running)
        # Note: These assertions are lenient as LLM output can vary
        assert isinstance(facts.technologies, list)
        assert isinstance(facts.resources, list)
        assert isinstance(facts.geography, list)
        assert isinstance(facts.beliefs, list)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_segments(self):
        """Should handle empty segments gracefully."""
        extractor = FactExtractor()
        facts = extractor.extract_facts([])

        assert facts.media_links == []
        assert facts.choices_proposed == []
        assert facts.technologies == []

    def test_invalid_llm_response(self):
        """Should handle LLM errors gracefully."""
        # Test with invalid Ollama URL
        extractor = FactExtractor(ollama_base_url="http://invalid:99999")

        segments = [{"segment_type": "narrative", "content": "Some text"}]
        facts = extractor.extract_facts(segments)

        # Should return empty lists instead of crashing
        assert facts.technologies == []
        assert facts.resources == []

    def test_malformed_choice_segment(self):
        """Should handle malformed choice segments."""
        extractor = FactExtractor()
        segments = [
            {"segment_type": "choice", "content": "No bullets here just text"}
        ]

        facts = extractor.extract_facts(segments)

        # Should not crash, may or may not extract choices
        assert isinstance(facts.choices_proposed, list)
