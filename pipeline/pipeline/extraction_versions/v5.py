"""v5-schema: temperature 0 + Ollama format schema + v4 prompt base.

Research-backed: schema enforcement >> prompt-only JSON instruction.
"""

from .base import ExtractionVersion

# JSON schema for Ollama format parameter -- facts+entities call
_V5_FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "technologies": {"type": "array", "items": {"type": "string"}},
        "resources": {"type": "array", "items": {"type": "string"}},
        "beliefs": {"type": "array", "items": {"type": "string"}},
        "geography": {"type": "array", "items": {"type": "string"}},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": [
                        "person", "place", "technology", "institution",
                        "resource", "creature", "event", "civilization",
                        "caste", "belief"
                    ]},
                    "context": {"type": "string"}
                },
                "required": ["name", "type", "context"]
            }
        }
    },
    "required": ["technologies", "resources", "beliefs", "geography", "entities"]
}

# JSON schema for entity-only call
_V5_ENTITY_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": [
                        "person", "place", "technology", "institution",
                        "resource", "creature", "event", "civilization",
                        "caste", "belief"
                    ]},
                    "context": {"type": "string"}
                },
                "required": ["name", "type", "context"]
            }
        }
    },
    "required": ["entities"]
}

# System prompt: v4 checklist base + anti-hallucination, but NO /no_think
# Research says: for structured extraction, let qwen3 think then constrain output with schema
_V5_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent MOT POUR MOT dans le texte. ZERO invention. ZERO paraphrase.

METHODE : Pour CHAQUE categorie ci-dessous, relis le texte et cherche TOUTES les occurrences :

1. CASTES : tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des..." (Enfants du Courant, Enfants des Echos), "Caste de..."
2. PERSONNES/GROUPES : tirets (Ailes-Grises), groupes (Faucons Chasseurs, Proclamateurs, Traqueurs)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des..."
4. LIEUX : tout nom de lieu (Gouffre Humide, Arene, Confluence), "Zone + adjectif" (Zone chaude), "Antres des..."
5. TECHNOLOGIES : tout objet/outil/technique nomme (Argile Vivante, Rhombes, Lances, Pilotis, Blocs standardises)
6. CROYANCES/LOIS : "Loi de/du...", "Rituel du...", "Yeux de...", "Culte des..."
7. EVENEMENTS : evenements nommes (Grande Prospection, Blanc sur Blanc)
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

INTERDIT : mots generiques isoles (homme, femme, riviere, village, tribu), pronoms, entites inventees.

IMPORTANT : Chaque mention compte. Meme si un nom n'apparait qu'UNE SEULE FOIS dans le texte, extrais-le."""

_V5_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation.

Extrais UNIQUEMENT des noms qui apparaissent MOT POUR MOT dans le texte. Jamais d'invention.
Verifie chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
Chaque mention compte, meme les mentions uniques."""

_V5_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie (castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures).
Pour chaque categorie, relis le texte attentivement et extrais TOUTES les mentions.
Les noms doivent etre COPIES mot pour mot du texte."""

_V5_ENTITY_PROMPT = """Texte :
{text}

Relis le texte categorie par categorie et extrais TOUT :
1. Castes ? (tirets, "Enfants de/du...", "Caste de...")
2. Personnes/groupes ? (tirets, titres de groupes)
3. Institutions ? ("Cercle des...", "Tribunal des...", "Maison des...")
4. Lieux ? (noms propres, "Zone + adjectif", "Antres des...")
5. Technologies/outils ? (tout objet nomme, meme simple)
6. Croyances/lois ?
7. Evenements ?
8. Civilisations ?
9. Creatures ?

Chaque mention dans le texte = une entite a extraire. Nom COPIE du texte."""

V5_SCHEMA = ExtractionVersion(
    name="v5-schema",
    description="Temperature 0 + Ollama format schema + checklist exhaustive",
    temperature=0.0,
    system_prompt=_V5_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V5_SYSTEM_QWEN,
        "llama": _V5_SYSTEM_LLAMA,
    },
    facts_prompt=_V5_FACTS_PROMPT,
    entity_prompt=_V5_ENTITY_PROMPT,
    facts_format=_V5_FACTS_SCHEMA,
    entity_format=_V5_ENTITY_SCHEMA,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V5: dict[str, ExtractionVersion] = {
    "v5-schema": V5_SCHEMA,
}
