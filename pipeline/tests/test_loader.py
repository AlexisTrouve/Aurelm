"""Tests for the markdown file loader."""

from pipeline.loader import (
    detect_format,
    parse_format_a,
    parse_format_b,
    _parse_date,
    _clean_format_a_content,
)


# === Format detection ===

def test_detect_format_a():
    text = "Arthur Ignatus\n—\n03/09/2024 04:09\nSome content here"
    assert detect_format(text) == "A"


def test_detect_format_b():
    text = "# Title\n\n## Post narratif - Arthur Ignatus (03/09/2024 04:10)\n\nContent"
    assert detect_format(text) == "B"


def test_detect_format_b_message_du_mj():
    text = "# Title\n\n## Message du MJ (Arthur Ignatus)\n\nContent"
    assert detect_format(text) == "B"


# === Format A parsing ===

FORMAT_A_SAMPLE = """Arthur Ignatus
—
03/09/2024 04:10
Premier âge
Blanc sur blanc. Ton premier souvenir, est blanc.
Choix
comment chasser le gibier,
comment pêcher le poisson de rivière,

Arthur Ignatus
—
03/09/2024 04:19
[ je suis entrain de playtest avec toi ]

Rubanc
—
03/09/2024 18:48
Je leur montre comment suivre la rivière.
"""


def test_format_a_parses_multiple_messages():
    messages = parse_format_a(FORMAT_A_SAMPLE, "test.md")
    assert len(messages) == 3


def test_format_a_extracts_authors():
    messages = parse_format_a(FORMAT_A_SAMPLE, "test.md")
    authors = [m.author_name for m in messages]
    assert "Arthur Ignatus" in authors
    assert "Rubanc" in authors


def test_format_a_extracts_timestamps():
    messages = parse_format_a(FORMAT_A_SAMPLE, "test.md")
    assert messages[0].timestamp == "2024-09-03T04:10:00"


def test_format_a_extracts_content():
    messages = parse_format_a(FORMAT_A_SAMPLE, "test.md")
    assert "Blanc sur blanc" in messages[0].content


# === Format B parsing ===

FORMAT_B_SAMPLE = """# Premier âge

## Post narratif - Arthur Ignatus (03/09/2024 04:10)

Blanc sur blanc. Ton premier souvenir, est blanc.

**Choix**
- comment chasser le gibier
- comment pêcher le poisson de rivière

---

## Réponse - Rubanc (03/09/2024 18:48)

Je leur montre comment suivre la rivière.
"""


def test_format_b_parses_sections():
    messages = parse_format_b(FORMAT_B_SAMPLE, "2024-09-03-test.md")
    assert len(messages) == 2


def test_format_b_extracts_authors():
    messages = parse_format_b(FORMAT_B_SAMPLE, "2024-09-03-test.md")
    assert messages[0].author_name == "Arthur Ignatus"
    assert messages[1].author_name == "Rubanc"


def test_format_b_extracts_timestamps():
    messages = parse_format_b(FORMAT_B_SAMPLE, "2024-09-03-test.md")
    assert messages[0].timestamp == "2024-09-03T04:10:00"


def test_format_b_extracts_content():
    messages = parse_format_b(FORMAT_B_SAMPLE, "2024-09-03-test.md")
    assert "Blanc sur blanc" in messages[0].content


def test_format_b_skips_hrp_notes():
    text = """# Test

## Post narratif - Arthur Ignatus (03/09/2024 04:10)

Content here.

---

## Note HRP pour Arthur

This is out of character.
"""
    messages = parse_format_b(text, "test.md")
    assert len(messages) == 1
    assert "out of character" not in messages[0].content


# === Helper functions ===

def test_parse_date_dd_mm_yyyy():
    assert _parse_date("03/09/2024 04:10") == "2024-09-03T04:10:00"


def test_clean_format_a_removes_youtube():
    content = "https://www.youtube.com/watch?v=abc\nYouTube\nArtist\nSong Title\nLes confluents vivent dans la vallee."
    cleaned = _clean_format_a_content(content)
    assert "youtube" not in cleaned.lower()
    assert "Artist" not in cleaned
    assert "Song Title" not in cleaned
    assert "Les confluents" in cleaned


def test_clean_format_a_removes_modified():
    content = "Some text\n(modifié)"
    cleaned = _clean_format_a_content(content)
    assert "(modifié)" not in cleaned
    assert "Some text" in cleaned


def test_clean_format_a_removes_timestamps():
    content = "[04:10]\nSome content here"
    cleaned = _clean_format_a_content(content)
    assert "[04:10]" not in cleaned
    assert "Some content here" in cleaned
