"""Named Entity Recognition — extracts game entities from turn text using spaCy."""

from __future__ import annotations

from dataclasses import dataclass

import spacy


@dataclass
class ExtractedEntity:
    text: str
    label: str  # PERSON, PLACE, TECH, INSTITUTION, RESOURCE, CREATURE
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
}

# Map spaCy default labels to our domain
SPACY_LABEL_MAP = {
    "PER": "person",
    "LOC": "place",
    "ORG": "institution",
    "MISC": "technology",  # Default fallback, refined by classifier
}


class EntityExtractor:
    def __init__(self, model_name: str = "fr_core_news_lg"):
        self.nlp = spacy.load(model_name)
        # TODO: Add custom NER patterns for game-specific entities

    def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract named entities from text."""
        doc = self.nlp(text)
        entities: list[ExtractedEntity] = []

        for ent in doc.ents:
            label = SPACY_LABEL_MAP.get(ent.label_, ent.label_.lower())
            context_start = max(0, ent.start_char - 50)
            context_end = min(len(text), ent.end_char + 50)

            entities.append(
                ExtractedEntity(
                    text=ent.text,
                    label=label,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    context=text[context_start:context_end],
                )
            )

        return entities
