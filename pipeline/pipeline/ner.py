"""Named Entity Recognition — extracts game entities from turn text using spaCy."""

from __future__ import annotations

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
ALIAS_MAP: dict[str, str] = {
    "faucons": "Faucons Chasseurs",
    "faucon": "Faucons Chasseurs",
    "regards-libres": "Regards-Libres",
    "regard-libre": "Regards-Libres",
    "passes-bien": "Passes-bien",
    "passe-bien": "Passes-bien",
    "ailes grises": "Ailes Grises",
    "aile-grise": "Ailes Grises",
    "ailes-grises": "Ailes Grises",
    "sans-ciel": "Sans-ciels",
    "sans-ciels": "Sans-ciels",
    "sans ciel": "Sans-ciels",
    "sans ciels": "Sans-ciels",
    "ciels-clairs": "Ciels-clairs",
    "ciel-clair": "Ciels-clairs",
    "enfants du courant": "Enfants du Courant",
    "enfants des échos": "Enfants des Échos",
    "nanzagouet": "Nanzagouets",
    "nanzagouets": "Nanzagouets",
    "cheveux de sang": "Cheveux de Sang",
    "cheveux-de-sang": "Cheveux de Sang",
    "pupupasu": "Pupupasu",
    "gouffre humide": "Gouffre Humide",
    "la confluence": "La Confluence",
    "confluence": "La Confluence",
    "argile vivante": "Argile Vivante",
    "rhombes": "Rhombes",
    "grande fresque": "Grande Fresque",
    "cercle des sages": "Cercle des Sages",
    "tribunal des mœurs": "Tribunal des Mœurs",
    "tribunal des moeurs": "Tribunal des Mœurs",
    "assemblée des chefs": "Assemblée des Chefs",
    "maison des découvertes": "Maison des Découvertes",
    "arbitre des esprits": "Arbitre des Esprits",
}


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
        """Extract named entities from text."""
        doc = self.nlp(text)
        entities: list[ExtractedEntity] = []
        seen: set[str] = set()

        for ent in doc.ents:
            label = SPACY_LABEL_MAP.get(ent.label_, ent.label_.lower())
            # Skip generic labels we can't map
            if label in ("cardinal", "date", "ordinal", "percent"):
                continue

            context_start = max(0, ent.start_char - 50)
            context_end = min(len(text), ent.end_char + 50)

            # Deduplicate: use canonical name if available
            canonical = self._canonicalize(ent.text)
            dedup_key = f"{canonical}|{label}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

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
