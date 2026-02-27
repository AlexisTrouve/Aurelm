"""Entity noise filtering — rejects structurally broken extractions.

Catches only STRUCTURAL noise: URLs, markdown artifacts, multiline strings,
truncated extractions, pure numbers. NO word lists — the LLM prompt handles
content-level filtering.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class ExtractedEntity:
    """An entity extracted from turn text."""
    text: str
    label: str  # person, place, technology, institution, resource, creature, event, civilization, caste, belief
    context: str


# Valid entity types for validation
VALID_ENTITY_TYPES = {
    "person", "place", "technology", "institution", "resource",
    "creature", "event", "civilization", "caste", "belief",
}


# Regex for structural noise patterns
_NOISE_PATTERN = re.compile(
    r"^("
    r"https?://|www\.|youtube|spotify"
    r"|.{1,2}$"           # 1-2 char strings
    r"|.*\n.*"            # multiline
    r"|.*[{}\[\]<>].*"   # markdown/code artifacts
    r"|__(.*?)__"         # underline markers
    r"|\*\*(.*?)\*\*$"   # bold-only strings
    r"|\d+$"             # pure numbers
    r")",
    re.IGNORECASE,
)

# Truncated entities ending with a preposition
_RE_TRAILING_PREP = re.compile(r"\b(de|du|des|de la|de l')\s*$", re.IGNORECASE)

# Starts with common article then nothing useful
_RE_ARTICLE_ONLY = re.compile(r"^(Le|La|Les|Un|Une|Des|Du|De)\s*$", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    """Remove diacritics and ligatures for accent-insensitive matching."""
    # Expand ligatures (not decomposed by NFKD)
    text = text.replace("\u0153", "oe").replace("\u0152", "OE")  # œ/Œ
    text = text.replace("\u00e6", "ae").replace("\u00c6", "AE")  # æ/Æ
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def is_noise_entity(name: str) -> bool:
    """Check if an entity name is structurally broken.

    Only rejects structural problems: URLs, markdown, multiline,
    truncated strings, pure numbers. Content-level filtering is
    the LLM prompt's job.
    """
    # Structural patterns (URLs, markdown, too short, numbers)
    if _NOISE_PATTERN.match(name):
        return True

    # Markdown bold artifacts
    if "**" in name:
        return True

    # Multiline = broken extraction
    if "\n" in name:
        return True

    # Too long = almost certainly noise
    if len(name) > 50:
        return True

    # Double underscore artifacts
    if "__" in name:
        return True

    # Parenthesis artifacts (e.g. "Capture)")
    if name.endswith(")") or name.startswith("("):
        return True

    # No alphabetic characters
    if not any(c.isalpha() for c in name):
        return True

    # Article-only strings ("Le", "La", "Des")
    if _RE_ARTICLE_ONLY.match(name):
        return True

    # Truncated entities ending with preposition ("Cercle des", "Maison de")
    if _RE_TRAILING_PREP.search(name):
        return True

    # Contains colon = likely a label or truncated heading
    if ":" in name:
        return True

    # Too many words = sentence fragment, not an entity name
    if len(name.split()) > 5:
        return True

    # Ends with sentence-ending punctuation = full sentence, not a name
    if name.rstrip().endswith((".","!","?")):
        return True

    return False
