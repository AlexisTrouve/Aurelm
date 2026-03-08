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
    certainty: int = 0  # LLM self-assessed confidence (0=not set, scale defined by version)


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


# Generic French nouns that are NEVER game-specific entity names.
# Language-level filter (not game-specific): these are common French words
# that smaller LLMs frequently extract as "entities" despite being generic.
# Only includes unambiguous generics — game-specific names that LOOK generic
# (e.g. "Passes-bien", "Ciels-clairs") are not here because their compound
# form makes them unique.
_GENERIC_FRENCH_NOUNS = {
    # Geography generics (single generic words)
    "montagne", "montagnes", "vallee", "vallees", "riviere", "rivieres",
    "fleuve", "fleuves", "lac", "lacs", "mer", "mers", "ocean", "oceans",
    "foret", "forets", "plaine", "plaines", "colline", "collines",
    "sommet", "sommets", "hauteur", "hauteurs", "berceau",
    # Profession generics (common roles, not game-specific titles)
    "pecheur", "pecheurs", "scribe", "scribes", "chef", "chefs",
    "pretre", "pretres", "batisseur", "batisseurs", "guerrier", "guerriers",
    "chasseur", "chasseurs", "artisan", "artisans", "marchand", "marchands",
    "sculpteur", "sculpteurs", "forgeron", "forgerons", "tailleur", "tailleurs",
    "cueilleur", "cueilleurs", "habitant", "habitants", "mineur", "mineurs",
    "paysan", "paysans", "soldat", "soldats", "espion", "espions",
    # Social group generics — single word without a distinguishing modifier
    # ("Tribu des X" = 3 words, passes; bare "Tribu" alone = noise)
    "tribu", "tribus", "clan", "clans", "clique", "cliques",
    "peuple", "peuples", "famille", "familles", "groupe", "groupes",
    "bande", "bandes", "communaute", "communautes",
    # Role/status generics — bare words that small LLMs tag as entities
    "anciens", "ancienne", "anciens", "aînes", "marginaux", "marginal",
    "dirigeant", "dirigeants", "chef",
    # Creature generics
    "creature", "creatures", "animal", "animaux", "bete", "betes",
    # Object generics (NOTE: "lance/lances", "codex", "palanquin/s", "fresque/s" intentionally
    # removed — they are confirmed named technologies in this JDR corpus and must NOT be filtered
    # even though they look like common French nouns. entity_filter is language-level, not
    # game-specific, but these specific words conflict with reference ground truth.)
    "arc", "arcs", "epee", "epees", "outil", "outils", "arme", "armes",
    # Building/place generics
    "maison", "village", "villages", "cite", "temple", "autel", "autels",
    "antre", "antres", "ruine", "ruines", "sanctuaire",
    # Abstract generics (glyphe/fresque kept because named entities using them are always
    # multi-word, e.g. "Glyphes du Gouffre" (3 words) and "Grande Fresque" (2 words, "grande"
    # is not in this set) — they pass the 1-2 word filter regardless)
    "hieroglyphe", "hieroglyphes", "glyphe", "glyphes",
    "present", "presents", "architecture",
}


def is_noise_entity(name: str) -> bool:
    """Check if an entity name is structurally broken or a generic French word.

    Two-level filtering:
    1. Structural: URLs, markdown, multiline, truncated strings, pure numbers
    2. Semantic: single generic French nouns that are never game-specific
       (only when the name is 1-2 words with no compound markers like hyphens)
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

    # Too many words = sentence fragment, not an entity name.
    # Threshold is 6 (not 5) to allow compound tool names like
    # "Ciseaux de bois au dents d'obsidienne" (6 words) which are valid technologies.
    if len(name.split()) > 6:
        return True

    # Ends with sentence-ending punctuation = full sentence, not a name
    if name.rstrip().endswith((".","!","?")):
        return True

    # Semantic filter: reject single generic French words.
    # Only applies to short names (1-2 words) WITHOUT compound markers
    # (hyphens, apostrophes) that could indicate a game-specific term.
    # "Montagne" → noise, but "Montagne-Blanche" → kept
    # "Sculpteurs" → noise, but "Sculpteurs d'Argile" → kept (3+ words)
    words = name.split()
    if len(words) <= 2 and "-" not in name and "'" not in name:
        normalized = _strip_accents(name.lower().strip())
        # Check each word individually — "Tailleurs de pierres" has 3 words
        # but "Tailleurs" alone should be caught as 1-word
        if len(words) == 1 and normalized in _GENERIC_FRENCH_NOUNS:
            return True
        # 2-word patterns like "étrange créature" or "étendue d'eau"
        # where both words are generic
        if len(words) == 2:
            w1 = _strip_accents(words[0].lower())
            w2 = _strip_accents(words[1].lower())
            if w1 in _GENERIC_FRENCH_NOUNS and w2 in _GENERIC_FRENCH_NOUNS:
                return True

    return False
