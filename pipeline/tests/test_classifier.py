"""Tests for message type classification."""

from pipeline.classifier import SegmentType, classify_segments, _split_paragraphs


# === Original tests ===

def test_choice_detection():
    text = "Que fais-tu face à cette menace ?\n1. Attaquer\n2. Fuir\n3. Négocier"
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.CHOICE


def test_ooc_detection():
    text = "(Note du MJ : on reprend la semaine prochaine)"
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.OOC


def test_narrative_default():
    text = "Le soleil se lève sur la vallée. Les premiers rayons illuminent la confluence des deux rivières."
    segments = classify_segments(text)
    assert len(segments) == 1
    assert segments[0].segment_type == SegmentType.NARRATIVE


# === New tests for enhanced patterns ===

class TestChoicePatterns:
    """Test detection of various choice formats found in real data."""

    def test_bold_choix_header(self):
        text = "**Choix**\n- comment chasser le gibier\n- comment pêcher le poisson"
        segments = classify_segments(text)
        # The bold header starts a new paragraph, then the bullet list follows
        choice_segs = [s for s in segments if s.segment_type == SegmentType.CHOICE]
        assert len(choice_segs) >= 1

    def test_numbered_choix_header(self):
        text = "**Choix 1 - Évaluation de l'initiative du Sans-ciel:**\n- de l'audace\n- c'est bien la preuve"
        segments = classify_segments(text)
        choice_segs = [s for s in segments if s.segment_type == SegmentType.CHOICE]
        assert len(choice_segs) >= 1

    def test_bullet_list_choices(self):
        text = "- Il y a un autre monde qui vous attend après la mort.\n- Il renaît dans un corps nouveau.\n- Son esprit se mêle à l'univers.\n- Rien. Il cesse d'être."
        segments = classify_segments(text)
        assert segments[0].segment_type == SegmentType.CHOICE

    def test_libre_marker(self):
        text = "**Libre**\nDe quoi s'agit-il ?"
        segments = classify_segments(text)
        # **Libre** should trigger choice
        choice_segs = [s for s in segments if s.segment_type == SegmentType.CHOICE]
        assert len(choice_segs) >= 1

    def test_autres_libre_marker(self):
        text = "Quelque chose\nautres [ libre ]"
        segments = classify_segments(text)
        choice_segs = [s for s in segments if s.segment_type == SegmentType.CHOICE]
        assert len(choice_segs) >= 1


class TestConsequencePatterns:
    """Test detection of consequence/response patterns."""

    def test_underline_choix_marker(self):
        text = "__Choix : Un étranger semble vouloir s'enfuir__\n\nUn instant. C'est tout ce qu'il a fallu."
        segments = classify_segments(text)
        consequence_segs = [s for s in segments if s.segment_type == SegmentType.CONSEQUENCE]
        assert len(consequence_segs) >= 1


class TestOOCPatterns:
    """Test OOC detection patterns."""

    def test_square_bracket_ooc(self):
        text = "[Je sais pas si c'est ce que tu veux]"
        segments = classify_segments(text)
        assert segments[0].segment_type == SegmentType.OOC

    def test_parenthesis_ooc(self):
        text = "(modifié)"
        segments = classify_segments(text)
        assert segments[0].segment_type == SegmentType.OOC


class TestParagraphSplitting:
    """Test that paragraph splitting respects markdown structures."""

    def test_split_on_horizontal_rule(self):
        text = "First paragraph.\n\n---\n\nSecond paragraph."
        paras = _split_paragraphs(text)
        assert len(paras) == 2

    def test_split_on_markdown_header(self):
        text = "Some text.\n\n## New Section\n\nMore text."
        paras = _split_paragraphs(text)
        assert len(paras) == 3

    def test_split_on_bold_header(self):
        text = "Narrative text here.\n\n**Choix**\n- option 1\n- option 2"
        paras = _split_paragraphs(text)
        assert len(paras) == 2

    def test_empty_text(self):
        assert _split_paragraphs("") == []

    def test_single_paragraph(self):
        paras = _split_paragraphs("Just one paragraph.")
        assert len(paras) == 1
