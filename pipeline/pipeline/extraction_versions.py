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
    seed: Optional[int] = None  # Fixed seed for deterministic output

    # System prompt (None = not used, everything in user prompt)
    # Can be a str (same for all models) or dict[str, str] keyed by model family
    system_prompt: Optional[str] = None
    system_prompt_by_model: Optional[dict[str, str]] = None

    # User prompt template for facts+entities call
    # Placeholders: {text}
    facts_prompt: str = ""
    # Per-model user prompt overrides (same pattern as system_prompt_by_model)
    facts_prompt_by_model: Optional[dict[str, str]] = None

    # User prompt template for entity-only call
    # Placeholders: {text}
    entity_prompt: str = ""
    # Per-model user prompt overrides
    entity_prompt_by_model: Optional[dict[str, str]] = None

    # Ollama format parameter — JSON schema to constrain output structure
    # When set, Ollama enforces the schema at generation level (not just prompt)
    facts_format: Optional[dict] = None
    entity_format: Optional[dict] = None

    # GPT-NER style marking prompt — LLM rewrites text with @@entity## markers
    # When set, adds a 3rd LLM call per chunk using this approach
    mark_prompt: Optional[str] = None
    mark_system_prompt: Optional[str] = None
    mark_system_prompt_by_model: Optional[dict[str, str]] = None

    # Validation pass — LLM filters extracted entities with a checklist
    validate_prompt: Optional[str] = None
    validate_system_prompt: Optional[str] = None
    validate_system_prompt_by_model: Optional[dict[str, str]] = None

    # Certainty score config — LLM self-assesses confidence per entity
    # certainty_scale: (min, max) — e.g. (1, 3) or (1, 10)
    # certainty_threshold: entities below this score are filtered out (0 = disabled)
    certainty_scale: tuple = (1, 3)
    certainty_threshold: int = 0  # 0 = no filtering (backwards compat)

    # Chunking config
    chunk_by_paragraph: bool = False
    max_chunk_words: int = 800  # only used if chunk_by_paragraph=True

    @staticmethod
    def _model_matches_prefix(model: str, prefix: str) -> bool:
        """Check if a model name matches a prefix.

        Handles both Ollama names (qwen3:8b) and OpenRouter IDs (qwen/qwen3-8b).
        """
        return model.startswith(prefix) or f"/{prefix}" in model

    def get_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the system prompt for a given model.

        Checks system_prompt_by_model first (matching by prefix),
        falls back to system_prompt.
        """
        if self.system_prompt_by_model and model:
            # Match by model family prefix: "qwen3:8b" matches "qwen3"
            for prefix, prompt in self.system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.system_prompt

    def get_mark_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the mark system prompt for a given model."""
        if self.mark_system_prompt_by_model and model:
            for prefix, prompt in self.mark_system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.mark_system_prompt

    def get_validate_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the validate system prompt for a given model."""
        if self.validate_system_prompt_by_model and model:
            for prefix, prompt in self.validate_system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.validate_system_prompt

    def get_facts_prompt(self, model: str = "") -> str:
        """Return the facts+entities user prompt for a given model.

        Checks facts_prompt_by_model first (matching by prefix),
        falls back to facts_prompt.
        """
        if self.facts_prompt_by_model and model:
            for prefix, prompt in self.facts_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.facts_prompt

    def get_entity_prompt(self, model: str = "") -> str:
        """Return the entity-only user prompt for a given model.

        Checks entity_prompt_by_model first (matching by prefix),
        falls back to entity_prompt.
        """
        if self.entity_prompt_by_model and model:
            for prefix, prompt in self.entity_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.entity_prompt


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
# v3-recall: optimized for high recall without sacrificing too much precision
# Key changes vs v2: softer exclusion list, richer few-shot, explicit
# instruction to extract ALL mentions even minor ones.
# ---------------------------------------------------------------------------

_V3_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

MISSION : Extrais TOUTES les entites nommees du texte. Prefere extraire trop que pas assez. En cas de doute, EXTRAIS.

TYPES VALIDES : person, place, technology, institution, resource, creature, event, civilization, caste, belief

CE QUI EST UNE ENTITE (extrais toujours) :
- Noms avec majuscule ou tirets : "Ailes-Grises", "Sans-ciels", "Passes-bien", "Regards-Libres"
- Groupes nommes : "Faucons Chasseurs", "Enfants du Courant", "Enfants des Echos", "Proclamateurs", "Traqueurs"
- Institutions : "Cercle des Sages", "Hall des Serments", "Confluence des Echanges", "Tribunal des Moeurs"
- Lieux nommes, meme descriptifs : "Zone chaude", "Zone froide", "Zone humide", "Zone seche", "Antres des Echos", "Basses terres"
- Technologies et outils : "Argile Vivante", "Lances", "Gourdins", "Rhombes", "Ideoglyphes", "Pilotis", "Blocs standardises"
- Croyances et lois : "Loi du Sang et de la Bete", "Yeux de l'aurore", "Culte des Ancetres"
- Evenements : "Grande Prospection", "Rituel du Regard Partage", "Blanc sur Blanc"
- Civilisations : "Cheveux de Sang", "Nanzagouets", "Confluents", "Siliaska"

CE QUI N'EST PAS UNE ENTITE (n'extrais jamais) :
- Pronoms : lui, eux, toi, nous, elle, on, il
- Mots isoles generiques sans contexte de jeu : homme, femme, eau, bois, pierre, riviere, montagne, village
- Phrases completes ou descriptions longues

ATTENTION AUX PIEGES :
- "Proclamateurs" = entite (groupe nomme), pas un mot generique
- "Lances" = entite (technologie du jeu), pas juste un nom commun
- "Zone chaude" = entite (lieu dans la Maison des Decouvertes), pas une description
- "Antres des Echos" = entite (lieu), meme si "antre" est un mot courant
- "Basses terres" = entite (region), meme si ca ressemble a une description
- "Passes-bien" = entite (caste), meme si ca ne ressemble pas a un nom propre

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Le Cercle des Sages se reunit dans la Zone chaude de la Maison des Decouvertes. Les Passes-bien et les Sans-ciels debattent. Les Proclamateurs annoncent que les Lances seront distribuees aux Faucons Chasseurs. Ailes-Grises invoque la Loi du Sang."

Reponse :
{
  "technologies": ["Lances"],
  "resources": [],
  "beliefs": ["Loi du Sang"],
  "geography": ["Zone chaude", "Maison des Decouvertes"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "se reunit"},
    {"name": "Zone chaude", "type": "place", "context": "dans la Maison des Decouvertes"},
    {"name": "Maison des Decouvertes", "type": "institution", "context": "lieu de reunion"},
    {"name": "Passes-bien", "type": "caste", "context": "debattent"},
    {"name": "Sans-ciels", "type": "caste", "context": "debattent"},
    {"name": "Proclamateurs", "type": "person", "context": "annoncent la distribution"},
    {"name": "Lances", "type": "technology", "context": "distribuees"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "recoivent les lances"},
    {"name": "Ailes-Grises", "type": "person", "context": "invoque la Loi"},
    {"name": "Loi du Sang", "type": "belief", "context": "invoquee par Ailes-Grises"}
  ]
}"""

_V3_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

MISSION : Extrais TOUTES les entites nommees. En cas de doute, extrais.

Types : person, place, technology, institution, resource, creature, event, civilization, caste, belief

Inclus : noms avec majuscules/tirets, groupes nommes, institutions, lieux (meme descriptifs comme "Zone chaude"), technologies/outils, croyances, evenements, civilisations.
Exclus : pronoms, mots isoles generiques (homme, femme, eau, bois, pierre).

Reponds UNIQUEMENT en JSON valide."""

_V3_FACTS_PROMPT = """Texte :
{text}

Extrais TOUTES les entites et faits. Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/outils nommes"],
  "resources": ["ressources nommees"],
  "beliefs": ["croyances/rituels/lois nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom exact du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

IMPORTANT : N'oublie aucune entite. Chaque nom propre, groupe, lieu, institution, technologie, caste mentionne dans le texte doit apparaitre."""

_V3_ENTITY_PROMPT = """Texte :
{text}

Extrais TOUTES les entites nommees. Cherche particulierement :
- Castes et groupes sociaux (noms avec tirets, "Enfants de/du...")
- Lieux specifiques (meme "Zone X", "Antres de...")
- Technologies et outils (meme simples comme "Lances", "Pilotis")
- Institutions et lois
- Personnes et creatures nommees

JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event|person|creature|resource", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V3_RECALL = ExtractionVersion(
    name="v3-recall",
    description="Optimise pour le recall -- prompt plus permissif, few-shot riche",
    system_prompt=_V3_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V3_SYSTEM_QWEN,
        "llama": _V3_SYSTEM_LLAMA,
    },
    facts_prompt=_V3_FACTS_PROMPT,
    entity_prompt=_V3_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v4-strict-recall: maximum recall with anti-hallucination guard
# Strategy: exhaustive category checklist + "copy from text" rule
# ---------------------------------------------------------------------------

_V4_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent TEXTUELLEMENT dans le passage. JAMAIS de paraphrase, synonyme, ou invention. Si le texte dit "Argile Vivante", extrais "Argile Vivante" -- pas "Argile qui vit", pas "argile".

METHODE : Lis le texte, puis passe en revue CHAQUE categorie ci-dessous. Pour chaque categorie, relis le texte et cherche TOUTES les mentions.

CATEGORIES A VERIFIER (dans cet ordre) :
1. CASTES : noms avec tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des..." (Enfants du Courant, Enfants des Echos), "Caste de..."
2. PERSONNES/GROUPES : noms avec tirets (Ailes-Grises), titres de groupes (Faucons Chasseurs, Proclamateurs, Traqueurs, Porteurs de Flamme)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des...", "Conseil..."
4. LIEUX : noms propres (Gouffre Humide, Confluence, Arene), "Zone + adjectif" (Zone chaude, Zone froide), "Antres des...", tout lieu avec majuscule
5. TECHNOLOGIES : objets nommes (Argile Vivante, Rhombes, Glyphes du Gouffre, Ideoglyphes, Lances, Gourdins, Pieux, Pilotis, Blocs standardises, Lait de Pierre)
6. CROYANCES/LOIS : "Loi de/du...", "Culte des...", "Rituel du...", "Yeux de..."
7. EVENEMENTS : "Grande Prospection", "Blanc sur Blanc", "Maladie des..."
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

INTERDIT :
- Inventer des entites absentes du texte
- Paraphraser (le nom doit etre COPIE du texte tel quel)
- Extraire des mots generiques isoles : homme, femme, eau, bois, pierre, riviere, village, tribu, peuple
- Extraire des pronoms : lui, eux, toi, nous

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Les Sans-ciels et les Enfants du Courant se reunissent a l'Arene pres de la Zone chaude. Ailes-Grises brandit les Lances devant le Cercle des Sages. Les Proclamateurs invoquent la Loi du Sang et de la Bete."

Reponse :
{
  "technologies": ["Lances"],
  "resources": [],
  "beliefs": ["Loi du Sang et de la Bete"],
  "geography": ["Arene", "Zone chaude"],
  "entities": [
    {"name": "Sans-ciels", "type": "caste", "context": "se reunissent a l'Arene"},
    {"name": "Enfants du Courant", "type": "caste", "context": "se reunissent a l'Arene"},
    {"name": "Arene", "type": "place", "context": "lieu de reunion"},
    {"name": "Zone chaude", "type": "place", "context": "pres de l'Arene"},
    {"name": "Ailes-Grises", "type": "person", "context": "brandit les Lances"},
    {"name": "Lances", "type": "technology", "context": "brandies par Ailes-Grises"},
    {"name": "Cercle des Sages", "type": "institution", "context": "devant le Cercle"},
    {"name": "Proclamateurs", "type": "person", "context": "invoquent la Loi"},
    {"name": "Loi du Sang et de la Bete", "type": "belief", "context": "invoquee par Proclamateurs"}
  ]
}
NOTE : 9 entites extraites pour 3 phrases. Sois aussi exhaustif."""

_V4_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE : Extrais UNIQUEMENT des noms qui apparaissent TEXTUELLEMENT. Jamais de paraphrase ou invention.
Passe en revue chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
Sois exhaustif -- chaque mention compte.

Reponds UNIQUEMENT en JSON valide."""

_V4_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie (castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures) et extrais TOUT.

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V4_ENTITY_PROMPT = """Texte :
{text}

CHECKLIST -- relis le texte pour chaque categorie et extrais TOUT ce que tu trouves :
- Castes ? (noms avec tirets, "Enfants de/du...", "Caste de...")
- Personnes/groupes ? (noms avec tirets, titres de groupes)
- Institutions ? ("Cercle des...", "Hall des...", "Tribunal des...", "Maison des...")
- Lieux ? (noms propres, "Zone + adjectif", "Antres des...")
- Technologies/outils ? (tout objet, technique, invention nomme)
- Croyances/lois ? ("Loi de...", "Rituel du...", "Culte des...")
- Evenements ?
- Civilisations ?
- Creatures ?

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V4_STRICT_RECALL = ExtractionVersion(
    name="v4-strict-recall",
    description="Recall maximum -- checklist par categorie + anti-hallucination",
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V4_FACTS_PROMPT,
    entity_prompt=_V4_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v5-schema: temperature 0 + Ollama format schema + v4 prompt base
# Research-backed: schema enforcement >> prompt-only JSON instruction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# v6-combo: best of v4 (checklist+/no_think) + v5 (temp 0, format schema)
# Lecons: /no_think obligatoire (sinon thinking brule num_predict et JSON tronque)
#         format schema elimine JSON malformed, temp 0 = deterministe
#         prompt plus court car le schema fait le boulot de structure
# ---------------------------------------------------------------------------

# Reuse v5 schemas -- they work, the problem was thinking mode
_V6_FACTS_SCHEMA = _V5_FACTS_SCHEMA
_V6_ENTITY_SCHEMA = _V5_ENTITY_SCHEMA

_V6_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent MOT POUR MOT dans le texte. ZERO invention, ZERO paraphrase.

METHODE -- pour CHAQUE categorie, relis le texte et note TOUTES les occurrences :
1. CASTES : tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des...", "Caste de..."
2. PERSONNES/GROUPES : tirets (Ailes-Grises), groupes nommes (Faucons Chasseurs, Proclamateurs, Traqueurs)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des..."
4. LIEUX : noms propres (Gouffre Humide, Arene, Confluence), "Zone + adjectif", "Antres des..."
5. TECHNOLOGIES : tout objet/outil nomme (Argile Vivante, Rhombes, Lances, Pilotis, Blocs standardises)
6. CROYANCES/LOIS : "Loi de/du...", "Rituel du...", "Yeux de...", "Culte des..."
7. EVENEMENTS : Grande Prospection, Blanc sur Blanc, etc.
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

INTERDIT : mots generiques isoles (homme, femme, riviere, village, tribu, maison, foyer, outils, briques), pronoms, entites inventees, "Chef du X" (extrais X pas "Chef du X").

Chaque mention compte, meme une seule occurrence.

/no_think"""

_V6_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation.
Extrais UNIQUEMENT des noms MOT POUR MOT du texte. Jamais d'invention.
Verifie chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
Chaque mention compte."""

# Prompts plus courts -- le format schema gere la structure, le prompt se concentre sur la tache
_V6_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie et extrais TOUTES les mentions. Noms COPIES mot pour mot du texte.

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V6_ENTITY_PROMPT = """Texte :
{text}

Relis le texte categorie par categorie. Extrais CHAQUE entite nommee, meme mentionnee une seule fois.
Noms COPIES mot pour mot du texte.

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V6_COMBO = ExtractionVersion(
    name="v6-combo",
    description="v4 checklist + /no_think + temp 0 + short prompt -- no format schema (causes truncation)",
    temperature=0.0,
    system_prompt=_V6_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V6_SYSTEM_QWEN,
        "llama": _V6_SYSTEM_LLAMA,
    },
    facts_prompt=_V6_FACTS_PROMPT,
    entity_prompt=_V6_ENTITY_PROMPT,
    # No format schema -- conflicts with /no_think on qwen3, causes truncated output
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v8-negshot: v7 base (v4+temp0) + negative few-shot examples
# Key insight: small LLMs learn more from "DON'T do this" examples than rules
# Targets the 6 FP patterns: generics, Chef de X, paraphrases, descriptions,
# hallucinations from other turns, inventions
# ---------------------------------------------------------------------------

_V8_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent TEXTUELLEMENT dans le passage. JAMAIS de paraphrase, synonyme, ou invention.

METHODE : Lis le texte, puis passe en revue CHAQUE categorie ci-dessous. Pour chaque categorie, relis le texte et cherche TOUTES les mentions.

CATEGORIES A VERIFIER (dans cet ordre) :
1. CASTES : noms avec tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des..." (Enfants du Courant, Enfants des Echos), "Caste de..."
2. PERSONNES/GROUPES : noms avec tirets (Ailes-Grises), titres de groupes (Faucons Chasseurs, Proclamateurs, Traqueurs, Porteurs de Flamme)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des...", "Conseil..."
4. LIEUX : noms propres (Gouffre Humide, Confluence, Arene), "Zone + adjectif" (Zone chaude, Zone froide), "Antres des...", tout lieu avec majuscule
5. TECHNOLOGIES : objets nommes (Argile Vivante, Rhombes, Glyphes du Gouffre, Ideoglyphes, Lances, Gourdins, Pieux, Pilotis, Blocs standardises, Lait de Pierre)
6. CROYANCES/LOIS : "Loi de/du...", "Culte des...", "Rituel du...", "Yeux de..."
7. EVENEMENTS : "Grande Prospection", "Blanc sur Blanc", "Maladie des..."
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

ERREURS A NE PAS FAIRE (exemples concrets) :
- PAS de mots generiques seuls : "Foyer" NON, "Maison" NON, "Entree" NON, "Montagnes" NON, "Vallee" NON, "Briques" NON, "Resines" NON, "Fibres" NON. Par contre "Maison des Decouvertes" OUI, "Foyer du Savoir" OUI.
- PAS de "Chef de/du X" : "Chef du Cercle des Sages" NON -> extrais "Cercle des Sages". "Chef du Tribunal" NON -> extrais "Tribunal des Moeurs".
- PAS de paraphrases : "Argile qui vit" NON -> le vrai nom est "Argile Vivante". "Rhombes geants" NON -> le vrai nom est "Rhombes". "Oiseaux qui comprennent" NON.
- PAS de descriptions generiques : "Outils tranchants" NON, "Argile et os" NON, "Riviere bleue" NON, "Sagesse des sommets" NON.
- PAS d'entites inventees : si le nom n'apparait pas EXACTEMENT dans le texte, ne l'extrais pas.

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Le chef du Cercle des Sages ordonne aux Sans-ciels de fabriquer de l'argile vivante dans la maison. Les Faucons Chasseurs partent vers l'Arene avec des outils tranchants et des briques."

BON :
{
  "technologies": ["argile vivante"],
  "resources": [],
  "beliefs": [],
  "geography": ["Arene"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "ordonne la fabrication"},
    {"name": "Sans-ciels", "type": "caste", "context": "fabriquent argile vivante"},
    {"name": "Argile Vivante", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "partent vers l'Arene"},
    {"name": "Arene", "type": "place", "context": "destination des Faucons"}
  ]
}
MAUVAIS (ne fais JAMAIS ca) : "Chef du Cercle des Sages", "maison", "outils tranchants", "briques", "argile qui vit"."""

_V8_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

Extrais UNIQUEMENT des noms EXACTS du texte. Pas de paraphrase, pas d'invention.
Verifie chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
NE FAIS PAS : mots seuls generiques (maison, foyer, briques), "Chef du X" (extrais X), paraphrases (argile qui vit -> Argile Vivante).
Reponds UNIQUEMENT en JSON valide."""

_V8_FACTS_PROMPT = _V4_FACTS_PROMPT
_V8_ENTITY_PROMPT = _V4_ENTITY_PROMPT

V8_NEGSHOT = ExtractionVersion(
    name="v8-negshot",
    description="v7 (v4+temp0) + negative few-shot pour neutraliser les FP",
    temperature=0.0,
    system_prompt=_V8_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V8_SYSTEM_QWEN,
        "llama": _V8_SYSTEM_LLAMA,
    },
    facts_prompt=_V8_FACTS_PROMPT,
    entity_prompt=_V8_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v9-neginuser: v4 system prompt (concis, ca marche) + temp 0 +
# negative examples dans le USER prompt au lieu du system prompt
# Lecon v8: system prompt trop gros -> LLM se noie -> 0 output
# ---------------------------------------------------------------------------

_V9_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie (castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures) et extrais TOUT.

ATTENTION -- erreurs courantes a eviter :
- "Chef du Cercle des Sages" -> extrais "Cercle des Sages" (pas le titre)
- "argile qui vit" -> extrais "Argile Vivante" (nom exact, pas paraphrase)
- "maison", "foyer", "briques", "outils" seuls -> N'EXTRAIS PAS (trop generique)
- "Rhombes geants" -> extrais "Rhombes" (nom exact sans adjectif ajoute)

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V9_ENTITY_PROMPT = """Texte :
{text}

CHECKLIST -- relis le texte pour chaque categorie et extrais TOUT ce que tu trouves :
- Castes ? (noms avec tirets, "Enfants de/du...", "Caste de...")
- Personnes/groupes ? (noms avec tirets, titres de groupes)
- Institutions ? ("Cercle des...", "Hall des...", "Tribunal des...", "Maison des...")
- Lieux ? (noms propres, "Zone + adjectif", "Antres des...")
- Technologies/outils ? (tout objet, technique, invention nomme)
- Croyances/lois ? ("Loi de...", "Rituel du...", "Culte des...")
- Evenements ?
- Civilisations ?
- Creatures ?

ATTENTION : pas de mots generiques seuls (maison, foyer, briques), pas de "Chef du X", pas de paraphrases.

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V9_NEGINUSER = ExtractionVersion(
    name="v9-neginuser",
    description="v4 system (concis) + temp 0 + negative examples dans user prompt",
    temperature=0.0,
    # Reuse v4 system prompt -- proven to work, right size for 8B model
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V9_FACTS_PROMPT,
    entity_prompt=_V9_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v10-mark: v7 base + GPT-NER style marking as 3rd LLM call
# The LLM rewrites the text with @@entity## markers — more natural for
# generative models, catches entities the JSON calls miss.
# ---------------------------------------------------------------------------

_V10_MARK_SYSTEM_QWEN = """Tu recois un texte de jeu de civilisation. Reecris-le en marquant CHAQUE entite nommee avec @@nom## .

Entites a marquer : castes, personnes, groupes, institutions, lieux, technologies, outils, croyances, lois, evenements, civilisations, creatures.

NE marque PAS : pronoms (lui, eux), mots generiques seuls (homme, village, riviere, maison).

/no_think
Reecris le texte COMPLET. Ne saute aucune phrase."""

_V10_MARK_SYSTEM_LLAMA = _V10_MARK_SYSTEM_QWEN

_V10_MARK_PROMPT = """Texte :
{text}

Reecris ce texte en marquant chaque entite nommee avec @@nom## . Garde le texte complet, change SEULEMENT en ajoutant les marqueurs.

Exemple :
"Les Sans-ciels se reunissent a l'Arene. Ailes-Grises brandit les Lances."
->
"Les @@Sans-ciels## se reunissent a l'@@Arene##. @@Ailes-Grises## brandit les @@Lances##."

Maintenant, reecris le texte ci-dessus avec les marqueurs :"""

V10_MARK = ExtractionVersion(
    name="v10-mark",
    description="v7 + GPT-NER marking (3e appel LLM par chunk)",
    temperature=0.0,
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V4_FACTS_PROMPT,
    entity_prompt=_V4_ENTITY_PROMPT,
    mark_prompt=_V10_MARK_PROMPT,
    mark_system_prompt=_V10_MARK_SYSTEM_LLAMA,
    mark_system_prompt_by_model={
        "qwen3": _V10_MARK_SYSTEM_QWEN,
        "llama": _V10_MARK_SYSTEM_LLAMA,
    },
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v11-heavy: prompt lourd, agnostique a toute civilisation
# Zero exemple specifique -- decrit la TACHE, pas les reponses
# Heavy user prompt avec marqueurs IMPORTANT/CRITICAL
# System prompt court, user prompt martele les regles
# ---------------------------------------------------------------------------

_V11_SYSTEM_QWEN = """Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. Tu dois les detecter dans le texte.

/no_think
Reponds UNIQUEMENT en JSON valide."""

_V11_SYSTEM_LLAMA = """Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. Tu dois les detecter dans le texte.

Reponds UNIQUEMENT en JSON valide."""

_V11_FACTS_PROMPT = """Tu recois un extrait d'un jeu de role civilisationnel. Les joueurs INVENTENT des noms pour tout : leurs castes, institutions, lieux, technologies, croyances, creatures, evenements. Ces noms N'EXISTENT PAS dans le monde reel. Ton travail est de les trouver TOUS.

=== IMPORTANT : QU'EST-CE QU'UNE ENTITE DE JDR ? ===

Une entite de JDR est un nom INVENTE par le joueur ou le MJ pour designer quelque chose dans le monde du jeu. Ce sont des noms propres FICTIFS.

Indices pour reconnaitre une entite de JDR :
- Un nom avec des majuscules qui ne designe PAS un objet du quotidien : c'est probablement une entite
- Un nom compose avec des tirets (X-Y, X-des-Y) : c'est TRES PROBABLEMENT une entite (caste, personne, lieu)
- Un groupe de mots qui fonctionne comme un nom propre ("Enfants du X", "Cercle des X", "Maison des X") : c'est une entite
- Un mot ordinaire utilise comme nom propre dans le contexte du jeu (une technologie, un lieu, une caste) : c'est une entite
- Un nom de civilisation, peuple, ou nation etrangere : c'est une entite

=== CRITICAL : CE QUI N'EST PAS UNE ENTITE ===

- Les mots generiques du francais courant utilises normalement : homme, femme, enfant, riviere, montagne, village, maison, outil, eau, bois, pierre
- Les pronoms : il, elle, lui, eux, nous, toi, on
- Les titres suivis d'un nom ("Chef du X", "Leader des X") : extrais X, pas le titre complet
- Les descriptions ou paraphrases : si le texte dit "les outils tranchants", c'est une description, pas un nom invente

=== IMPORTANT : METHODE D'EXTRACTION ===

Lis le texte attentivement. Pour CHAQUE phrase, demande-toi : "Y a-t-il un nom invente ici ?"

Cherche dans cet ordre :
1. Les noms avec tirets ou majuscules inhabituelles
2. Les groupes nominaux qui fonctionnent comme des noms propres
3. Les noms de groupes sociaux, castes, classes, factions
4. Les noms d'institutions, assemblees, conseils, tribunaux
5. Les noms de lieux specifiques au jeu
6. Les noms de technologies, inventions, savoir-faire specifiques
7. Les noms de croyances, lois, rituels
8. Les noms d'evenements historiques du jeu
9. Les noms de civilisations ou peuples
10. Les noms de creatures specifiques au jeu

=== CRITICAL : REGLE D'OR ===

Le nom que tu extrais doit etre COPIE MOT POUR MOT du texte. ZERO invention, ZERO paraphrase. Si tu n'es pas sur qu'un mot est une entite inventee, EXTRAIS-LE QUAND MEME. Il vaut mieux extraire trop que pas assez.

=== EXEMPLE (civilisation fictive, PAS dans le jeu) ===

Texte : "Les Marche-Nuages se reunissent au Sanctuaire des Vents. Le Conseil des Souffles decide d'envoyer les Porteurs d'Ecume vers la Faille Blanche. Ils emportent des Pierres-Souffle et du bois. La Loi des Trois Ciels interdit tout retour avant la prochaine Convergence."

Reponse :
{{
  "technologies": ["Pierres-Souffle"],
  "resources": [],
  "beliefs": ["Loi des Trois Ciels"],
  "geography": ["Sanctuaire des Vents", "Faille Blanche"],
  "entities": [
    {{"name": "Marche-Nuages", "type": "caste", "context": "se reunissent au Sanctuaire"}},
    {{"name": "Sanctuaire des Vents", "type": "place", "context": "lieu de reunion"}},
    {{"name": "Conseil des Souffles", "type": "institution", "context": "decide l'envoi"}},
    {{"name": "Porteurs d'Ecume", "type": "person", "context": "envoyes vers la Faille"}},
    {{"name": "Faille Blanche", "type": "place", "context": "destination"}},
    {{"name": "Pierres-Souffle", "type": "technology", "context": "emportees pour le voyage"}},
    {{"name": "Loi des Trois Ciels", "type": "belief", "context": "interdit le retour"}},
    {{"name": "Convergence", "type": "event", "context": "moment attendu pour le retour"}}
  ]
}}

NOTE : "bois" n'est PAS extrait (mot generique). "Marche-Nuages" EST extrait (nom invente avec tiret). 8 entites pour 4 phrases -- sois aussi exhaustif.

=== MAINTENANT, EXTRAIS LES ENTITES DU TEXTE SUIVANT ===

Texte :
{text}

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V11_ENTITY_PROMPT = """Tu recois un extrait d'un jeu de role civilisationnel. Les noms sont INVENTES par les joueurs. Ton travail : trouver TOUS les noms inventes.

=== IMPORTANT : COMMENT DETECTER UN NOM INVENTE ===

Un nom invente se reconnait parce qu'il ne designe PAS un objet du quotidien. C'est un terme propre au monde du jeu : une caste, un groupe, une institution, un lieu, une technologie, une croyance, un evenement, une civilisation, une creature.

Indices :
- Tirets dans un nom (X-Y) = TRES PROBABLEMENT une entite
- "Enfants du/des X", "Caste de X", "Cercle des X", "Maison des X" = entite
- Majuscule inhabituelle sur un mot ordinaire = probablement une entite (nom de lieu, technologie...)
- Nom de peuple, nation, civilisation etrangere = entite

=== CRITICAL : EXTRAIS TOUT, MEME EN CAS DE DOUTE ===

Si tu hesites entre "c'est un mot generique" et "c'est un nom invente pour le jeu" : EXTRAIS-LE.
Le seul cas ou tu n'extrais PAS : les mots vraiment banals (homme, eau, pierre, village, riviere) et les pronoms.

=== METHODE ===

Relis le texte PHRASE PAR PHRASE. Pour chaque phrase, note TOUS les noms inventes. Ne saute aucune phrase.

Texte :
{text}

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V11_HEAVY = ExtractionVersion(
    name="v11-heavy",
    description="Prompt lourd agnostique -- zero exemples specifiques, fake civ demo, marqueurs IMPORTANT/CRITICAL",
    temperature=0.0,
    system_prompt=_V11_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V11_SYSTEM_QWEN,
        "llama": _V11_SYSTEM_LLAMA,
    },
    facts_prompt=_V11_FACTS_PROMPT,
    entity_prompt=_V11_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v12-think: v11 base + thinking tree dans le user prompt
# Le LLM doit d'abord lister TOUS les candidats, puis decider pour chacun
# Raisonnement force dans l'output JSON via champ "keep" et "reason"
# num_predict augmente a 6000 pour le raisonnement
# ---------------------------------------------------------------------------

_V12_SYSTEM_QWEN = """Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. Tu dois les detecter dans le texte.

/no_think
Reponds UNIQUEMENT en JSON valide."""

_V12_SYSTEM_LLAMA = """Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. Tu dois les detecter dans le texte.

Reponds UNIQUEMENT en JSON valide."""

_V12_FACTS_PROMPT = """Tu recois un extrait d'un jeu de role civilisationnel. Les joueurs INVENTENT des noms pour tout : castes, institutions, lieux, technologies, croyances, creatures, evenements. Ces noms N'EXISTENT PAS dans le monde reel.

=== CRITICAL : METHODE EN DEUX ETAPES ===

ETAPE 1 — CANDIDATS : Lis le texte PHRASE PAR PHRASE. Note CHAQUE mot ou groupe de mots qui POURRAIT etre un nom invente. Sois TRES genereux. Inclus :
- Tout nom avec tiret (X-Y, X-des-Y)
- Tout nom avec majuscule inhabituelle
- Tout groupe "Enfants du/des X", "Caste de X", "Cercle des X", "Maison des X", "Loi du/de X"
- Tout nom de groupe, faction, peuple, caste
- Tout objet ou technique qui semble specifique au jeu
- Tout lieu qui n'est pas juste "riviere" ou "montagne"
- Tout rituel, loi, croyance nommee
- Tout evenement historique du jeu

ETAPE 2 — DECISION : Pour chaque candidat, pose-toi UNE question :
"Est-ce un nom INVENTE pour ce jeu, ou un mot BANAL du francais courant ?"
- "Cercle des Sages" → invente (institution du jeu) → GARDER
- "riviere" → banal → REJETER
- "Sans-ciels" → invente (nom avec tiret, caste) → GARDER
- "homme" → banal → REJETER
- "Argile Vivante" → invente (majuscule inhabituelle sur "vivante", technologie) → GARDER
- "maison" → banal → REJETER
- "Loi du Sang" → invente (loi du jeu) → GARDER
- "outils" → banal → REJETER

=== IMPORTANT : INDICES QU'UN NOM EST INVENTE ===

- Tiret dans le nom → PROBABLEMENT invente (Ailes-Grises, Passes-bien, Sans-ciels)
- Majuscule sur un mot qui n'en a normalement pas → PROBABLEMENT invente
- Combinaison de mots ordinaires formant un nom propre → invente (Lait de Pierre, Argile Vivante)
- Nom de groupe/caste/faction → invente meme si les mots sont ordinaires
- "les X" ou "des X" utilise comme nom de peuple/caste → invente

=== IMPORTANT : CE QUI N'EST JAMAIS UNE ENTITE ===

- Mots isoles banals : homme, femme, enfant, riviere, montagne, village, maison, outil, eau, bois, pierre, foyer, vallee, oiseaux, poissons
- Pronoms : il, elle, lui, eux, nous, toi, on
- "Chef du X" → extrais "X" (l'institution), PAS "Chef du X"
- Descriptions generiques : "outils tranchants", "huttes chaudes", "bete sacree"

=== EXEMPLE (civilisation fictive) ===

Texte : "Les Marche-Nuages et les Fils-du-Givre se reunissent au Sanctuaire des Vents. Le chef du Conseil des Souffles annonce la Loi des Trois Ciels. Les hommes emportent des Pierres-Souffle et du bois vers la Faille Blanche pour la prochaine Convergence."

Raisonnement :
- "Marche-Nuages" : tiret + nom de groupe → GARDER
- "Fils-du-Givre" : tiret + nom de groupe → GARDER
- "Sanctuaire des Vents" : lieu specifique au jeu → GARDER
- "chef du Conseil des Souffles" : titre → extraire "Conseil des Souffles" → GARDER
- "Loi des Trois Ciels" : loi du jeu → GARDER
- "hommes" : mot banal → REJETER
- "Pierres-Souffle" : tiret + technologie → GARDER
- "bois" : mot banal → REJETER
- "Faille Blanche" : lieu specifique → GARDER
- "Convergence" : evenement du jeu → GARDER

JSON :
{{
  "technologies": ["Pierres-Souffle"],
  "resources": [],
  "beliefs": ["Loi des Trois Ciels"],
  "geography": ["Sanctuaire des Vents", "Faille Blanche"],
  "entities": [
    {{"name": "Marche-Nuages", "type": "caste", "context": "se reunissent"}},
    {{"name": "Fils-du-Givre", "type": "caste", "context": "se reunissent"}},
    {{"name": "Sanctuaire des Vents", "type": "place", "context": "lieu de reunion"}},
    {{"name": "Conseil des Souffles", "type": "institution", "context": "annonce la loi"}},
    {{"name": "Loi des Trois Ciels", "type": "belief", "context": "annoncee par le Conseil"}},
    {{"name": "Pierres-Souffle", "type": "technology", "context": "emportees"}},
    {{"name": "Faille Blanche", "type": "place", "context": "destination"}},
    {{"name": "Convergence", "type": "event", "context": "prochaine occurrence attendue"}}
  ]
}}

NOTE : 8 entites pour 3 phrases. "hommes" et "bois" REJETES. "chef du Conseil des Souffles" → "Conseil des Souffles". Sois AUSSI exhaustif.

=== MAINTENANT, EXTRAIS LES ENTITES DU TEXTE SUIVANT ===

Texte :
{text}

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V12_ENTITY_PROMPT = """Tu recois un extrait d'un jeu de role civilisationnel. Les noms sont INVENTES par les joueurs.

=== CRITICAL : METHODE ===

Pour CHAQUE phrase du texte :
1. Liste tous les candidats possibles (tout ce qui pourrait etre un nom invente)
2. Pour chaque candidat : "nom invente ou mot banal ?" → si invente, EXTRAIS

=== IMPORTANT : DETECTER LES NOMS INVENTES ===

Cherche PARTICULIEREMENT :
- Noms avec TIRETS (X-Y) : presque TOUJOURS une entite (caste, personne, lieu)
- "Enfants du/des X", "Fils de/du X" : castes ou groupes
- "Cercle des X", "Maison des X", "Tribunal des X" : institutions
- "Loi du/de X", "Rituel du/de X" : croyances
- Mots ordinaires avec majuscule inhabituelle : technologies, lieux
- Noms de peuples, civilisations etrangeres

EN CAS DE DOUTE → EXTRAIS. Il vaut mieux un faux positif qu'un faux negatif.

Texte :
{text}

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V12_THINK = ExtractionVersion(
    name="v12-think",
    description="v11 + thinking tree -- candidats puis decision, raisonnement explicite dans l'exemple",
    temperature=0.0,
    num_predict=6000,  # plus de budget pour le raisonnement
    system_prompt=_V12_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V12_SYSTEM_QWEN,
        "llama": _V12_SYSTEM_LLAMA,
    },
    facts_prompt=_V12_FACTS_PROMPT,
    entity_prompt=_V12_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v13-validate: v11 extraction + passe de validation LLM post-extraction
# Le LLM recoit la liste brute d'entites + le texte original, et pour chacune
# repond a une checklist : apparait dans le texte ? nom invente ou generique ?
# titre ("Chef du X") ? → garde ou rejette
# 1 appel LLM supplementaire apres les 2 appels d'extraction
# ---------------------------------------------------------------------------

_V13_VALIDATE_SYSTEM_QWEN = """Tu es un validateur d'entites pour un jeu de role civilisationnel. On te donne une liste d'entites extraites d'un texte. Tu dois FILTRER cette liste.

/no_think
Reponds UNIQUEMENT en JSON valide."""

_V13_VALIDATE_SYSTEM_LLAMA = """Tu es un validateur d'entites pour un jeu de role civilisationnel. On te donne une liste d'entites extraites d'un texte. Tu dois FILTRER cette liste.

Reponds UNIQUEMENT en JSON valide."""

_V13_VALIDATE_PROMPT = """Voici des entites extraites d'un jeu de role civilisationnel. Certaines sont de VRAIES entites du jeu, d'autres sont du BRUIT (mots generiques). FILTRE la liste.

ENTITES A VALIDER :
{entities}

REJETER si :
- Mot banal francais utilise seul : maison, foyer, vallee, montagne, riviere, outils, briques, oiseaux, village, eau, bois, pierre, entree
- Titre + entite : "Chef du Cercle des Sages" → REJETER (garder "Cercle des Sages")
- Description generique : "outils tranchants", "bete sacree", "sagesse des sommets", "oiseaux qui comprennent"
- ATTENTION : "Maison des Decouvertes" = GARDER (nom compose = entite). "Maison" seul = REJETER.

GARDER si :
- Nom avec tiret (Sans-ciels, Ailes-Grises) = TOUJOURS garder
- Nom compose specifique (Maison des Decouvertes, Loi du Sang) = garder
- Nom de caste, institution, technologie, lieu, croyance, creature, civilisation = garder
- En cas de doute = GARDER

Retourne les noms a garder. JSON :
{{"keep": ["nom1", "nom2", "nom3"]}}"""

V13_VALIDATE = ExtractionVersion(
    name="v13-validate",
    description="v11 extraction + passe de validation LLM post-extraction (checklist 4 questions)",
    temperature=0.0,
    seed=42,
    system_prompt=_V11_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V11_SYSTEM_QWEN,
        "llama": _V11_SYSTEM_LLAMA,
    },
    facts_prompt=_V11_FACTS_PROMPT,
    entity_prompt=_V11_ENTITY_PROMPT,
    validate_prompt=_V13_VALIDATE_PROMPT,
    validate_system_prompt=_V13_VALIDATE_SYSTEM_LLAMA,
    validate_system_prompt_by_model={
        "qwen3": _V13_VALIDATE_SYSTEM_QWEN,
        "llama": _V13_VALIDATE_SYSTEM_LLAMA,
    },
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v13.1-validate: same extraction as v13, heavier validation prompt
# Targets the 5 remaining FP patterns with explicit examples
# ---------------------------------------------------------------------------

_V13_1_VALIDATE_PROMPT = """Voici des entites extraites d'un jeu de role civilisationnel. FILTRE cette liste. Sois STRICT.

ENTITES A VALIDER :
{entities}

=== CRITICAL : REJETER ces patterns ===

1. MOT BANAL SEUL : un seul mot du dictionnaire francais = REJETER
   REJETER : maison, foyer, vallee, montagne, riviere, outils, briques, village, eau, bois, pierre, entree, oiseaux, sculptures, fibres, resines, services, offrandes, ornements, montagnes
   GARDER : "Maison des Decouvertes" (nom compose = entite)

2. TITRE + ENTITE : "Chef du X", "Leader des X" = REJETER
   REJETER : "Chef du Cercle des Sages", "Chef de la Maison"
   L'entite X est deja dans la liste, pas besoin du titre.

3. DESCRIPTION GENERIQUE : groupe de mots qui DECRIT au lieu de NOMMER = REJETER
   REJETER : "outils tranchants", "bete sacree", "huttes chaudes", "rhombes geants"
   REJETER : "oiseaux qui comprennent", "recipients qui portent l'eau", "argile qui vit"
   REJETER : "assemblages d'argile et d'os", "forgeron d'os"
   Ces mots DECRIVENT quelque chose, ce ne sont PAS des noms inventes.

4. PARAPHRASE / INVENTION : un nom qui SEMBLE invente mais qui est en fait une description poetique = REJETER
   REJETER : "Sagesse des sommets", "Foyer eternel", "Oracle lointain des sommets", "Arbre de toutes les possibilites", "Triple revelation", "Sagesse du vivant"
   TEST : Est-ce que ca sonne comme un TITRE DE CHAPITRE ou une METAPHORE ? Si oui = REJETER.
   COMPARER : "Cercle des Sages" = nom d'INSTITUTION (structure politique) = GARDER.
             "Sagesse des sommets" = METAPHORE (concept vague) = REJETER.

5. DOUBLON AVEC MAUVAIS TYPE : si la meme entite apparait 2x avec des types differents, garder UNE seule occurrence (le type le plus logique).

=== IMPORTANT : GARDER ces patterns ===

- Nom avec TIRET : TOUJOURS garder (Sans-ciels, Ailes-Grises, Passes-bien, Regards-Libres)
- Nom d'institution compose : "Cercle des X", "Tribunal des X", "Assemblee des X", "Maison des X" = garder
- Nom de technologie specifique : "Argile vivante", "Lait de Pierre", "Rhombes" = garder
- Nom de lieu specifique : "Arene", "Confluence", "Zone chaude" = garder
- Nom de loi/croyance : "Loi du Sang", "Culte des Ancetres" = garder
- En cas de DOUTE : garder

Retourne les noms a garder. JSON :
{{"keep": ["nom1", "nom2", "nom3"]}}"""

V13_1_VALIDATE = ExtractionVersion(
    name="v13.1-validate",
    description="v13 + validation heavy -- cible les 5 FP restants avec exemples explicites",
    temperature=0.0,
    seed=42,
    system_prompt=_V11_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V11_SYSTEM_QWEN,
        "llama": _V11_SYSTEM_LLAMA,
    },
    facts_prompt=_V11_FACTS_PROMPT,
    entity_prompt=_V11_ENTITY_PROMPT,
    validate_prompt=_V13_1_VALIDATE_PROMPT,
    validate_system_prompt=_V13_VALIDATE_SYSTEM_LLAMA,
    validate_system_prompt_by_model={
        "qwen3": _V13_VALIDATE_SYSTEM_QWEN,
        "llama": _V13_VALIDATE_SYSTEM_LLAMA,
    },
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v13.2-validate: v13.1 mais validation moins aggressive
# v13.1 tuait des TP (Proclamateurs, Regards-Libres, Arbitre des Esprits)
# Cause : les regles REJETER etaient trop fortes vs le "en cas de doute GARDER"
# Fix : insister BEAUCOUP plus sur le "GARDER en cas de doute", reduire les regles REJETER
# ---------------------------------------------------------------------------

_V13_2_VALIDATE_PROMPT = """Voici des entites extraites d'un jeu de role civilisationnel. Certaines sont du BRUIT. Filtre-les.

ENTITES :
{entities}

=== CRITICAL : REGLE NUMERO 1 — EN CAS DE DOUTE, GARDER ===

C'est la regle la plus importante. Si tu hesites meme une SECONDE, GARDE l'entite. Un faux positif n'est pas grave. Un faux negatif est CATASTROPHIQUE.

=== REJETER UNIQUEMENT ces 3 cas evidents ===

1. MOT BANAL SEUL (1 seul mot du dictionnaire) : maison, foyer, vallee, montagne, riviere, outils, village, eau, bois, pierre, entree
   MAIS "Maison des Decouvertes" = GARDER (c'est un nom compose)

2. DESCRIPTION / METAPHORE evidente : "oiseaux qui comprennent", "sagesse des sommets", "arbre de toutes les possibilites", "oracle lointain des sommets", "foyer eternel", "sagesse du vivant"
   TEST : ca contient "qui" + verbe ? Ou ca sonne comme une phrase poetique ? = REJETER

3. DOUBLON exact : meme nom apparait 2x avec des types differents = garder UNE seule fois

=== IMPORTANT : NE JAMAIS REJETER ces patterns ===

- Nom avec TIRET : TOUJOURS garder (Sans-ciels, Ailes-Grises, Passes-bien, Regards-Libres)
- Nom de GROUPE de personnes : TOUJOURS garder (Proclamateurs, Faucons Chasseurs, Traqueurs, Porteurs de Flamme)
- Nom d'INSTITUTION : TOUJOURS garder (Cercle des Sages, Arbitre des Esprits, Tribunal des Moeurs)
- Nom de CREATURE : TOUJOURS garder (Regards-Libres, Nantons)
- Tout nom compose de 2+ mots : presumer que c'est une entite sauf si c'est clairement une metaphore

Retourne les noms a garder. JSON :
{{"keep": ["nom1", "nom2", "nom3"]}}"""

V13_2_VALIDATE = ExtractionVersion(
    name="v13.2-validate",
    description="v13.1 + validation moins aggressive -- insiste sur GARDER en cas de doute",
    temperature=0.0,
    seed=42,
    system_prompt=_V11_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V11_SYSTEM_QWEN,
        "llama": _V11_SYSTEM_LLAMA,
    },
    facts_prompt=_V11_FACTS_PROMPT,
    entity_prompt=_V11_ENTITY_PROMPT,
    validate_prompt=_V13_2_VALIDATE_PROMPT,
    validate_system_prompt=_V13_VALIDATE_SYSTEM_LLAMA,
    validate_system_prompt_by_model={
        "qwen3": _V13_VALIDATE_SYSTEM_QWEN,
        "llama": _V13_VALIDATE_SYSTEM_LLAMA,
    },
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v14-certainty: inline certainty score replaces validation pass
# The LLM self-assesses each entity with a certainty score in the SAME call.
# No separate validation pass needed — filter by threshold in code.
# Scale is configurable: (1,3) for small models, (1,10) for larger ones.
# ---------------------------------------------------------------------------

# Helper to build scale-aware prompt fragments
# All helpers are generic — they adapt to any (min, max) scale.

def _certainty_scale_text(scale: tuple = (1, 3)) -> str:
    """Generate prompt text describing the certainty scale."""
    lo, hi = scale
    if hi == 3:
        return (
            f"\"certainty\": {lo} a {hi}\n"
            f"  - {lo} = \"peut-etre, j'hesite\" (mot generique, nom ambigu, pourrait ne PAS etre une entite inventee)\n"
            f"  - 2 = \"probable\" (ressemble a un terme invente mais pas 100% sur)\n"
            f"  - {hi} = \"certain\" (nom propre clairement invente pour le jeu, sans ambiguite)"
        )
    elif hi == 5:
        return (
            f"\"certainty\": {lo} a {hi}\n"
            f"  - {lo} = tres incertain (mot generique, nom ambigu, probablement PAS une entite inventee)\n"
            f"  - 2 = incertain (pourrait etre un terme invente, pas clair)\n"
            f"  - 3 = neutre (possible entite, pas assez d'indices)\n"
            f"  - 4 = probable (ressemble fortement a un nom invente)\n"
            f"  - {hi} = certain (nom propre clairement invente pour le jeu, sans ambiguite)"
        )
    elif hi == 10:
        return (
            f"\"certainty\": {lo} a {hi}\n"
            f"  - {lo}-3 = tres incertain (mot generique, nom ambigu, probablement PAS une entite inventee)\n"
            f"  - 4-6 = incertain (pourrait etre un terme invente, pas clair)\n"
            f"  - 7-8 = probable (ressemble fortement a un nom invente)\n"
            f"  - 9-{hi} = certain (nom propre clairement invente pour le jeu)"
        )
    else:  # 1-100 (percentage) scale
        return (
            f"\"certainty\": {lo} a {hi} (pourcentage de confiance)\n"
            f"  - {lo}-20 = tres incertain (mot generique, nom ambigu, probablement PAS une entite inventee)\n"
            f"  - 21-50 = incertain (pourrait etre un terme invente, pas clair)\n"
            f"  - 51-80 = probable (ressemble fortement a un nom invente)\n"
            f"  - 81-{hi} = certain (nom propre clairement invente pour le jeu, sans ambiguite)"
        )


def _certainty_examples(scale: tuple = (1, 3)) -> str:
    """Generate certainty examples adapted to the scale."""
    hi = scale[1]
    if hi == 3:
        return (
            "Exemples de certitude :\n"
            "- certainty 3 : \"Gouffre Humide\", \"Ailes-Grises\", \"Argile vivante\" -> noms inventes evidents\n"
            "- certainty 2 : \"Premiers Ancetres\", \"Peuple de la vallee\" -> pourrait etre specifique au jeu\n"
            "- certainty 1 : \"montagne\", \"creature\", \"sculpteurs\" -> mots generiques francais"
        )
    elif hi == 5:
        return (
            "Exemples de certitude :\n"
            "- certainty 5 : \"Gouffre Humide\", \"Ailes-Grises\", \"Argile vivante\" -> noms inventes evidents\n"
            "- certainty 4 : \"Premiers Ancetres\", \"Peuple de la vallee\" -> probablement specifique au jeu\n"
            "- certainty 3 : \"Sanctuaire\", \"Conseil\" -> mot avec majuscule, ambigu\n"
            "- certainty 1-2 : \"montagne\", \"creature\", \"sculpteurs\" -> mots generiques francais"
        )
    elif hi == 10:
        return (
            "Exemples de certitude :\n"
            "- certainty 9-10 : \"Gouffre Humide\", \"Ailes-Grises\", \"Argile vivante\" -> noms inventes evidents\n"
            "- certainty 7-8 : \"Premiers Ancetres\", \"Peuple de la vallee\" -> probablement specifique au jeu\n"
            "- certainty 4-6 : \"Sanctuaire\", \"Conseil\" -> mot avec majuscule, ambigu\n"
            "- certainty 1-3 : \"montagne\", \"creature\", \"sculpteurs\" -> mots generiques francais"
        )
    else:  # percentage
        return (
            "Exemples de certitude (en pourcentage) :\n"
            "- certainty 90-100 : \"Gouffre Humide\", \"Ailes-Grises\", \"Argile vivante\" -> noms inventes evidents\n"
            "- certainty 60-80 : \"Premiers Ancetres\", \"Peuple de la vallee\" -> probablement specifique au jeu\n"
            "- certainty 30-50 : \"Sanctuaire\", \"Conseil\" -> mot avec majuscule, ambigu\n"
            "- certainty 1-20 : \"montagne\", \"creature\", \"sculpteurs\" -> mots generiques francais"
        )


def _certainty_json_example(scale: tuple = (1, 3)) -> str:
    """Generate JSON example with certainty scores adapted to the scale."""
    hi = scale[1]
    # Map: high confidence, medium confidence, low confidence scores per scale
    if hi == 3:
        top, mid, lo = 3, 2, 1
    elif hi == 5:
        top, mid, lo = 5, 3, 1
    elif hi == 10:
        top, mid, lo = 10, 7, 3
    else:  # percentage
        top, mid, lo = 95, 65, 15
    return (
        '{{\n'
        '  "technologies": ["Pierres-Souffle"],\n'
        '  "resources": [],\n'
        '  "beliefs": ["Loi des Trois Ciels"],\n'
        '  "geography": ["Sanctuaire des Vents", "Faille Blanche"],\n'
        '  "entities": [\n'
        f'    {{{{"name": "Marche-Nuages", "type": "caste", "context": "se reunissent", "certainty": {top}}}}},\n'
        f'    {{{{"name": "Sanctuaire des Vents", "type": "place", "context": "lieu de reunion", "certainty": {top}}}}},\n'
        f'    {{{{"name": "Conseil des Souffles", "type": "institution", "context": "decide l\'envoi", "certainty": {top}}}}},\n'
        f'    {{{{"name": "Porteurs d\'Ecume", "type": "person", "context": "envoyes vers la Faille", "certainty": {top}}}}},\n'
        f'    {{{{"name": "Convergence", "type": "event", "context": "prochaine occurrence", "certainty": {mid}}}}},\n'
        f'    {{{{"name": "hommes", "type": "person", "context": "mot generique", "certainty": {lo}}}}}\n'
        '  ]\n'
        '}}'
    )


def _build_v14_facts_prompt(scale: tuple = (1, 3)) -> str:
    """Build the v14 facts+entities prompt with certainty score instructions."""
    return (
        "Tu recois un extrait d'un jeu de role civilisationnel. Les joueurs INVENTENT des noms pour tout : "
        "leurs castes, institutions, lieux, technologies, croyances, creatures, evenements. "
        "Ces noms N'EXISTENT PAS dans le monde reel. Ton travail est de les trouver TOUS.\n\n"
        "=== IMPORTANT : QU'EST-CE QU'UNE ENTITE DE JDR ? ===\n\n"
        "Une entite de JDR est un nom INVENTE par le joueur ou le MJ pour designer quelque chose dans le monde du jeu.\n\n"
        "Indices pour reconnaitre une entite de JDR :\n"
        "- Un nom avec des majuscules qui ne designe PAS un objet du quotidien\n"
        "- Un nom compose avec des tirets (X-Y) : TRES PROBABLEMENT une entite\n"
        "- \"Enfants du/des X\", \"Cercle des X\", \"Maison des X\" : entite\n"
        "- Un mot ordinaire utilise comme nom propre dans le contexte du jeu\n"
        "- Un nom de civilisation, peuple, ou nation etrangere\n\n"
        "=== CRITICAL : CE QUI N'EST PAS UNE ENTITE ===\n\n"
        "- Mots generiques du francais courant : homme, femme, enfant, riviere, montagne, village, maison, outil, eau, bois, pierre\n"
        "- Pronoms : il, elle, lui, eux, nous, on\n"
        "- Titres suivis d'un nom (\"Chef du X\") : extrais X, pas le titre\n"
        "- Descriptions : \"les outils tranchants\" = description, pas nom invente\n\n"
        "=== NOUVEAU : SCORE DE CERTITUDE ===\n\n"
        "Pour CHAQUE entite, ajoute un champ " + _certainty_scale_text(scale) + "\n\n"
        "" + _certainty_examples(scale) + "\n\n"
        "IMPORTANT : donne un score HONNETE. Si tu hesites, mets un score BAS plutot que haut. "
        "Le filtrage se fait cote code — mieux vaut extraire avec un score bas que ne pas extraire du tout.\n\n"
        "=== METHODE D'EXTRACTION ===\n\n"
        "Lis le texte phrase par phrase. Pour chaque phrase, cherche :\n"
        "1. Noms avec tirets ou majuscules inhabituelles\n"
        "2. Groupes nominaux = noms propres\n"
        "3. Castes, institutions, lieux, technologies, croyances, creatures, evenements, civilisations\n\n"
        "=== REGLE D'OR : COPIE MOT POUR MOT du texte. ZERO invention. ===\n\n"
        "=== EXEMPLE ===\n\n"
        "Texte : \"Les Marche-Nuages se reunissent au Sanctuaire des Vents. Le Conseil des Souffles decide "
        "d'envoyer les Porteurs d'Ecume vers la Faille Blanche. Ils emportent des Pierres-Souffle et du bois. "
        "La Loi des Trois Ciels interdit tout retour avant la prochaine Convergence. Les hommes preparent le voyage.\"\n\n"
        "Reponse :\n" + _certainty_json_example(scale) + "\n\n"
        # Match the lo/top values used in _certainty_json_example for consistency
        "NOTE : \"bois\" n'est PAS extrait (generique). \"hommes\" a certainty "
        + str({3: 1, 5: 1, 10: 3}.get(scale[1], 15))
        + " (generique). "
        "\"Marche-Nuages\" a certainty " + str(scale[1]) + " (nom invente evident). Sois AUSSI exhaustif.\n\n"
        "=== MAINTENANT, EXTRAIS LES ENTITES DU TEXTE SUIVANT ===\n\n"
        "Texte :\n{text}\n\n"
        "JSON UNIQUEMENT :\n"
        "{{\n"
        "  \"technologies\": [\"noms exacts du texte\"],\n"
        "  \"resources\": [\"noms exacts du texte\"],\n"
        "  \"beliefs\": [\"noms exacts du texte\"],\n"
        "  \"geography\": [\"noms exacts du texte\"],\n"
        "  \"entities\": [{{\"name\": \"Nom COPIE du texte\", \"type\": \"person|place|technology|institution|resource|creature|event|civilization|caste|belief\", \"context\": \"phrase courte\", \"certainty\": N}}]\n"
        "}}"
    )


def _build_v14_entity_prompt(scale: tuple = (1, 3)) -> str:
    """Build the v14 entity-only prompt with certainty score instructions."""
    return (
        "Tu recois un extrait d'un jeu de role civilisationnel. Les noms sont INVENTES par les joueurs. "
        "Ton travail : trouver TOUS les noms inventes.\n\n"
        "=== COMMENT DETECTER UN NOM INVENTE ===\n\n"
        "- Tirets dans un nom (X-Y) = TRES PROBABLEMENT une entite\n"
        "- \"Enfants du/des X\", \"Cercle des X\", \"Maison des X\" = entite\n"
        "- Majuscule inhabituelle = probablement entite\n"
        "- Nom de peuple, civilisation = entite\n\n"
        "=== SCORE DE CERTITUDE ===\n\n"
        "Pour CHAQUE entite, ajoute " + _certainty_scale_text(scale) + "\n\n"
        "" + _certainty_examples(scale) + "\n\n"
        "Score HONNETE. Si tu hesites, mets un score BAS. Mieux vaut extraire avec score bas que rater.\n\n"
        "=== EXTRAIS TOUT, MEME EN CAS DE DOUTE ===\n\n"
        "Relis phrase par phrase. Note TOUS les noms inventes avec leur certitude.\n\n"
        "Texte :\n{text}\n\n"
        "JSON :\n"
        "{{\"entities\": [{{\"name\": \"Nom COPIE du texte\", \"type\": \"person|place|technology|institution|resource|creature|event|civilization|caste|belief\", \"context\": \"phrase courte\", \"certainty\": N}}]}}\n\n"
        "Si aucune entite, retourne {{\"entities\": []}}."
    )


# ---------------------------------------------------------------------------
# Mistral Nemo-specific prompts for v14
# Nemo needs markdown structure (### headers), shorter examples, explicit JSON.
# No /no_think (Nemo doesn't have thinking mode), no === CRITICAL === blocks.
# French with accents (Nemo handles UTF-8 well, unlike qwen3 where we avoid them).
# ---------------------------------------------------------------------------

_V14_SYSTEM_NEMO = (
    "Tu es un assistant specialise dans l'extraction d'entites nommees "
    "a partir de textes de jeux de role civilisationnels.\n\n"
    "Tu reponds uniquement en JSON valide. Pas de texte avant ou apres le JSON."
)


# --- Nemo prompt builders ---
# Benchmarked findings (Mistral Nemo on OpenRouter, v14-certainty-10, turn 14):
#
# | Prompt style            | Scale | P     | R     | F1    | TP | FP | Notes                    |
# |-------------------------|-------|-------|-------|-------|----|----|--------------------------|
# | qwen3 prompts (before)  | 1-10  | 33.3% | 18.8% | 24.0% |  9 | 18 | Generic noise            |
# | checklist+example short | 1-10  | 66.7% | 20.8% | 31.7% | 10 |  5 | Good precision           |
# | checklist+example short | %     | 78.6% | 22.9% | 35.5% | 11 |  3 | BEST F1, best precision  |
# | checklist long+example  | 1-10  | 33.3% |  6.2% | 10.5% |  3 |  6 | Example copied as FP     |
# | no example              | 1-10  | 58.8% | 20.8% | 30.8% | 10 |  7 | Invents entities         |
# | no example              | %     | 62.5% | 20.8% | 31.2% | 10 |  6 | "Spirituels" returns     |
# | open/permissive         | %     | 47.4% | 18.8% | 26.9% |  9 | 10 | More FP, less TP         |
# | open/permissive         | 1-10  | 45.0% | 18.8% | 26.5% |  9 | 11 | Worst of both worlds     |
#
# Conclusions:
# - Short example (3 entities) is critical: teaches format without polluting
# - Strict exclusions help precision, opening them adds FP without recall gain
# - % scale produces slightly better results than 1-10 (but Nemo doesn't calibrate)
# - Recall is capped at ~22% regardless of prompt — model limitation
# - Best config: checklist + short example + % scale = F1=35.5%, P=78.6%


def _build_nemo_facts_prompt(scale: tuple = (1, 10)) -> str:
    """Build the Nemo facts+entities prompt. Scale-aware for % or 1-10."""
    hi = scale[1]
    if hi == 100:
        cert_line = "Le champ `certainty` va de 1 (tres incertain) a 100 (certain). Score honnete."
        ex_scores = (95, 95, 95)
    else:
        cert_line = "Le champ `certainty` va de 1 (tres incertain) a 10 (certain). Score honnete."
        ex_scores = (10, 10, 10)

    return (
        "### Tache\n"
        "Extrais toutes les entites nommees inventees par les joueurs dans ce texte de jeu de role.\n\n"
        "### Checklist — relis le texte pour CHAQUE categorie\n"
        "1. Castes/groupes sociaux (tirets, \"Enfants du/des X\", \"Caste de X\")\n"
        "2. Personnes/groupes nommes (tirets, titres de groupes)\n"
        "3. Institutions (\"Cercle des X\", \"Hall des X\", \"Maison des X\", \"Foyer du X\")\n"
        "4. Lieux (noms propres, \"Zone + adjectif\", \"Route-X\")\n"
        "5. Technologies/outils (tout objet nomme)\n"
        "6. Croyances/lois (\"Loi de X\", \"Rituel du X\")\n"
        "7. Evenements, civilisations, creatures\n\n"
        "### Exclusions\n"
        "Mots generiques (homme, femme, riviere, village, eau, bois, pierre), pronoms, descriptions.\n\n"
        "### Format de reponse OBLIGATOIRE\n"
        "Tu DOIS utiliser EXACTEMENT ce format JSON. Pas d'autre structure.\n\n"
        "```json\n"
        "{{\n"
        "  \"technologies\": [\"noms exacts\"],\n"
        "  \"resources\": [],\n"
        "  \"beliefs\": [\"noms exacts\"],\n"
        "  \"geography\": [\"noms exacts\"],\n"
        "  \"entities\": [\n"
        "    {{\"name\": \"Nom exact\", \"type\": \"caste|person|institution|place|technology"
        "|belief|event|civilization|creature|resource\", \"context\": \"phrase courte\", \"certainty\": N}}\n"
        "  ]\n"
        "}}\n"
        "```\n\n"
        f"{cert_line}\n\n"
        "### Exemple\n\n"
        "Texte : \"Les Marche-Nuages se reunissent au Sanctuaire des Vents. "
        "Le Conseil des Souffles decide d'envoyer les Porteurs d'Ecume vers la Faille Blanche.\"\n\n"
        "{{\n"
        "  \"technologies\": [],\n"
        "  \"resources\": [],\n"
        "  \"beliefs\": [],\n"
        "  \"geography\": [\"Sanctuaire des Vents\", \"Faille Blanche\"],\n"
        "  \"entities\": [\n"
        f"    {{{{\"name\": \"Marche-Nuages\", \"type\": \"caste\", \"context\": \"se reunissent\", \"certainty\": {ex_scores[0]}}}}},\n"
        f"    {{{{\"name\": \"Sanctuaire des Vents\", \"type\": \"place\", \"context\": \"lieu de reunion\", \"certainty\": {ex_scores[1]}}}}},\n"
        f"    {{{{\"name\": \"Conseil des Souffles\", \"type\": \"institution\", \"context\": \"decide l'envoi\", \"certainty\": {ex_scores[2]}}}}}\n"
        "  ]\n"
        "}}\n\n"
        "### Texte a analyser\n\n"
        "{text}\n\n"
        "Reponds avec le JSON ci-dessus, rien d'autre."
    )


def _build_nemo_entity_prompt(scale: tuple = (1, 10)) -> str:
    """Build the Nemo entity-only prompt. Scale-aware."""
    hi = scale[1]
    cert_range = "1 a 100 (%)" if hi == 100 else "1 a 10"
    return (
        "### Tache\n"
        "Trouve tous les noms inventes dans ce texte de jeu de role civilisationnel.\n\n"
        "### Checklist\n"
        "Castes, personnes, institutions, lieux, technologies, croyances, evenements, "
        "civilisations, creatures.\n\n"
        "### Format OBLIGATOIRE\n"
        "{{\"entities\": [{{\"name\": \"Nom exact\", \"type\": \"caste|person|institution|place"
        "|technology|belief|event|civilization|creature|resource\", \"context\": \"phrase courte\", "
        "\"certainty\": N}}]}}\n\n"
        f"certainty : {cert_range}. Sois exhaustif.\n\n"
        "### Texte\n"
        "{text}\n\n"
        "Reponds avec le JSON ci-dessus, rien d'autre."
    )


# Nemo prompts — percentage scale wins (F1=35.5% vs 31.7% on 1-10).
# Used by both v14-certainty-10 (via by_model override) and v14-nemo-pct.
# Note: Nemo doesn't actually calibrate (all scores 80-100%), but the %
# prompt produces better extraction quality than the 1-10 prompt.
_V14_FACTS_PROMPT_NEMO = _build_nemo_facts_prompt((1, 100))
_V14_ENTITY_PROMPT_NEMO = _build_nemo_entity_prompt((1, 100))

# Alias for explicit percentage version
_V14_FACTS_PROMPT_NEMO_PCT = _V14_FACTS_PROMPT_NEMO
_V14_ENTITY_PROMPT_NEMO_PCT = _V14_ENTITY_PROMPT_NEMO


# System prompts for v14
# Qwen3 needs /no_think on Ollama to disable thinking mode (saves num_predict budget).
# On OpenRouter it's stripped automatically (reasoning.effort:none handles it).
_V14_SYSTEM_QWEN = (
    "Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. "
    "Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. "
    "Tu dois les detecter dans le texte et evaluer ta certitude pour chacune.\n\n"
    "/no_think\n"
    "Reponds UNIQUEMENT en JSON valide."
)

_V14_SYSTEM_LLAMA = (
    "Tu es un extracteur d'entites nommees pour un jeu de role civilisationnel. "
    "Chaque civilisation invente ses propres noms. Tu ne les connais pas a l'avance. "
    "Tu dois les detecter dans le texte et evaluer ta certitude pour chacune.\n\n"
    "Reponds UNIQUEMENT en JSON valide."
)

# Default v14: scale 1-3, threshold 2 (conservative — filters "peut-etre" entities)
# num_predict=6000: certainty adds ~15 chars/entity, need more budget than v11's 4000
V14_CERTAINTY = ExtractionVersion(
    name="v14-certainty",
    description="v11 extraction + inline certainty score (1-3), no validation pass, threshold=2",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
    },
    facts_prompt=_build_v14_facts_prompt((1, 3)),
    entity_prompt=_build_v14_entity_prompt((1, 3)),
    certainty_scale=(1, 3),
    certainty_threshold=2,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# Variant: scale 1-5 for balanced granularity, threshold 3
V14_CERTAINTY_5 = ExtractionVersion(
    name="v14-certainty-5",
    description="v11 extraction + inline certainty score (1-5), no validation pass, threshold=3",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
    },
    facts_prompt=_build_v14_facts_prompt((1, 5)),
    entity_prompt=_build_v14_entity_prompt((1, 5)),
    certainty_scale=(1, 5),
    certainty_threshold=3,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# Variant: scale 1-100 (percentage), threshold 50
V14_CERTAINTY_PCT = ExtractionVersion(
    name="v14-certainty-pct",
    description="v11 extraction + inline certainty score (1-100%), no validation pass, threshold=50",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
    },
    facts_prompt=_build_v14_facts_prompt((1, 100)),
    entity_prompt=_build_v14_entity_prompt((1, 100)),
    certainty_scale=(1, 100),
    certainty_threshold=50,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# "Blind" variant: LLM scores freely, NO threshold — we sweep in post-processing.
# The prompt does NOT mention any threshold, just asks for honest confidence %.
V14_BLIND = ExtractionVersion(
    name="v14-blind",
    description="v11 extraction + inline certainty % (1-100), NO threshold — sweep in benchmark",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
    },
    facts_prompt=_build_v14_facts_prompt((1, 100)),
    entity_prompt=_build_v14_entity_prompt((1, 100)),
    certainty_scale=(1, 100),
    certainty_threshold=0,  # NO filtering — benchmark will sweep thresholds
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# "Blind" variant on scale 1-10: sweep thresholds, Nemo-specific prompts included.
V14_BLIND_10 = ExtractionVersion(
    name="v14-blind-10",
    description="v14 certainty (1-10), NO threshold — sweep in benchmark. Nemo prompts included.",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
        "mistral": _V14_SYSTEM_NEMO,
    },
    facts_prompt=_build_v14_facts_prompt((1, 10)),
    facts_prompt_by_model={
        "mistral": _V14_FACTS_PROMPT_NEMO,
    },
    entity_prompt=_build_v14_entity_prompt((1, 10)),
    entity_prompt_by_model={
        "mistral": _V14_ENTITY_PROMPT_NEMO,
    },
    certainty_scale=(1, 10),
    certainty_threshold=0,  # NO filtering — benchmark will sweep thresholds
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# Variant: scale 1-10 for testing granularity, threshold 5
# Includes Mistral Nemo-specific prompts via *_by_model overrides.
# Prefix "mistral" matches "mistral-nemo:latest" via _model_matches_prefix.
V14_CERTAINTY_10 = ExtractionVersion(
    name="v14-certainty-10",
    description="v11 extraction + inline certainty score (1-10), no validation pass, threshold=5",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
        "mistral": _V14_SYSTEM_NEMO,
    },
    facts_prompt=_build_v14_facts_prompt((1, 10)),
    facts_prompt_by_model={
        "mistral": _V14_FACTS_PROMPT_NEMO,
    },
    entity_prompt=_build_v14_entity_prompt((1, 10)),
    entity_prompt_by_model={
        "mistral": _V14_ENTITY_PROMPT_NEMO,
    },
    certainty_scale=(1, 10),
    certainty_threshold=5,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# Nemo percentage variant: scale 1-100%, no threshold, sweep in benchmark.
# Tests whether Nemo gives more granular scores on a % scale.
V14_NEMO_PCT = ExtractionVersion(
    name="v14-nemo-pct",
    description="v14 certainty % (1-100) with Nemo-specific prompts, NO threshold — sweep",
    temperature=0.0,
    num_predict=6000,
    seed=42,
    system_prompt=_V14_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V14_SYSTEM_QWEN,
        "llama": _V14_SYSTEM_LLAMA,
        "mistral": _V14_SYSTEM_NEMO,
    },
    facts_prompt=_build_v14_facts_prompt((1, 100)),
    facts_prompt_by_model={
        "mistral": _V14_FACTS_PROMPT_NEMO_PCT,
    },
    entity_prompt=_build_v14_entity_prompt((1, 100)),
    entity_prompt_by_model={
        "mistral": _V14_ENTITY_PROMPT_NEMO_PCT,
    },
    certainty_scale=(1, 100),
    certainty_threshold=0,  # sweep in benchmark
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v15-recall-baseline: v1 prompt (best precision) + paragraph chunking
# Hypothesis: v1's low recall is a coverage problem, not a prompt problem.
# Chunking ensures the LLM sees the full text instead of truncating at num_ctx.
# ---------------------------------------------------------------------------

V15_RECALL_BASELINE = ExtractionVersion(
    name="v15-recall-baseline",
    description="v1 prompt + paragraph chunking (coverage fix)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v15.1-sysnoise: v15 + system prompt anti-bruit
# Target: reduce FP from generic words, singular variants, descriptions.
# Keep the v1 user prompt intact — only add a lightweight system prompt.
# ---------------------------------------------------------------------------

_V15_1_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, assemblees, rumeur, autre, exil, guerre, combat, collaboration.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

V15_1_SYSNOISE = ExtractionVersion(
    name="v15.1-sysnoise",
    description="v15 + system prompt anti-bruit (generiques, variantes, phrases)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v15.2-negex: v15 + negative examples dans le user prompt
# Instead of a system prompt, embed anti-noise rules directly in user prompt
# with concrete negative examples from observed FP.
# ---------------------------------------------------------------------------

_V15_2_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

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
NON : pronoms (lui, eux, toi, nous), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere), phrases longues.
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : descriptions avec articles ("Un Faucon Chasseur veteran", "Une Grande Foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete, avec le bon pluriel/tiret)."""

_V15_2_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Rhombes", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang".
NON : mots communs, mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre).
NON : descriptions ("Un Faucon Chasseur veteran", "Action libre - L'epave", "Mars Attack").
NON : variantes — UNE forme par entite.
Si rien, retourne {{"entities": []}}."""

V15_2_NEGEX = ExtractionVersion(
    name="v15.2-negex",
    description="v15 + negative examples in user prompt (anti-noise)",
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v15.3-combo: v15.1 system prompt + v15.2 negative examples
# Belt and suspenders: both system rules AND user prompt negatives.
# ---------------------------------------------------------------------------

V15_3_COMBO = ExtractionVersion(
    name="v15.3-combo",
    description="v15 + system anti-bruit + negex user prompt (full combo)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v15.4-temp005: v15 base with temperature 0.05 (more conservative)
# Hypothesis: lower temp = fewer hallucinated entities = less FP.
# ---------------------------------------------------------------------------

V15_4_TEMP005 = ExtractionVersion(
    name="v15.4-temp005",
    description="v15 + temperature 0.05 (more conservative output)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    temperature=0.05,
)

# ---------------------------------------------------------------------------
# v15.3 micro-variations — single variable changes from the best config
# Goal: push F1 above 67.2% by targeting the 19 remaining FP.
# All use the same system+negex combo and chunking as v15.3.
# ---------------------------------------------------------------------------

# v15.3.1: temperature=0 — fully deterministic, may reduce variant FP
V15_3_1_TEMP0 = ExtractionVersion(
    name="v15.3.1-temp0",
    description="v15.3 + temperature=0 (deterministic)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    temperature=0.0,
)

# v15.3.2: smaller chunks (600w) — more focused per call, less context confusion
V15_3_2_CHUNK600 = ExtractionVersion(
    name="v15.3.2-chunk600",
    description="v15.3 + max_chunk_words=600 (tighter chunks)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=600,
)

# v15.3.3: larger chunks (1200w) — more context per call, LLM sees more entities together
# Hypothesis: seeing "Faucons Chasseurs" and "Faucon Chasseur" in the same chunk
# helps the LLM deduplicate them itself.
V15_3_3_CHUNK1200 = ExtractionVersion(
    name="v15.3.3-chunk1200",
    description="v15.3 + max_chunk_words=1200 (wider chunks)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=1200,
)

# v15.3.4: tighter NON list — adds the specific FP generics still leaking through
_V15_3_4_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type", "Grande Foret".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

V15_3_4_TIGHTNON = ExtractionVersion(
    name="v15.3.4-tightnon",
    description="v15.3 + expanded NON list targeting remaining FP generics",
    system_prompt=_V15_3_4_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v16-bigctx: v1 prompt + 16K context window (no chunking)
# Alternative coverage fix: instead of chunking, expand the context window
# so the full 7.6K-word turn fits in a single call.
# Risk: "lost in the middle" — LLM may forget entities from the center.
# ---------------------------------------------------------------------------

V16_BIGCTX = ExtractionVersion(
    name="v16-bigctx",
    description="v1 prompt + num_ctx=16384 (full text in one call)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=False,
    num_ctx=16384,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_VERSIONS: dict[str, ExtractionVersion] = {
    "v1-baseline": V1_BASELINE,
    "v2-fewshot": V2_FEWSHOT,
    "v3-recall": V3_RECALL,
    "v4-strict-recall": V4_STRICT_RECALL,
    "v5-schema": V5_SCHEMA,
    "v6-combo": V6_COMBO,
    "v8-negshot": V8_NEGSHOT,
    "v9-neginuser": V9_NEGINUSER,
    "v10-mark": V10_MARK,
    "v11-heavy": V11_HEAVY,
    "v12-think": V12_THINK,
    "v13-validate": V13_VALIDATE,
    "v13.1-validate": V13_1_VALIDATE,
    "v13.2-validate": V13_2_VALIDATE,
    "v14-certainty": V14_CERTAINTY,
    "v14-certainty-5": V14_CERTAINTY_5,
    "v14-certainty-pct": V14_CERTAINTY_PCT,
    "v14-blind": V14_BLIND,
    "v14-blind-10": V14_BLIND_10,
    "v14-certainty-10": V14_CERTAINTY_10,
    "v14-nemo-pct": V14_NEMO_PCT,
    "v15-recall-baseline": V15_RECALL_BASELINE,
    "v15.1-sysnoise": V15_1_SYSNOISE,
    "v15.2-negex": V15_2_NEGEX,
    "v15.3-combo": V15_3_COMBO,
    "v15.4-temp005": V15_4_TEMP005,
    "v15.3.1-temp0": V15_3_1_TEMP0,
    "v15.3.2-chunk600": V15_3_2_CHUNK600,
    "v15.3.3-chunk1200": V15_3_3_CHUNK1200,
    "v15.3.4-tightnon": V15_3_4_TIGHTNON,
    "v16-bigctx": V16_BIGCTX,
    "v7-v4t0": ExtractionVersion(
        name="v7-v4t0",
        description="v4 exact + temperature 0 (single variable change)",
        temperature=0.0,
        system_prompt=_V4_SYSTEM_LLAMA,
        system_prompt_by_model={
            "qwen3": _V4_SYSTEM_QWEN,
            "llama": _V4_SYSTEM_LLAMA,
        },
        facts_prompt=_V4_FACTS_PROMPT,
        entity_prompt=_V4_ENTITY_PROMPT,
        chunk_by_paragraph=True,
        max_chunk_words=800,
    ),
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
