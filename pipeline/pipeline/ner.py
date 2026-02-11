"""Named Entity Recognition — extracts game entities from turn text using spaCy.

Includes noise filtering to reject entities from soundtrack metadata, choice labels,
narrative fragments, and common French words that spaCy misidentifies.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import spacy


@dataclass
class ExtractedEntity:
    text: str
    label: str  # person, place, technology, institution, resource, creature, event, civilization, caste
    start_char: int
    end_char: int
    context: str


# Custom entity labels for civilization RPG domain
CUSTOM_LABELS = {
    "TECH": "technology",
    "INSTITUTION": "institution",
    "RESOURCE": "resource",
    "CREATURE": "creature",
    "RITUAL": "event",
    "CASTE": "caste",
    "CIV": "civilization",
}

# Map spaCy default labels to our domain
SPACY_LABEL_MAP = {
    "PER": "person",
    "LOC": "place",
    "ORG": "institution",
    "MISC": "technology",
    "TECH": "technology",
    "INSTITUTION": "institution",
    "RESOURCE": "resource",
    "CREATURE": "creature",
    "RITUAL": "event",
    "CASTE": "caste",
    "CIV": "civilization",
}

# Game-specific entity patterns for the EntityRuler
GAME_ENTITY_PATTERNS = [
    # === CASTES ===
    {"label": "CASTE", "pattern": "Sans-ciels"},
    {"label": "CASTE", "pattern": "sans-ciels"},
    {"label": "CASTE", "pattern": "Sans-ciel"},
    {"label": "CASTE", "pattern": "sans ciel"},
    {"label": "CASTE", "pattern": "sans ciels"},
    {"label": "CASTE", "pattern": [{"LOWER": "enfants"}, {"LOWER": "du"}, {"LOWER": "courant"}]},
    {"label": "CASTE", "pattern": [{"LOWER": "enfants"}, {"LOWER": "des"}, {"LOWER": "échos"}]},
    {"label": "CASTE", "pattern": [{"LOWER": "ailes"}, {"LOWER": "grises"}]},
    {"label": "CASTE", "pattern": "Aile-Grise"},
    {"label": "CASTE", "pattern": "Ailes-Grises"},
    {"label": "CASTE", "pattern": "aile-grise"},
    {"label": "CASTE", "pattern": [{"LOWER": "faucons"}, {"LOWER": "chasseurs"}]},
    {"label": "CASTE", "pattern": "Faucon Chasseur"},
    {"label": "CASTE", "pattern": [{"LOWER": "regards"}, {"LOWER": "-"}, {"LOWER": "libres"}]},
    {"label": "CASTE", "pattern": "Regards-Libres"},
    {"label": "CASTE", "pattern": "Regard-Libre"},
    {"label": "CASTE", "pattern": [{"LOWER": "passes"}, {"LOWER": "-"}, {"LOWER": "bien"}]},
    {"label": "CASTE", "pattern": "Passes-bien"},
    {"label": "CASTE", "pattern": "Passe-bien"},
    {"label": "CASTE", "pattern": [{"LOWER": "voix"}, {"LOWER": "de"}, {"LOWER": "l'"}, {"LOWER": "aurore"}]},
    {"label": "CASTE", "pattern": [{"LOWER": "ciels"}, {"LOWER": "-"}, {"LOWER": "clairs"}]},
    {"label": "CASTE", "pattern": "Ciels-clairs"},
    {"label": "CASTE", "pattern": "Ciel-clair"},
    {"label": "CASTE", "pattern": "ciels-clairs"},
    {"label": "CASTE", "pattern": "ciel-clair"},

    # === TECHNOLOGIES ===
    {"label": "TECH", "pattern": [{"LOWER": "argile"}, {"LOWER": "vivante"}]},
    {"label": "TECH", "pattern": "Rhombes"},
    {"label": "TECH", "pattern": "rhombes"},
    {"label": "TECH", "pattern": [{"LOWER": "glyphes"}, {"LOWER": "du"}, {"LOWER": "gouffre"}]},
    {"label": "TECH", "pattern": [{"LOWER": "colliers"}, {"LOWER": "de"}, {"LOWER": "glyphes"}]},
    {"label": "TECH", "pattern": [{"LOWER": "grande"}, {"LOWER": "fresque"}]},
    {"label": "TECH", "pattern": [{"LOWER": "lait"}, {"LOWER": "de"}, {"LOWER": "pierre"}]},

    # === PLACES ===
    {"label": "LOC", "pattern": [{"LOWER": "la"}, {"LOWER": "confluence"}]},
    {"label": "LOC", "pattern": [{"LOWER": "gouffre"}, {"LOWER": "humide"}]},
    {"label": "LOC", "pattern": [{"LOWER": "hall"}, {"LOWER": "des"}, {"LOWER": "serments"}]},
    {"label": "LOC", "pattern": [{"LOWER": "maison"}, {"LOWER": "des"}, {"LOWER": "découvertes"}]},
    {"label": "LOC", "pattern": [{"LOWER": "antre"}, {"LOWER": "des"}, {"LOWER": "échos"}]},

    # === CIVILIZATIONS ===
    {"label": "CIV", "pattern": "Nanzagouets"},
    {"label": "CIV", "pattern": "Nanzagouet"},
    {"label": "CIV", "pattern": "Tlazhuaneca"},
    {"label": "CIV", "pattern": "Pouleheimos"},
    {"label": "CIV", "pattern": [{"LOWER": "cheveux"}, {"LOWER": "de"}, {"LOWER": "sang"}]},
    {"label": "CIV", "pattern": "Cheveux-de-Sang"},
    {"label": "CIV", "pattern": "Pupupasu"},
    {"label": "CIV", "pattern": "Siliaska"},
    {"label": "CIV", "pattern": [{"LOWER": "civilisation"}, {"LOWER": "de"}, {"LOWER": "la"}, {"LOWER": "confluence"}]},

    # === INSTITUTIONS ===
    {"label": "INSTITUTION", "pattern": [{"LOWER": "cercle"}, {"LOWER": "des"}, {"LOWER": "sages"}]},
    {"label": "INSTITUTION", "pattern": [{"LOWER": "tribunal"}, {"LOWER": "des"}, {"LOWER": "mœurs"}]},
    {"label": "INSTITUTION", "pattern": [{"LOWER": "tribunal"}, {"LOWER": "des"}, {"LOWER": "moeurs"}]},
    {"label": "INSTITUTION", "pattern": [{"LOWER": "assemblée"}, {"LOWER": "des"}, {"LOWER": "chefs"}]},
    {"label": "INSTITUTION", "pattern": [{"LOWER": "maison"}, {"LOWER": "des"}, {"LOWER": "découvertes"}]},

    # === ROLES / TITLES ===
    {"label": "INSTITUTION", "pattern": [{"LOWER": "arbitre"}, {"LOWER": "des"}, {"LOWER": "esprits"}]},

    # === RITUALS / EVENTS ===
    {"label": "RITUAL", "pattern": [{"LOWER": "rituel"}, {"LOWER": "du"}, {"LOWER": "regard"}, {"LOWER": "partagé"}]},
    {"label": "RITUAL", "pattern": [{"LOWER": "maladie"}, {"LOWER": "des"}, {"LOWER": "antres"}]},
]

# Short forms that should map to canonical names
# Alias map: kept minimal. Case + plurals are handled programmatically
# in runner.py _normalize_for_dedup(). Only truly semantic aliases here.
ALIAS_MAP: dict[str, str] = {}


# ============================================================
# NOISE FILTERING
# ============================================================

# Known noise entity names from spaCy general model
# Stored WITHOUT accents — comparison uses _strip_accents() for robustness
_NOISE_NAMES = {
    # Soundtrack / YouTube artists
    "geiita", "bartosz pokrywka", "carolina romero", "rithelgo",
    "bartosz pokrywka - topic", "youtube", "jimmys g", "deadfire",
    # Generic French words misidentified as entities
    "blanc", "hier", "rare", "but", "observer", "transporter",
    "organisation", "formes", "halls", "hall", "cercle", "antre",
    "biens", "autre", "autres", "chef du", "gardiens de",
    "mienne", "toutes", "message", "si",
    "village", "methode", "couche", "premiers", "esprits",
    "lances", "sculptures", "tribunal", "shamans",
    "amelioration", "conseil", "acquisitions",
    "posseder", "ramassez",
    "faucon", "cercles", "echos", "equipes", "cliques",
    "rubanc", "sanciel", "sanciels",  # player name, ambiguous short form
    # Common false-positive persons/adjectives
    "ravitaille", "touche", "planche", "libre", "lootbox", "farouche",
    "montes", "proclamateurs", "nantons", "nanton",
    # Misc fragments and generic words
    "origines", "couche", "feux", "foyer", "porteurs",
    "premier", "premiers", "sel", "antres",
    "faconneurs", "echanges", "medier",
    "l'autre", "le sel", "la fresque",
    "oracle",  # too generic without context
    "l'antre",  # too generic (vs "antre des Echos" which is specific)
    "posture militaire",  # game mechanic descriptor, not entity
    "vallee",  # too generic on its own
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


def _strip_accents(text: str) -> str:
    """Remove diacritics for accent-insensitive matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _is_noise_entity(name: str) -> bool:
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
    name_no_accents = _strip_accents(name).lower()
    if re.search(r"\b\w+e[es]?\s+(sur|dans|sous|vers|entre|parmi|contre)\b", name_no_accents):
        return True

    return False


class EntityExtractor:
    def __init__(self, model_name: str = "fr_core_news_lg"):
        self.nlp = spacy.load(model_name)
        self._add_entity_ruler()

    def _add_entity_ruler(self) -> None:
        """Add an EntityRuler with game-specific patterns before the NER component."""
        ruler = self.nlp.add_pipe(
            "entity_ruler", before="ner", config={"overwrite_ents": True}
        )
        ruler.add_patterns(GAME_ENTITY_PATTERNS)  # type: ignore[union-attr]

    def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract named entities from text, filtering out noise."""
        doc = self.nlp(text)
        entities: list[ExtractedEntity] = []
        seen: set[str] = set()

        for ent in doc.ents:
            label = SPACY_LABEL_MAP.get(ent.label_, ent.label_.lower())
            # Skip generic labels we can't map
            if label in ("cardinal", "date", "ordinal", "percent"):
                continue

            # Deduplicate: use canonical name if available
            canonical = self._canonicalize(ent.text)

            # Filter noise before anything else
            if _is_noise_entity(canonical):
                continue

            dedup_key = f"{canonical}|{label}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            context_start = max(0, ent.start_char - 50)
            context_end = min(len(text), ent.end_char + 50)

            entities.append(
                ExtractedEntity(
                    text=canonical,
                    label=label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    context=text[context_start:context_end],
                )
            )

        return entities

    def _canonicalize(self, text: str) -> str:
        """Map aliases and short forms to canonical names."""
        lower = text.lower().strip()
        return ALIAS_MAP.get(lower, text)
