"""Extraction version registry — defines prompt strategies for entity extraction.

Each version bundles: system prompt, user prompt templates, chunking config,
and LLM parameters. Versions are immutable once defined — create a new version
to iterate, never edit an existing one.

Usage:
    from .extraction_versions import get_version, list_versions

    v = get_version("v2-fewshot")
    print(v.description)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ExtractionVersion:
    """Immutable extraction config."""
    name: str
    description: str

    # LLM parameters
    temperature: float = 0.1
    num_predict: int = 4000
    num_ctx: int = 8192

    # System prompt (None = not used, everything in user prompt)
    # Can be a str (same for all models) or dict[str, str] keyed by model family
    system_prompt: Optional[str] = None
    system_prompt_by_model: Optional[dict[str, str]] = None

    # User prompt template for facts+entities call
    # Placeholders: {text}
    facts_prompt: str = ""

    # User prompt template for entity-only call
    # Placeholders: {text}
    entity_prompt: str = ""

    # Chunking config
    chunk_by_paragraph: bool = False
    max_chunk_words: int = 800  # only used if chunk_by_paragraph=True

    def get_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the system prompt for a given model.

        Checks system_prompt_by_model first (matching by prefix),
        falls back to system_prompt.
        """
        if self.system_prompt_by_model and model:
            # Match by model family prefix: "qwen3:8b" matches "qwen3"
            for prefix, prompt in self.system_prompt_by_model.items():
                if model.startswith(prefix):
                    return prompt
        return self.system_prompt


# ---------------------------------------------------------------------------
# v1-baseline: everything in the user prompt, no system, no chunking
# ---------------------------------------------------------------------------

_V1_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/savoir-faire adoptes"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI : "Cercle des Sages", "Argile Vivante", "Gouffre Humide", "Faucons Chasseurs", "Caste de l'Air", "Gourdins", "Lances", "Ciels-clairs".
NON : pronoms (lui, eux, toi, nous), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere), phrases longues."""

_V1_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Rhombes", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang", "Loi du Sang".
NON : mots communs (riviere, vallee, village, nature, neige, vent, nuit, homme, femme, artisans, pecheurs, tribus), pronoms (toi, lui, eux).
Si rien, retourne {{"entities": []}}."""

V1_BASELINE = ExtractionVersion(
    name="v1-baseline",
    description="Prompt unique, pas de system, pas de chunking",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=False,
)

# ---------------------------------------------------------------------------
# v2-fewshot: system prompt + few-shot example + paragraph chunking
# System prompt adapte par modele (llama vs qwen3)
# ---------------------------------------------------------------------------

# Llama 3.1 — needs explicit encouragement to extract enough
_V2_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Tu recois du texte narratif et tu retournes du JSON.

Regles :
- Extrais TOUTES les entites nommees : institutions, castes, technologies, outils, lieux, civilisations, croyances, rituels, evenements, personnes, creatures.
- Inclus les outils simples (gourdins, lances, pieux, rhombes) et les castes (Caste de l'Air, Ciels-clairs, Sans-ciels).
- N'extrais JAMAIS : pronoms (lui, eux, toi, nous, elle), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere, nature, oiseaux, arbre), phrases completes, descriptions generiques.
- Chaque entite doit avoir un nom exact tel qu'il apparait dans le texte.
- Reponds UNIQUEMENT en JSON valide, rien d'autre.

Exemple :
Texte : "Le Cercle des Sages a ordonne la fabrication de gourdins et de lances. Les Faucons Chasseurs partent vers le Gouffre Humide. La Caste de l'Air refuse de suivre les Ciels-clairs dans leur quete."

Reponse :
{
  "technologies": ["gourdins", "lances"],
  "resources": [],
  "beliefs": [],
  "geography": ["Gouffre Humide"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "ordonne la fabrication"},
    {"name": "Gourdins", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Lances", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "partent vers le Gouffre"},
    {"name": "Gouffre Humide", "type": "place", "context": "destination des Faucons"},
    {"name": "Caste de l'Air", "type": "caste", "context": "refuse de suivre"},
    {"name": "Ciels-clairs", "type": "caste", "context": "quete refusee"}
  ]
}"""

# Qwen3 — much stricter, needs to be told what NOT to extract
_V2_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE CRITIQUE : Extrais UNIQUEMENT les NOMS PROPRES et TERMES SPECIFIQUES au jeu. Pas de noms communs francais.

EXTRAIS (noms propres du jeu) :
- Institutions nommees : "Cercle des Sages", "Hall des Serments", "Tribunal des Moeurs", "Conseil du village"
- Castes nommees : "Ciels-clairs", "Sans-ciels", "Caste de l'Air", "Enfants du Courant", "Faconneurs de Pierre"
- Technologies nommees : "Argile Vivante", "Lait de Pierre", "Rhombes", "Glyphes du Gouffre", "Ideoglyphes"
- Outils specifiques nommes : "Gourdins", "Lances", "Pieux", "Pointes de fleches"
- Lieux propres : "Gouffre Humide", "Gorge Profonde", "Morsure-des-Ancetres", "Route-riviere"
- Civilisations : "Cheveux de Sang", "Nanzagouets", "Confluents"
- Personnes nommees : "Ailes-Grises", "Faucons Chasseurs", "Voix de l'Aurore", "Porteurs de Flamme"
- Creatures nommees : "Regards-Libres", "Nantons"
- Croyances/rituels nommes : "Loi du Sang et de la Bete", "Rituel du Regard Partage", "Culte des Ancetres"
- Evenements nommes : "Grande Prospection", "Blanc sur Blanc", "Maladie des Antres"

N'EXTRAIS JAMAIS (noms communs francais, meme s'ils apparaissent dans le texte) :
- Generiques : homme, femme, enfant, tribu, peuple, vallee, riviere, montagne, village, ciel, cave, galerie, surface, grotte, antre, autels
- Animaux generiques : oiseaux, poissons, animaux, grues, mollusques, bete
- Ressources generiques : graines, baies, eau, bois, pierre, nourriture
- Activites : chasse, peche, rituels, expedition, celebration, ecriture, gravure, creusage
- Croyances vagues : esprits, ancetres, mission sacree, lois anciennes, rituels sacres
- Descriptions : vieil homme, creature, basses terres, large vallee, etendue d'eau
- Pronoms : lui, eux, toi, nous, elle, on, il

TEST : Si le mot existe dans un dictionnaire francais standard et n'est PAS un nom propre invente pour ce jeu, NE L'EXTRAIS PAS.

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Le Cercle des Sages a ordonne la fabrication de gourdins et de lances. Les Faucons Chasseurs partent vers le Gouffre Humide avec des poissons seches et de l'eau."

Reponse :
{
  "technologies": ["gourdins", "lances"],
  "resources": [],
  "beliefs": [],
  "geography": ["Gouffre Humide"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "ordonne la fabrication"},
    {"name": "Gourdins", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Lances", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "partent vers le Gouffre"},
    {"name": "Gouffre Humide", "type": "place", "context": "destination des Faucons"}
  ]
}
NOTE : "poissons", "eau" ne sont PAS extraits car ce sont des noms communs."""

_V2_FACTS_PROMPT = """Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/outils"],
  "resources": ["ressources"],
  "beliefs": ["croyances/rituels"],
  "geography": ["lieux"],
  "entities": [{{"name": "Nom exact", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V2_ENTITY_PROMPT = """Texte :
{text}

Extrais TOUTES les entites nommees en JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event|person|creature|resource", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V2_FEWSHOT = ExtractionVersion(
    name="v2-fewshot",
    description="System prompt + few-shot + chunking par paragraphes",
    system_prompt=_V2_SYSTEM_LLAMA,  # default fallback
    system_prompt_by_model={
        "qwen3": _V2_SYSTEM_QWEN,
        "llama": _V2_SYSTEM_LLAMA,
    },
    facts_prompt=_V2_FACTS_PROMPT,
    entity_prompt=_V2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_VERSIONS: dict[str, ExtractionVersion] = {
    "v1-baseline": V1_BASELINE,
    "v2-fewshot": V2_FEWSHOT,
}


def get_version(name: str) -> ExtractionVersion:
    """Get an extraction version by name. Raises KeyError if unknown."""
    if name not in _VERSIONS:
        available = ", ".join(sorted(_VERSIONS.keys()))
        raise KeyError(f"Unknown extraction version '{name}'. Available: {available}")
    return _VERSIONS[name]


def list_versions() -> list[str]:
    """Return list of available version names."""
    return sorted(_VERSIONS.keys())
