"""Entity noise filtering — rejects false-positive entity names.

Catches: soundtrack metadata, choice labels, narrative fragments,
generic French words, markdown artifacts, truncated extractions.
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


# ============================================================
# NOISE FILTERING
# ============================================================

# Known noise entity names from spaCy general model
# Stored WITHOUT accents — comparison uses _strip_accents() for robustness
_NOISE_NAMES = {
    # Soundtrack / YouTube metadata (platform-level noise)
    "youtube",
    # Generic French words — too short or ambiguous to be proper names
    "blanc", "hier", "rare", "but", "si", "message",
    "autre", "autres", "mienne", "toutes",
    "hall", "halls", "cercle", "cercles", "antre", "antres",
    "biens", "formes", "couche",
    "methode", "organisation", "amelioration", "conseil", "acquisitions",
    "observer", "transporter", "posseder", "ramassez",
    "village", "vallee", "oracle", "tribunal",
    "premier", "premiers", "esprits", "lances", "sculptures",
    "feux", "foyer", "sel", "echanges",
    "l'autre", "le sel", "l'antre",
    # Generic French fragments (article + noun, truncated phrases)
    "chef du", "gardiens de",
    # Generic people/roles (not proper names in any game)
    "homme", "femme", "mari", "enfant", "enfants", "jeune", "jeunes",
    "ancien", "anciens", "individu", "individus", "defunt", "defunte",
    "chasseur", "chasseurs", "pecheur", "pecheurs", "artisan", "artisans",
    "guerrier", "guerriers", "guerriere", "guerrieres",
    "chef", "chefs", "ancetre", "ancetres", "aine", "aines",
    "mere", "pere", "frere", "soeur", "fils", "fille",
    "l'homme", "la femme", "le mari", "la tribu", "le clan",
    "les anciens", "les ancetres", "les jeunes", "les individus",
    "les chasseurs", "les pecheurs", "les artisans",
    "le defunt", "la defunte",
    # Generic nature/world words (exist in any French text)
    "ciel", "terre", "soleil", "lune", "etoile", "etoiles",
    "riviere", "montagne", "foret", "mer", "ocean", "lac",
    "oiseau", "oiseaux", "animal", "animaux", "poisson", "poissons",
    "arbre", "arbres", "plante", "plantes", "pierre", "pierres",
    "le ciel", "la terre", "le soleil", "la lune",
    "les oiseaux", "les animaux",
    # Generic social/abstract concepts
    "tribu", "clan", "peuple", "civilisation", "societe", "communaute",
    "rite", "rites", "tradition", "traditions", "coutume", "coutumes",
    "saison", "saisons", "guerre", "paix", "mort", "vie",
    "les saisons", "les rites",
}

# Substrings in entity names that signal noise
_NOISE_SUBSTRINGS = {
    "Choix", "Option", "option libre",
    "Pillar", "Soundtrack", "DETECTIVE", "Topic",
    "Tu es ", "Tu t'", "Et maintenant", "Puis tu",
    "Everybody wants", "The end of", "The Adventure",
    "L'air est froid", "Tu t'entoures", "Tu t'avance",
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

# Sentence-like fragments containing conjugated verbs
_RE_VERB_FRAGMENT = re.compile(r"\b(est|sont|fut|sera|etait|était)\b", re.IGNORECASE)

# Starts with determinants that signal NER noise (not proper names)
_RE_DET_START = re.compile(r"^(Que|Ces|Cet|Cette|Un |Une |Des )\s?")

# Starts with common article then nothing useful
_RE_ARTICLE_ONLY = re.compile(r"^(Le|La|Les|Un|Une|Des|Du|De)\s*$", re.IGNORECASE)

# "article + single word" = almost always generic (e.g. "le ciel", "la tribu")
# Real game entities are multi-word proper names (e.g. "Cercle des Sages")
_RE_ARTICLE_PLUS_ONE = re.compile(
    r"^(le|la|les|l'|un|une|des|du)\s+\w+$", re.IGNORECASE
)

# Game mechanic artifacts: "équipe(s) N", "groupe N"
_RE_GAME_MECHANIC = re.compile(
    r"^(l')?(equipe|groupe|option|choix)\s*\d*$", re.IGNORECASE
)


def _strip_accents(text: str) -> str:
    """Remove diacritics and ligatures for accent-insensitive matching."""
    # Expand ligatures (not decomposed by NFKD)
    text = text.replace("\u0153", "oe").replace("\u0152", "OE")  # œ/Œ
    text = text.replace("\u00e6", "ae").replace("\u00c6", "AE")  # æ/Æ
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def is_noise_entity(name: str) -> bool:
    """Check if an entity name is noise rather than a real game entity.

    Catches: soundtrack metadata, choice labels, narrative fragments,
    generic French words, markdown artifacts, truncated extractions.
    """
    # Accent-insensitive match on known noise names (all stored lowercase)
    if _strip_accents(name).lower() in _NOISE_NAMES:
        return True

    # Structural patterns
    if _NOISE_PATTERN.match(name):
        return True

    # Markdown bold artifacts
    if "**" in name:
        return True

    # Multiline = broken extraction
    if "\n" in name:
        return True

    # Noise substrings
    if any(noise in name for noise in _NOISE_SUBSTRINGS):
        return True

    # Too long = almost certainly noise (real entity names are short)
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

    # Article-only strings
    if _RE_ARTICLE_ONLY.match(name):
        return True

    # "article + single lowercase word" (e.g. "le ciel", "la tribu") -- too generic
    # But allow "la Confluence", "le Confluent" (article + capitalized word = proper noun)
    name_no_accents = _strip_accents(name).lower()
    if _RE_ARTICLE_PLUS_ONE.match(name_no_accents):
        # Check original name: if word after article is capitalized, it's likely a proper noun
        parts = name.split(None, 1)
        if len(parts) == 2 and not parts[1][0].isupper():
            return True

    # Game mechanic artifacts (e.g. "équipe 1", "groupe 3")
    if _RE_GAME_MECHANIC.match(name_no_accents):
        return True

    # Truncated entities ending with preposition
    if _RE_TRAILING_PREP.search(name):
        return True

    # Sentence fragments with conjugated verbs
    if _RE_VERB_FRAGMENT.search(name):
        return True

    # Starts with noise determinants
    if _RE_DET_START.match(name):
        return True

    # English text (indicates soundtrack/YouTube metadata)
    english_words = {"the", "of", "and", "is", "in", "to", "for", "with", "wants", "write", "near", "begins"}
    words_lower = {w.lower() for w in name.split()}
    if len(words_lower & english_words) >= 2:
        return True

    # Contains colon = likely a label or truncated heading
    if ":" in name:
        return True

    # Contains "cette/ce/cet" = sentence fragment, not proper name
    if re.search(r"\b(cette|cet)\b", name, re.IGNORECASE):
        return True

    # Descriptive phrases: past participle + preposition pattern
    # e.g. "Feux allumes sur les tours", "Dents fichees dans la roche"
    if re.search(r"\b\w+e[es]?\s+(sur|dans|sous|vers|entre|parmi|contre)\b", name_no_accents):
        return True

    # Possessive fragment: "X de leur/son/sa/ses Y" = sentence fragment, not entity name
    if re.search(r"\b(de leur|de son|de sa|de ses|de notre|de votre)\b", name_no_accents):
        return True

    # Activity/gerund phrases: "l'etude de", "la pratique de", etc.
    if re.search(r"^l'(etude|pratique|recherche|exploration|observation|utilisation)\b", name_no_accents):
        return True

    # Single common word (no article, no compound) -- too generic
    if re.match(r"^\w+$", name_no_accents) and len(name_no_accents) <= 12:
        # Single words under 12 chars are almost always generic French nouns
        # Real game entities are multi-word or distinctive names (e.g. "Nanzagouets")
        # Allow words with uppercase in the original (likely proper nouns)
        if name[0].islower():
            return True

    return False
