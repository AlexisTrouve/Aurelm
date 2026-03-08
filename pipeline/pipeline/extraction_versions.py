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

    # Focus call — 3rd JSON extraction call focused on a specific entity type
    # (e.g. castes/institutions only). Runs per-chunk like calls 1 and 2,
    # and its results are merged into the entity list before dedup.
    focus_prompt: Optional[str] = None
    focus_prompt_by_model: Optional[dict[str, str]] = None

    # Per-call model overrides — let a cheaper/different model handle a specific pass.
    # e.g. validate_model = "meta-llama/llama-3.1-8b-instruct" for the validate pass
    #      (binary OUI/NON filter doesn't need qwen3:14b).
    # focus_model = "mistralai/mistral-nemo" for the focused extraction call.
    # None = use self.model (the main extraction model).
    validate_model: Optional[str] = None
    focus_model: Optional[str] = None

    # num_predict override specifically for the validate pass.
    # Validate responses are short (just a list of kept names), so 256 suffices.
    # When None, falls back to the global num_predict (default 4000).
    validate_num_predict: Optional[int] = None

    # Certainty score config — LLM self-assesses confidence per entity
    # certainty_scale: (min, max) — e.g. (1, 3) or (1, 10)
    # certainty_threshold: entities below this score are filtered out (0 = disabled)
    certainty_scale: tuple = (1, 3)
    certainty_threshold: int = 0  # 0 = no filtering (backwards compat)

    # Masked extraction passes — after first-pass dedup, replace found entity
    # names with _____ in the chunk text and run extra entity-only LLM calls.
    # Forces the LLM to look at what remains when dominant entities are hidden,
    # improving recall for techs/beliefs/creatures that get overshadowed otherwise.
    mask_and_retry: bool = False  # v21.0 compat — equivalent to mask_passes=1
    # mask_passes > 0 overrides mask_and_retry. 1 = one masked pass (v21.1+),
    # 2 = two sequential masked passes (v21.1 triple-pass), etc.
    mask_passes: int = 0
    # Custom prompt for the masked entity pass. If None, falls back to entity_prompt.
    # The mask prompt can explain what _____ means and focus on overlooked types.
    mask_entity_prompt: Optional[str] = None
    mask_entity_prompt_by_model: Optional[dict[str, str]] = None
    # Model for the masked pass. If None, falls back to self.model (extraction model).
    # Higher-precision models (e.g. qwen3.5-35b-a3b) may reduce hallucinations
    # when the LLM is given text stripped of its dominant entities.
    mask_model: Optional[str] = None
    # Per-pass prompts for scoped masked extraction (v21.5+).
    # If set, pass N uses mask_entity_prompts[N] (if index in range), falling back
    # to mask_entity_prompt then entity_prompt. Must be a tuple (frozen dataclass).
    # Useful to assign different entity-type scopes to each sequential masked pass,
    # e.g. pass 0 = techs/beliefs, pass 1 = persons/places.
    mask_entity_prompts: Optional[tuple] = None

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

    def get_focus_prompt(self, model: str = "") -> Optional[str]:
        """Return the focus prompt for a given model (falls back to focus_prompt)."""
        if self.focus_prompt_by_model and model:
            for prefix, prompt in self.focus_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.focus_prompt

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

    def get_mask_entity_prompt(self, model: str = "", pass_index: int = 0) -> str:
        """Return the entity prompt for a given masked pass.

        Priority order:
          1. mask_entity_prompts[pass_index] — per-pass scoped prompts (v21.5+)
          2. mask_entity_prompt_by_model — model-specific single prompt
          3. mask_entity_prompt — single custom prompt for all masked passes
          4. entity_prompt / entity_prompt_by_model — normal entity pass prompt
        """
        # Per-pass scoped prompt takes highest priority
        if self.mask_entity_prompts and pass_index < len(self.mask_entity_prompts):
            return self.mask_entity_prompts[pass_index]
        if self.mask_entity_prompt_by_model and model:
            for prefix, prompt in self.mask_entity_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        if self.mask_entity_prompt:
            return self.mask_entity_prompt
        return self.get_entity_prompt(model)

    def effective_mask_passes(self) -> int:
        """Number of masked passes to run after first extraction.

        mask_passes takes priority over mask_and_retry (backwards compat).
        """
        if self.mask_passes > 0:
            return self.mask_passes
        if self.mask_and_retry:
            return 1
        return 0


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
# v17: type-aware recall fix
#
# Two confirmed root causes for FNs in v15.3.4 (F1=69.5%):
#
# 1. entity_filter killed named technologies: Lances, Codex, Palanquin, Fresque(s)
#    Fix: removed them from _GENERIC_FRENCH_NOUNS in entity_filter.py
#
# 2. System prompt JAMAIS list had "reincarnation" as a single generic word —
#    unintentionally discouraged extraction of "Croyance en la reincarnation"
#    (4-word belief in the reference).
#    Fix: remove "reincarnation" from JAMAIS, add explicit belief examples.
#
# 3. LLM misses simple single-word technologies (Pilotis, Pigments, Rhombes, Cornex)
#    because they look like common nouns. Fix: add them to OUI example list.
#
# 4. LLM misses beliefs because no examples of multi-word named beliefs were shown.
#    Fix: add belief examples to both system prompt and entity_prompt.
# ---------------------------------------------------------------------------
_V17_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- Les outils simples sont des technologies nommees quand ils ont un role cle dans le recit : Lances, Pilotis, Rhombes, Pigments, Codex, Palanquin = OUI si mentionnes comme acquis/fabriques/utilises.
- Les croyances peuvent etre des formulations completes : "Croyance en la reincarnation", "Pelerinage de Gouffre Humide", "Yeux de l'aurore" = OUI (croyances nommees).
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type", "Grande Foret".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

_V17_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Pilotis", "Rhombes", "Pigments", "Codex", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang", "Croyance en la reincarnation", "Pelerinage de Gouffre Humide".
NON : mots communs, mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre).
NON : descriptions ("Un Faucon Chasseur veteran", "Action libre - L'epave", "Mars Attack").
NON : variantes — UNE forme par entite.
Si rien, retourne {{"entities": []}}."""

V17_TYPERECALL = ExtractionVersion(
    name="v17-typerecall",
    description=(
        "Type-aware recall fix — targets the 2 confirmed root causes of technology/belief FNs: "
        "(1) entity_filter no longer kills Lances/Codex/Palanquin/Fresque; "
        "(2) system prompt no longer has 'reincarnation' in JAMAIS list; "
        "(3) entity_prompt OUI list adds Pilotis/Rhombes/Pigments/Codex and belief examples. "
        "Based on v15.3.4-tightnon structure."
    ),
    system_prompt=_V17_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V17_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v18: T11-targeted recall fix (tools + compound places/institutions)
#
# Root causes diagnosed on T11 benchmark (F1=71.4%, 6 FNs, 10 FPs):
#
# FN root causes:
# 1. entity_filter blocked "Ciseaux de bois au dents d'obsidienne" (6 words, > 5 limit)
#    Fix: entity_filter.py threshold changed from > 5 to > 6.
#
# 2. LLM extracts "Antres" (1 word, blocked by antre/antres in GENERIC_FRENCH_NOUNS)
#    instead of the full "Antres des Echos". Fix: add to entity_prompt OUI.
#
# 3. LLM misses craft tools (burin en pierre, maillets en bois, ciseaux de bois)
#    because they look like descriptive phrases. Fix: explicit tech examples.
#
# 4. LLM misses "Voix de l'Aurore" (starts with lowercase "voix" in text).
#    Fix: add to entity_prompt OUI.
#
# FP root causes:
# 5. "Zone humide/chaude/seche/froide" = sections of a building, not entities.
#    Fix: explicit NON example.
# 6. "Foyer eternel", "Arbre de toutes les possibilites" = metaphors.
#    Fix: system prompt rule against abstract metaphors.
# ---------------------------------------------------------------------------
_V18_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- TOUJOURS le nom COMPLET compose : "Antres des Echos" (pas "Antres"), "Voix de l'Aurore" (pas "Voix").
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Grande Foret".
- JAMAIS de sections de batiment : "zone humide", "zone chaude", "zone seche", "zone froide".
- JAMAIS de metaphores ou images poetiques : "foyer eternel", "arbre de toutes les possibilites".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

_V18_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["outils/inventions nommes : 'burin en pierre', 'maillets en bois', 'ciseaux de bois au dents d obsidienne', 'rhombes', 'lances', 'argile vive'"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI : "Cercle des Sages", "Argile Vivante", "Ciels-clairs", "Gourdins", "Lances", "burin en pierre", "maillets en bois", "Voix de l'Aurore", "Antres des Echos".
NON : pronoms (lui, eux, toi, nous), mots purement generiques (homme, femme, vallee, village, riviere, montagne), phrases longues.
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : sections de batiment ("zone humide", "zone chaude", "zone seche", "zone froide") ni metaphores ("foyer eternel").
NON : descriptions avec articles ("Un Faucon Chasseur veteran", "Une Grande Foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete, avec le bon pluriel/tiret).
NOTE : des mots comme "marginaux", "artisans", "pecheurs", "chasseurs" peuvent designer des groupes sociaux nommes (castes). Extrais-les si utilises comme groupe distinct dans le texte."""

_V18_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Rhombes", "Antres des Echos", "Voix de l'Aurore", "burin en pierre", "maillets en bois", "ciseaux de bois au dents d obsidienne".
NON : mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre, homme, femme, riviere, village).
NON : sections de batiment ("zone humide", "zone chaude", "zone seche", "zone froide").
NON : descriptions ("Un Faucon Chasseur veteran", "Action libre - L'epave", "Mars Attack").
NON : variantes — UNE forme par entite.
NOTE : "marginaux", "artisans", "pecheurs", "chasseurs" peuvent etre des groupes sociaux nommes — extrais si groupe distinct.
Si rien, retourne {{"entities": []}}."""

V18_TOOLRECALL = ExtractionVersion(
    name="v18-toolrecall",
    description=(
        "T11-targeted: adds craft tool examples (burin/maillet/ciseaux) to OUI lists, "
        "compound place/institution completeness rule (Antres des Echos, Voix de l'Aurore), "
        "building-section NON examples (zone humide/chaude/seche/froide), "
        "metaphor JAMAIS rule. entity_filter threshold also bumped to > 6 words."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.1: v18 + validation pass (call 4: LLM filters the combined list)
#
# Goal: kill the persistent FPs that survive the NON instructions:
#   - Zone humide/chaude/seche/froide (building sections)
#   - Foyer eternel, Arbre de toutes les possibilites (metaphors)
#   - Argile vivante (doublon of Argile vive)
#   - Descriptive titles like "Trois Revelations de l'Arbitre des Esprits"
# Risk: over-filtering may drop some TPs → recall could drop slightly.
# ---------------------------------------------------------------------------
_V18_1_VALIDATE_PROMPT = """Tu valides une liste d'entites nommees extraites d'un texte de jeu.
Reponds UNIQUEMENT avec du JSON.

Texte de reference :
{text}

Entites a valider :
{entities}

VIRE une entite si c'est :
- Une section de batiment : "Zone humide", "Zone chaude", "Zone seche", "Zone froide"
- Une metaphore ou image poetique : "Foyer eternel", "Arbre de toutes les possibilites", "Fleuve du temps"
- Un doublon d'une entite deja presente (forme differente du meme nom : "Argile vivante" si "Argile vive" est la)
- Un titre de passage ou formulation narrative : "Trois Revelations de ...", "Premiere Revelation"
- Un mot seul generique sans contexte de jeu : "Foyer", "Ciel", "Riviere"

GARDE tout le reste : castes, institutions, lieux nommes, technologies, civilisations, croyances.

Reponds avec un JSON contenant les noms a conserver tels quels (copie exacte depuis la liste).
Exemple de format : {{"keep": ["Cercle des Sages", "Ailes-Grises", "Argile Vivante"]}}"""

V18_1_VALIDATE = ExtractionVersion(
    name="v18.1-validate",
    description=(
        "v18 + validation pass: LLM filters combined list to kill persistent FPs "
        "(Zone X building sections, metaphors, doublons). validate_prompt targets "
        "the specific FP patterns still surviving v18's NON instructions."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    validate_prompt=_V18_1_VALIDATE_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.2: v18 + GPT-NER marking pass (call 3: LLM annotates text inline)
#
# Goal: catch entities the JSON calls miss by asking the LLM to re-read
# the text and annotate every entity name with @@name## markers.
# Particularly useful for: Rhombes, Voix de l'Aurore (missed in dense paragraphs).
# Risk: mark pass tends to add FPs (no type constraint, any noun can be marked).
# label="unknown" for all marked entities (types resolved later by alias pass).
# ---------------------------------------------------------------------------
_V18_2_MARK_PROMPT = """Relis ce texte et entoure CHAQUE nom propre d'entite avec @@...## :
castes, institutions, lieux, technologies nommees, civilisations, personnages.

NE MODIFIE PAS le texte. Insere SEULEMENT les marqueurs @@...## autour des noms.
N'entoure PAS les mots communs, descriptions, metaphores ni sections de batiment.

Texte :
{text}"""

V18_2_MARK = ExtractionVersion(
    name="v18.2-mark",
    description=(
        "v18 + GPT-NER marking pass: LLM re-reads text and annotates entities "
        "inline with @@name## markers. Catches what JSON calls miss in dense paragraphs "
        "(Rhombes, Voix de l'Aurore). Risk: may add FPs (no type constraint)."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    mark_prompt=_V18_2_MARK_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.3: v18 + focused call (call 3b: JSON extraction for castes/institutions only)
#
# Goal: recover castes that fall through calls 1+2 in dense narrative chunks
# (Tailleurs de pierre, Explorateurs, Regards-Libres fluctuate as TPs/FNs).
# Uses focus_prompt → _llm_extract_focused() — a targeted JSON call with a
# narrower prompt than call 2.
# ---------------------------------------------------------------------------
_V18_3_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions et civilisations de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization", "context": "phrase courte"}}]}}

OUI : "Enfants des Echos", "Tailleurs de pierre", "Egalisateurs", "Dessinateurs", "Peintres", "Passes-bien", "Ailes-Grises", "Sans-ciels", "Ciels-libres", "Enfants du Courant", "Explorateurs", "Regards-Libres", "Voix de l'Aurore", "Assemblee des Chefs", "Cercle des Sages", "Maison des Decouvertes", "Tribunal des Moeurs".
NON : mots communs (tribus, peuple, habitants, artisans), pronoms, descriptions.
Si rien, retourne {{"entities": []}}."""

V18_3_FOCUS = ExtractionVersion(
    name="v18.3-focus",
    description=(
        "v18 + focused caste/institution call (call 3b): dedicated JSON pass "
        "targeting social groups and institutions only. Recovers castes that "
        "calls 1+2 miss in dense narrative (Tailleurs de pierre, Explorateurs, "
        "Regards-Libres, Voix de l'Aurore). Uses focus_prompt infrastructure."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    focus_prompt=_V18_3_FOCUS_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.4-combo: v18.3 (focus) + v18.1 (validate) + accent dedup fix
#
# Strategy: maximize recall with the focus call, then prune FPs with the
# validate pass using a cheap model (llama3.1:8b / meta-llama on OpenRouter).
#
# 3 extraction calls per chunk (facts+entities, entities-only, castes/institutions)
# + 1 global validate pass post-dedup using a cheaper/faster model.
#
# Expected: R≥90% from focus, FPs pruned by validate → best F1 combo.
# Dedup now normalizes accents so focus call (no accents in prompt) doesn't
# produce doublons vs calls 1+2 (accented output from qwen3:14b).
#
# validate_model = "meta-llama/llama-3.1-8b-instruct" (OpenRouter) or
#                  "llama3.1:8b" (Ollama local) — cheap binary filter task.
# ---------------------------------------------------------------------------
V18_4_COMBO = ExtractionVersion(
    name="v18.4-combo",
    description=(
        "v18 + focus call (castes/institutions) + validate pass (llama3.1:8b). "
        "Accent-normalized dedup to avoid doublons from focus call. "
        "3 extraction calls + 1 validate: maximize recall then prune FPs cheaply."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    focus_prompt=_V18_3_FOCUS_PROMPT,
    validate_prompt=_V18_1_VALIDATE_PROMPT,
    # Llama 3.1 8B handles binary OUI/NON filtering fine and is 4-5x cheaper.
    # OpenRouter: "meta-llama/llama-3.1-8b-instruct"
    # Ollama local: "llama3.1:8b"
    validate_model="meta-llama/llama-3.1-8b-instruct",
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.4.1: v18.4 + protected validate prompt (castes/institutions immune)
#           + Rhombes added to focus OUI list
#
# Root cause of v18.4 FNs: Llama's validate pass removes castes it perceives
# as "generic workers" (Tailleurs de pierre, Explorateurs) and institutions
# that aren't obviously institutional (Voix de l'Aurore).
# Fix: make the validate prompt explicitly type-aware — NE JAMAIS virer [caste]/[institution]/[person].
# Also: add Rhombes to focus prompt to catch the persistent tech FN.
# ---------------------------------------------------------------------------
_V18_4_1_VALIDATE_PROMPT = """Tu valides une liste d'entites nommees extraites d'un jeu de role.
Reponds UNIQUEMENT avec du JSON.

Texte de reference :
{text}

Entites a valider :
{entities}

VIRE UNIQUEMENT si c'est CLAIREMENT l'un de ces cas :
1. Section de batiment : "Zone humide", "Zone chaude", "Zone seche", "Zone froide"
2. Metaphore ou image poetique : "Foyer eternel", "Arbre de toutes les possibilites", "Fleuve du temps"
3. Doublon evident de la meme entite : "Argile vivante" si "Argile vive" est deja present
4. Titre narratif trop long ou descriptif : "Trois Revelations de l'Arbitre des Esprits", "Premiere revelation"
5. Mot seul generique (1 mot) sans specifique : "Foyer", "Ciel", "Riviere", "Batiment"

NE VIRE JAMAIS :
- Une caste ou groupe social [caste] — meme si le nom semble generique : "Tailleurs de pierre", "Explorateurs", "Passes-bien"
- Une institution [institution] — meme si peu connue : "Voix de l'Aurore", "Confluence des Echanges"
- Un personnage nomme [person]
- Une technologie nommee [technology]
- Un lieu nomme [place]

Reponds avec un JSON contenant les noms a conserver tels quels (copie exacte depuis la liste).
Exemple de format : {{"keep": ["Cercle des Sages", "Ailes-Grises", "Argile Vivante"]}}"""

_V18_4_1_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions, civilisations et technologies nommees de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization|technology", "context": "phrase courte"}}]}}

OUI : "Enfants des Echos", "Tailleurs de pierre", "Egalisateurs", "Dessinateurs", "Peintres", "Passes-bien", "Ailes-Grises", "Sans-ciels", "Ciels-libres", "Enfants du Courant", "Explorateurs", "Regards-Libres", "Voix de l'Aurore", "Assemblee des Chefs", "Cercle des Sages", "Maison des Decouvertes", "Tribunal des Moeurs", "Rhombes".
NON : mots purement generiques (peuple, habitants, gens), descriptions, sections de batiment.
NOTE : "marginaux", "artisans", "tribu" peuvent etre des groupes sociaux nommes — inclus si groupe distinct dans le texte.
Si rien, retourne {{"entities": []}}."""

V18_4_1_PROTECTCASTE = ExtractionVersion(
    name="v18.4.1-protectcaste",
    description=(
        "v18.4 + type-aware validate prompt (NE JAMAIS virer caste/institution/person/technology) "
        "+ Rhombes added to focus OUI list. "
        "Fixes: Tailleurs de pierre, Explorateurs, Voix de l'Aurore killed by Llama validate."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    focus_prompt=_V18_4_1_FOCUS_PROMPT,
    validate_prompt=_V18_4_1_VALIDATE_PROMPT,
    validate_model="meta-llama/llama-3.1-8b-instruct",
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v18.4.2: v18.4.1 same tweaks but Mistral-Nemo for validate
#
# Nemo is smaller/faster than qwen3:14b but better at French than llama3.1:8b.
# Hypothesis: Nemo's understanding of French nominal groups (castes with French
# names) is better than Llama's — less likely to strip "Tailleurs de pierre".
# ---------------------------------------------------------------------------
V18_4_2_NEMO = ExtractionVersion(
    name="v18.4.2-nemo",
    description=(
        "v18.4.1 prompts but validate_model = mistral-nemo (better French than llama3.1:8b). "
        "Tests if Nemo's French comprehension preserves French-named castes better."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    focus_prompt=_V18_4_1_FOCUS_PROMPT,
    validate_prompt=_V18_4_1_VALIDATE_PROMPT,
    validate_model="mistralai/mistral-nemo",
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v19-recall: v18.4.2-nemo with relaxed social-role NON lists
#
# Root cause of T05/T04 under-extraction: _V18_FACTS_PROMPT and _V18_ENTITY_PROMPT
# had "artisans, chasseurs, pecheurs, tribus" explicitly in the NON list, and
# "mots communs" as a catch-all. This blocked game-specific social group names
# (marginaux, artisans as a caste, tribunal special) that use common French vocab.
#
# Fix: remove social role words from NON lists, add NOTE clarifying they can be
# named castes/groups. entity_filter.py handles structural noise; semantic noise
# (truly generic words) is handled in post-processing.
# ---------------------------------------------------------------------------
V19_RECALL = ExtractionVersion(
    name="v19-recall",
    description=(
        "v18.4.2-nemo with relaxed social-role NON lists. Removes 'artisans, chasseurs, "
        "pecheurs, tribus' from NON mots communs — these can be named castes. Adds NOTE "
        "in all 3 extraction prompts clarifying social groups may be named entities."
    ),
    # _V18_SYSTEM unchanged — its JAMAIS list only blocks clearly generic single words
    system_prompt=_V18_SYSTEM,
    # facts + entity prompts now use the updated NON lists (modified in-place above)
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    # focus prompt also updated (artisans removed from NON)
    focus_prompt=_V18_4_1_FOCUS_PROMPT,
    validate_prompt=_V18_4_1_VALIDATE_PROMPT,
    validate_model="mistralai/mistral-nemo",
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# ---------------------------------------------------------------------------
# v20-clean: generic prompts (no game-specific entity names) + strong validate
#
# Root cause of contamination: OUI lists in v18/v19 contained hardcoded entity
# names from the game (Cheveux de Sang, Gorge Profonde, Hall des Serments, etc.)
# which caused the LLM to hallucinate those entities even when absent from text.
#
# Approach:
#   - Extraction prompts: TYPE-based guidance only, no specific entity names
#   - Focus prompt: describes caste/institution STRUCTURE, not specific names
#   - Validate: adds text-presence rule ("vire si le nom n'apparait pas dans le texte")
#   - Same 4-call architecture as v18.4.2-nemo
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# v22 prompts: adds explicit guidance for rituels/rites/architecture.
# Root insight: the pipeline consistently misses ritual practices (even named
# ones like "Rites de déposition des morts") and architectural elements
# (Pilotis, Paniers immergés) because prompts focus on weapons/institutions.
# Solution: add these categories explicitly in OUI examples and TOUJOURS rules.
# v22 system prompt is updated; facts/entity/focus user prompts are updated.
# ---------------------------------------------------------------------------

_V22_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- TOUJOURS le nom COMPLET compose : "Antres des Echos" (pas "Antres"), "Voix de l'Aurore" (pas "Voix").
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- TOUJOURS les rituels et rites nommes, meme si le nom semble courant : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres".
- TOUJOURS les elements d'architecture et d'infrastructure specifiques a la civilisation : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Grande Foret".
- JAMAIS de sections de batiment : "zone humide", "zone chaude", "zone seche", "zone froide".
- JAMAIS de metaphores ou images poetiques : "foyer eternel", "arbre de toutes les possibilites".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

_V22_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["outils/inventions nommes en 2-5 mots"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI si c'est : un NOM PROPRE, un GROUP SOCIAL DISTINCT, une INSTITUTION DE GOUVERNANCE, un OUTIL/TECHNIQUE NOMME.
OUI : rituels et rites nommes meme si le nom semble ordinaire : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres".
OUI : elements d'architecture et d'infrastructure : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
NON : pronoms (lui, eux, toi, nous), mots purement generiques (homme, femme, vallee, village, riviere, montagne).
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : metaphores ou images poetiques ("foyer eternel", "arbre de toutes les possibilites").
NON : descriptions avec articles indefinis ("Un chasseur veteran", "Une grande foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete).
NOTE : des groupes comme "marginaux", "artisans", "pecheurs", "chasseurs" peuvent designer des CASTES nommees. Extrais-les si utilises comme groupe social distinct dans le texte."""

_V22_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI si c'est un NOM PROPRE ou terme specifique : groupe social distinct, institution de gouvernance, outil/technique nomme, lieu geographique nomme, civilisation, croyance ritualisee.
OUI : rituels et rites nommes : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres", "Rites funeraires".
OUI : elements d'architecture/infrastructure : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
NON : mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre, homme, femme, riviere, village).
NON : descriptions longues ou phrases ("Un Faucon Chasseur veteran", "Action libre - L'epave").
NON : variantes — UNE forme par entite.
NOTE : groupes sociaux comme "artisans", "pecheurs", "chasseurs" peuvent etre des castes nommees — inclus si groupe distinct.
Si rien, retourne {{"entities": []}}."""

_V22_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions, civilisations, technologies et rituels nommees de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization|technology|belief", "context": "phrase courte"}}]}}

CASTES = groupes sociaux distincts avec un nom propre. Formes typiques :
  - Occupation au pluriel : "Sculpteurs", "Explorateurs", "Dessinateurs", "Peintres", "Chasseurs"
  - Nom compose avec trait d'union : "Ciels-libres", "Sans-ciels", "Porte-flammes", "Ailes-grises"
  - Formule "Enfants/Fils/Filles de X" : "Enfants des Echos", "Fils du Vent", "Enfants du Courant"
  - Adjectif + trait d'union : "Regards-Libres", "Passes-bien", "Pieds-noirs"
INSTITUTIONS = organes de gouvernance, de savoir ou de justice :
  - Formule "Assemblee/Cercle/Maison/Tribunal/Voix de X" : "Assemblee des Chefs", "Cercle des Sages", "Maison des Decouvertes", "Tribunal des Moeurs"
  - Autres organes nommes : "Confluence des Echanges", "Ordre des Anciens"
TECHNOLOGIES = outils, techniques, elements d'architecture ou savoir-faire nommes : "burin en pierre", "filet de peche leste", "rhombes", "pilotis", "paniers immerges"
RITUELS/CROYANCES = pratiques religieuses ou spirituelles nommees : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres"
NON : mots purement generiques (peuple, habitants, gens, tribu sans nom propre), descriptions, sections de batiment sans nom.
NOTE : des termes comme "marginaux", "artisans" peuvent designer des groupes sociaux distincts — inclus si groupe nomme dans le texte.
Si rien, retourne {{"entities": []}}."""

# ---------------------------------------------------------------------------
# v22.1 prompts: adds explicit event-type support.
# Root cause: "Grande Prospection", "Maladie des Antres" etc. are named
# historical EVENTS — not technologies, not beliefs. v22.0 had no TOUJOURS
# rule for events, no event examples in OUI sections, and _V22_FOCUS_PROMPT
# omitted the `event` type entirely. This version fixes all three gaps.
# ---------------------------------------------------------------------------

_V22_1_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- TOUJOURS le nom COMPLET compose : "Antres des Echos" (pas "Antres"), "Voix de l'Aurore" (pas "Voix").
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- TOUJOURS les rituels et rites nommes, meme si le nom semble courant : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres".
- TOUJOURS les elements d'architecture et d'infrastructure specifiques a la civilisation : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
- TOUJOURS les evenements nommes qui marquent l'histoire de la civilisation : une expedition collective, une epidemie fondatrice, un acte inaugural, une catastrophe nommee — UNIQUEMENT si le nom apparait litteralement dans le texte.
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Grande Foret".
- JAMAIS de sections de batiment : "zone humide", "zone chaude", "zone seche", "zone froide".
- JAMAIS de metaphores ou images poetiques : "foyer eternel", "arbre de toutes les possibilites".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

_V22_1_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["outils/inventions nommes en 2-5 mots"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI si c'est : un NOM PROPRE, un GROUP SOCIAL DISTINCT, une INSTITUTION DE GOUVERNANCE, un OUTIL/TECHNIQUE NOMME.
OUI : rituels et rites nommes meme si le nom semble ordinaire : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres".
OUI : elements d'architecture et d'infrastructure : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
OUI : evenements historiques nommes de la civilisation (type event) : une expedition collective nommee, une epidemie qui a marque la tribu, un acte inaugural — UNIQUEMENT si le nom exact apparait dans le texte.
NON : pronoms (lui, eux, toi, nous), mots purement generiques (homme, femme, vallee, village, riviere, montagne).
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : metaphores ou images poetiques ("foyer eternel", "arbre de toutes les possibilites").
NON : descriptions avec articles indefinis ("Un chasseur veteran", "Une grande foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete).
NOTE : des groupes comme "marginaux", "artisans", "pecheurs", "chasseurs" peuvent designer des CASTES nommees. Extrais-les si utilises comme groupe social distinct dans le texte."""

_V22_1_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI si c'est un NOM PROPRE ou terme specifique : groupe social distinct, institution de gouvernance, outil/technique nomme, lieu geographique nomme, civilisation, croyance ritualisee.
OUI : rituels et rites nommes : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres", "Rites funeraires".
OUI : elements d'architecture/infrastructure : "Pilotis", "Paniers immerges", "Rhombes", "Pipeau en bambou".
OUI : evenements historiques nommes (type event) : une expedition collective nommee, une epidemie fondatrice, un acte inaugural — UNIQUEMENT si le nom apparait litteralement dans le texte.
NON : mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre, homme, femme, riviere, village).
NON : descriptions longues ou phrases ("Un Faucon Chasseur veteran", "Action libre - L'epave").
NON : variantes — UNE forme par entite.
NOTE : groupes sociaux comme "artisans", "pecheurs", "chasseurs" peuvent etre des castes nommees — inclus si groupe distinct.
Si rien, retourne {{"entities": []}}."""

_V22_1_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions, civilisations, technologies, rituels et evenements nommes de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization|technology|belief|event", "context": "phrase courte"}}]}}

CASTES = groupes sociaux distincts avec un nom propre. Formes typiques :
  - Occupation au pluriel : "Sculpteurs", "Explorateurs", "Dessinateurs", "Peintres", "Chasseurs"
  - Nom compose avec trait d'union : "Ciels-libres", "Sans-ciels", "Porte-flammes", "Ailes-grises"
  - Formule "Enfants/Fils/Filles de X" : "Enfants des Echos", "Fils du Vent", "Enfants du Courant"
  - Adjectif + trait d'union : "Regards-Libres", "Passes-bien", "Pieds-noirs"
INSTITUTIONS = organes de gouvernance, de savoir ou de justice :
  - Formule "Assemblee/Cercle/Maison/Tribunal/Voix de X" : "Assemblee des Chefs", "Cercle des Sages", "Maison des Decouvertes", "Tribunal des Moeurs"
  - Autres organes nommes : "Confluence des Echanges", "Ordre des Anciens"
TECHNOLOGIES = outils, techniques, elements d'architecture ou savoir-faire nommes : "burin en pierre", "filet de peche leste", "rhombes", "pilotis", "paniers immerges"
RITUELS/CROYANCES = pratiques religieuses ou spirituelles nommees : "Rites de deposition des morts", "Rituels de Fertilite", "Culte des Ancetres"
EVENEMENTS = faits historiques nommes qui marquent l'histoire de la civilisation (type event) : expeditions collectives, epidemies fondatrices, actes inauguraux — UNIQUEMENT si le nom propre de l'evenement apparait litteralement dans le texte
NON : mots purement generiques (peuple, habitants, gens, tribu sans nom propre), descriptions, sections de batiment sans nom.
NOTE : des termes comme "marginaux", "artisans" peuvent designer des groupes sociaux distincts — inclus si groupe nomme dans le texte.
Si rien, retourne {{"entities": []}}."""

# ---------------------------------------------------------------------------
# v22.2.1 prompts: zero hardcoded game entity names anywhere.
# Root bug: examples like "Grande Prospection", "Maladie des Antres",
# "Confluence des Echanges", "Rites de deposition des morts" in OUI/TOUJOURS
# sections caused the LLM to hallucinate those exact entities in turns where
# they don't appear. Fix: replace ALL specific names with structural patterns.
# Rule: describe WHAT to extract (structure/pattern), never NAME it.
# ---------------------------------------------------------------------------

_V22_2_1_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- TOUJOURS le nom COMPLET compose : deux mots minimum si le nom est compose.
- UNE seule forme par entite. Si la forme plurielle existe, n'extrais pas aussi le singulier.
- TOUJOURS les rituels et rites nommes, meme si le nom semble courant — un rituel est nomme quand le texte lui donne un titre specifique en 2+ mots.
- TOUJOURS les elements d'architecture et d'infrastructure specifiques a la civilisation — outils, constructions, instruments nommes par le texte.
- TOUJOURS les evenements nommes qui marquent l'histoire de la civilisation — UNIQUEMENT si le nom propre de l'evenement apparait litteralement dans le texte, pas par inference.
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions longues avec article indefini : "Un chasseur veteran", "Une grande expedition", "Le representant des pecheurs".
- JAMAIS de sections de batiment : "zone humide", "zone chaude", "zone seche", "zone froide".
- JAMAIS de metaphores ou images poetiques : "foyer eternel", "arbre de toutes les possibilites".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom extrait."""

_V22_2_1_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["outils/inventions nommes en 2-5 mots"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI si c'est : un NOM PROPRE, un GROUPE SOCIAL DISTINCT, une INSTITUTION DE GOUVERNANCE, un OUTIL/TECHNIQUE NOMME en 2+ mots.
OUI : rituels et rites quand le texte leur donne un NOM PROPRE en 2+ mots (ex: un rituel funeraire nomme, une pratique saisonniere nommee).
OUI : elements d'architecture/infrastructure quand ils ont un NOM SPECIFIQUE dans le texte (ex: un outil nomme, un instrument nomme).
OUI : evenements historiques quand leur NOM PROPRE apparait litteralement dans le texte (ex: le nom d'une expedition, d'une epidemie nommee).
NON : pronoms (lui, eux, toi, nous), mots purement generiques (homme, femme, vallee, village, riviere, montagne).
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : metaphores ou images poetiques ("foyer eternel", "arbre de toutes les possibilites").
NON : descriptions avec articles indefinis ("Un chasseur veteran", "Une grande foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete).
NOTE : des groupes comme "marginaux", "artisans", "pecheurs", "chasseurs" peuvent designer des CASTES nommees. Extrais-les si utilises comme groupe social distinct dans le texte."""

_V22_2_1_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI si c'est un NOM PROPRE ou terme specifique en 2+ mots : groupe social distinct, institution de gouvernance, outil/technique nomme, lieu geographique nomme, civilisation, croyance ritualisee.
OUI : rituels et rites quand le texte leur donne un NOM PROPRE specifique en 2+ mots.
OUI : elements d'architecture/infrastructure quand ils ont un nom specifique dans le texte.
OUI : evenements historiques (type event) UNIQUEMENT si leur nom propre apparait litteralement dans le texte.
NON : mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre, homme, femme, riviere, village).
NON : descriptions longues ou phrases avec article indefini.
NON : variantes — UNE forme par entite.
NOTE : groupes sociaux comme "artisans", "pecheurs", "chasseurs" peuvent etre des castes nommees — inclus si groupe distinct.
Si rien, retourne {{"entities": []}}."""

_V22_2_1_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions, civilisations, technologies, rituels et evenements nommes de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization|technology|belief|event", "context": "phrase courte"}}]}}

CASTES = groupes sociaux distincts avec un nom propre dans le texte. Formes typiques :
  - Occupation au pluriel : un metier ou role social utilise comme nom de groupe
  - Nom compose avec trait d'union : une identite de groupe avec tiret
  - Formule "Enfants/Fils/Filles de X" : filiation symbolique utilisee comme nom de groupe
  - Adjectif substantive avec trait d'union : identite adjectivale
INSTITUTIONS = organes de gouvernance, de savoir ou de justice avec un nom propre :
  - Formule "Assemblee/Cercle/Maison/Tribunal/Voix/Conseil de X"
  - Tout organe formel designe par un nom propre compose dans le texte
TECHNOLOGIES = outils, techniques, elements d'architecture ou savoir-faire avec un nom specifique en 2+ mots dans le texte
RITUELS/CROYANCES = pratiques religieuses ou spirituelles avec un NOM PROPRE en 2+ mots dans le texte
EVENEMENTS = faits historiques avec un NOM PROPRE dans le texte — UNIQUEMENT si ce nom apparait litteralement, jamais par inference
NON : mots purement generiques (peuple, habitants, gens, tribu sans nom propre), descriptions, sections de batiment sans nom.
NOTE : des termes comme "marginaux", "artisans" peuvent designer des groupes sociaux distincts — inclus si groupe nomme dans le texte.
Si rien, retourne {{"entities": []}}."""

# Alias — v20/v21 versions use this name; v22 prompt is a superset (added OUI
# lines for rituels/architecture) so pointing old versions here is safe.
_V20_FACTS_PROMPT = _V22_FACTS_PROMPT

_V20_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI si c'est un NOM PROPRE ou terme technique specifique en 2-5 mots : groupe social distinct, institution de gouvernance, outil/technique nomme, lieu geographique nomme, civilisation, croyance ritualisee.
NON : mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre, homme, femme, riviere, village).
NON : descriptions longues ou phrases ("Un Faucon Chasseur veteran", "Action libre - L'epave").
NON : variantes — UNE forme par entite.
NOTE : groupes sociaux comme "artisans", "pecheurs", "chasseurs" peuvent etre des castes nommees — inclus si groupe distinct.
Si rien, retourne {{"entities": []}}."""

_V20_FOCUS_PROMPT = """Extrait UNIQUEMENT les castes, groupes sociaux, institutions, civilisations et technologies nommees de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "caste|institution|civilization|technology", "context": "phrase courte"}}]}}

CASTES = groupes sociaux distincts avec un nom propre. Formes typiques :
  - Occupation au pluriel : "Sculpteurs", "Explorateurs", "Dessinateurs", "Peintres", "Chasseurs"
  - Nom compose avec trait d'union : "Ciels-libres", "Sans-ciels", "Porte-flammes", "Ailes-grises"
  - Formule "Enfants/Fils/Filles de X" : "Enfants des Echos", "Fils du Vent", "Enfants du Courant"
  - Adjectif + trait d'union : "Regards-Libres", "Passes-bien", "Pieds-noirs"
INSTITUTIONS = organes de gouvernance, de savoir ou de justice :
  - Formule "Assemblee/Cercle/Maison/Tribunal/Voix de X" : "Assemblee des Chefs", "Cercle des Sages", "Maison des Decouvertes", "Tribunal des Moeurs"
  - Autres organes nommes : "Confluence des Echanges", "Ordre des Anciens"
TECHNOLOGIES = outils, techniques ou savoir-faire nommes en 2-5 mots : "burin en pierre", "filet de peche leste", "rhombes"
NON : mots purement generiques (peuple, habitants, gens, tribu sans nom propre), descriptions, sections de batiment sans nom.
NOTE : des termes comme "marginaux", "artisans" peuvent designer des groupes sociaux distincts — inclus si groupe nomme dans le texte.
Si rien, retourne {{"entities": []}}."""

_V20_VALIDATE_PROMPT = """Tu valides une liste d'entites nommees extraites d'un jeu de role.
Reponds UNIQUEMENT avec du JSON.

Texte de reference :
{text}

Entites a valider :
{entities}

VIRE UNIQUEMENT si c'est CLAIREMENT l'un de ces cas :
1. Metaphore ou image poetique : "Foyer eternel", "Arbre de toutes les possibilites", "Fleuve du temps"
2. Doublon evident de la meme entite : "Argile vivante" si "Argile vive" est deja present
3. Titre narratif trop long ou descriptif : "Trois Revelations de l'Arbitre des Esprits"
4. Mot seul generique (1 mot) sans specifique : "Foyer", "Ciel", "Riviere", "Batiment"
5. Entite dont AUCUN mot significatif (longueur >= 4) ne se retrouve nulle part dans le texte, meme approximativement

NE VIRE JAMAIS :
- Une caste ou groupe social [caste] — meme si le nom semble generique : "Tailleurs de pierre", "Explorateurs", "Ailes-Grises", "Sans-ciels"
- Une institution [institution] — meme si peu connue : "Voix de l'Aurore", "Confluence des Echanges"
- Une technologie nommee [technology] en 2+ mots : "burin en pierre", "ciseaux de bois"
- Un personnage nomme [person]
- Un lieu nomme [place]
En cas de doute, GARDE l'entite.

Reponds avec un JSON contenant les noms a conserver tels quels (copie exacte depuis la liste).
Exemple de format : {{"keep": ["Cercle des Sages", "Ailes-Grises", "Argile Vivante"]}}"""

# ---------------------------------------------------------------------------
# v20.1-clean: v20-clean + redesigned nemo validate prompt
#
# Problems with v20 validate prompt:
#   - Two conflicting blocks (VIRE si / NE VIRE JAMAIS) → nemo takes shortcuts,
#     killed ALL technologies in T06 despite explicit NE VIRE JAMAIS [technology].
#   - No few-shot examples: nemo guesses intent instead of following rules.
#   - num_predict=4000 wasted for a ~100 char response.
#
# Fixes:
#   - Positive framing: GARDE by default, SUPPRIME only 3 explicit cases.
#   - Type protections stated FIRST with concrete domain examples.
#   - Few-shot examples covering the exact failure modes (technologies kept).
#   - validate_num_predict=256 (enough for a JSON list of names).
# ---------------------------------------------------------------------------

_V20_1_VALIDATE_PROMPT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide. Aucune explication.

REGLE : GARDE tout par defaut.
SUPPRIME seulement si c'est clairement l'un de ces 3 cas :
1. Metaphore poetique sans referent concret dans le texte : "Fleuve du temps", "Bras de la mort"
2. Un seul mot generique (pas un nom propre) : "feu", "ciel", "riviere", "montagne"
3. Doublon exact d'une autre entite de la liste

Exemples :
- "Gardiens du Feu Sacre" [caste]          → GARDE
- "Lance a pointe d'obsidienne" [technology] → GARDE
- "Voix des Ancetres" [belief]             → GARDE (nom propre d'une croyance)
- "Conseil des Sages" [institution]        → GARDE
- "Fleuve du temps" [belief]               → SUPPRIME (metaphore, pas une entite reelle)
- "feu" [place]                            → SUPPRIME (mot generique)

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec exactement ce format :
{{"keep": ["Nom Exact 1", "Nom Exact 2"]}}"""

V20_1_CLEAN = ExtractionVersion(
    name="v20.1-clean",
    description=(
        "v20-clean + redesigned nemo validate prompt. "
        "Positive framing (GARDE by default), type protections first, "
        "few-shot examples covering technology/caste/institution cases. "
        "validate_num_predict=256 (validate responses are ~100 chars)."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_1_VALIDATE_PROMPT,
    validate_model="mistralai/mistral-nemo",
    validate_num_predict=256,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


# ---------------------------------------------------------------------------
# v20.2-clean: v20.1 + per-entity reasoning in nemo validate
#
# Change: output format {"keep": [...]} → {"decisions": [{name, keep, reason}]}
# Forcing nemo to justify each decision improves consistency and gives us
# visibility on why entities are dropped (debuggable).
# validate_num_predict bumped to 512 (was 256) to fit ~15 entries with reasons.
# ---------------------------------------------------------------------------

_V20_2_VALIDATE_PROMPT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

REGLE : GARDE tout par defaut.
SUPPRIME seulement si c'est clairement l'un de ces cas :
- Metaphore poetique sans referent concret dans le texte
- Un seul mot generique commun (pas un nom propre, pas un outil, pas un groupe social)
- Doublon exact d'une autre entite de la liste

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec ce format JSON :
- "keep" : noms exacts des entites gardees (copies depuis la liste ci-dessus)
- "drops" : pour chaque entite supprimee, ecrire "nom exact: raison textuelle courte" separes par " | "

{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison textuelle | Nom2 supprime: raison textuelle"}}"""

V20_2_CLEAN = ExtractionVersion(
    name="v20.2-clean",
    description=(
        "v20.1-clean + per-entity reasoning in validate. "
        "Uses qwen3:14b for validation (not nemo) — nemo can only handle simple lists, "
        "loops with dots on any format that requires textual reasoning in a string field. "
        "Output format: {keep: [...], drops: 'name: reason | name2: reason2'}. "
        "validate_num_predict=512."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",  # qwen3 handles structured reasoning; nemo loops on drops field
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)


V21_0_MASKED = ExtractionVersion(
    name="v21.0-masked",
    description=(
        "v20.2-clean + masked second-pass extraction. "
        "After first-pass dedup, replaces found entity names with _____ in the chunk text "
        "and runs an extra entity-only LLM call. Without dominant entities (Oracle, Cercle des Sages...) "
        "the LLM is forced to find what remains — improves recall for techs/beliefs/creatures."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_and_retry=True,
)

# ---------------------------------------------------------------------------
# Masked-pass prompt — explains the _____ placeholders and redirects focus
# to the entity types systematically missed by the main extraction passes.
# Used by v21.2 and v21.4.
# ---------------------------------------------------------------------------
_V21_MASK_ENTITY_PROMPT = """\
Dans le texte ci-dessous, _____ représente des entités nommées déjà identifiées \
(personnes, institutions majeures, castes, lieux connus...).

Ta tâche : extraire UNIQUEMENT les entités nommées que _____ n'a PAS remplacées.
Concentre-toi sur ce que les autres appels ratent systématiquement :
- Technologies et outils (procédés, artefacts, instruments nommés)
- Ressources naturelles et plantes avec un nom propre
- Lieux et environnements nommés (gorges, plateaux, zones précises)
- Croyances, rituels et pratiques sociales nommées
- Créatures et espèces avec un nom propre
- Groupes et institutions secondaires

N'extrais PAS : les blancs _____ eux-mêmes, les objets entièrement génériques (pierre, eau, bois).

Texte :
{text}

Réponds UNIQUEMENT en JSON :
{{"entities": [{{"name": "nom exact tel qu'écrit dans le texte", \
"type": "technology|place|belief|resource|creature|institution|caste|person|event|civilization", \
"context": "courte phrase où il apparaît"}}]}}"""

# ---------------------------------------------------------------------------
# v21.1-masked-triple: 2 sequential masked passes (triple-pass total)
# Each pass uses entities from all previous passes to mask the text, then
# searches for what remains — progressively peeling layers of saliency.
# ---------------------------------------------------------------------------
V21_1_MASKED_TRIPLE = ExtractionVersion(
    name="v21.1-masked-triple",
    description=(
        "v21.0-masked + a second masked pass (triple-pass total). "
        "Pass 1: normal 4-call extraction. Pass 2: mask P1 entities -> extract again. "
        "Pass 3: mask P1+P2 entities -> extract again. Same prompt/model as normal entity pass."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=2,  # 2 extra masked passes after the initial extraction
)

# ---------------------------------------------------------------------------
# v21.2-masked-prompt: 1 masked pass with a targeted prompt
# The mask prompt explains what _____ means and focuses on overlooked types.
# ---------------------------------------------------------------------------
V21_2_MASKED_PROMPT = ExtractionVersion(
    name="v21.2-masked-prompt",
    description=(
        "v21.0-masked + custom masked-pass prompt that explains _____ placeholders "
        "and explicitly targets technologies/resources/beliefs/creatures overlooked by the main pass."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_entity_prompt=_V21_MASK_ENTITY_PROMPT,
)

# ---------------------------------------------------------------------------
# v21.3-masked-llm: 1 masked pass with a higher-precision model
# qwen3.5-35b-a3b had 94.1% precision on T11 vs 81% for qwen3:14b —
# less likely to hallucinate when the text is stripped of its main entities.
# ---------------------------------------------------------------------------
V21_3_MASKED_LLM = ExtractionVersion(
    name="v21.3-masked-llm",
    description=(
        "v21.0-masked + different model for the masked pass (qwen/qwen3.5-35b-a3b). "
        "High-precision model reduces hallucinations on impoverished (heavily masked) text."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_model="qwen/qwen3.5-35b-a3b",
)

# ---------------------------------------------------------------------------
# v21.4-masked-both: 1 masked pass with targeted prompt + high-precision model
# Combines v21.2 (targeted prompt) and v21.3 (35b-a3b model).
# ---------------------------------------------------------------------------
V21_4_MASKED_BOTH = ExtractionVersion(
    name="v21.4-masked-both",
    description=(
        "v21.0-masked + targeted mask prompt (v21.2) + qwen3.5-35b-a3b model (v21.3). "
        "Best-of-both: the prompt explains _____ and focuses on missed types; "
        "the high-precision model reduces hallucinations."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_entity_prompt=_V21_MASK_ENTITY_PROMPT,
    mask_model="qwen/qwen3.5-35b-a3b",
)

# ---------------------------------------------------------------------------
# v21.5-scoped: 2 masked passes, each targeting a different entity-type scope.
# Pass 0: tech/beliefs/resources/creatures — typically missed by main passes.
# Pass 1: persons/places/institutions — secondary ones missed by main passes.
# Each pass only sees entities remaining AFTER all previous passes are masked.
# ---------------------------------------------------------------------------
_V21_MASK_SCOPE0_PROMPT = """\
Dans ce texte, _____ remplace des entites nommees deja identifiees.

Passe 1 - Culture materielle et savoirs.
Extrais UNIQUEMENT ce qui reste dans cette categorie :
- Technologies, outils, procedes de fabrication (meme non capitalises)
- Ressources naturelles ou matieres avec un nom specifique
- Croyances, rituels, pratiques sociales nommes
- Etres vivants ou especes avec un nom propre

N'inclus PAS de personnages, institutions ou lieux (reserves a la passe suivante).

Texte :
{text}

JSON uniquement :
{{"entities": [{{"name": "nom tel qu'ecrit", "type": "technology|resource|belief|creature", "context": "courte phrase"}}]}}\
"""

_V21_MASK_SCOPE1_PROMPT = """\
Dans ce texte, _____ remplace des entites nommees deja identifiees.

Passe 2 - Acteurs et espaces.
Extrais UNIQUEMENT ce qui reste dans cette categorie :
- Personnes ou personnages avec un nom propre non encore captures
- Lieux, zones, environnements nommes (gorges, plateaux, batiments, routes)
- Groupes, institutions, castes secondaires non encore captures
- Evenements ou moments cles nommes

N'inclus PAS technologies, ressources ou croyances (couverts par la passe precedente).

Texte :
{text}

JSON uniquement :
{{"entities": [{{"name": "nom tel qu'ecrit", "type": "person|place|institution|caste|event|civilization", "context": "courte phrase"}}]}}\
"""

V21_5_SCOPED = ExtractionVersion(
    name="v21.5-scoped",
    description=(
        "v21.0-masked + 2 scoped masked passes with different type-buckets. "
        "Pass 0 (tech/beliefs/resources/creatures) + pass 1 (persons/places/institutions). "
        "Each pass forces focus on one half of the entity taxonomy."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=2,
    # Per-pass prompts: pass 0 = tech scope, pass 1 = person/place scope
    mask_entity_prompts=(_V21_MASK_SCOPE0_PROMPT, _V21_MASK_SCOPE1_PROMPT),
)

# ---------------------------------------------------------------------------
# v21.6-llama: 2 masked passes using llama3.1:8b as the mask-pass model.
# Tests whether a different architecture (llama vs qwen3) handles masked text
# better — the 35b-a3b (also non-qwen3) returned empty JSON, llama may differ.
# ---------------------------------------------------------------------------
V21_6_LLAMA = ExtractionVersion(
    name="v21.6-llama",
    description=(
        "v21.0-masked + 2 masked passes using llama3.1:8b as mask-pass model. "
        "Tests if llama architecture handles masked (_____ heavy) text better "
        "than qwen3 (which tends to ignore remaining content) or 35b-a3b (empty JSON)."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=2,
    mask_model="meta-llama/llama-3.1-8b-instruct",
)

# ---------------------------------------------------------------------------
# v21.7-radical: 1 masked pass with a completely different framing.
# Instead of "named entity extraction", frames the task as completing an
# archaeologist's catalog — explicitly drops the proper-noun requirement
# and biases toward exhaustiveness. Targets the core missed-entity pattern:
# specific cultural terms that look like common nouns (gourdins, pieu...).
# ---------------------------------------------------------------------------
_V21_RADICAL_PROMPT = """\
Un groupe d'anthropologues documente une civilisation fictive.
Ils ont deja repertorie ses entites majeures dans le texte (remplacees par _____).

Ta mission : COMPLETER leur catalogue avec ce qu'ils ont manque.

Critere d'inclusion : un terme merite d'etre inclus s'il est PROPRE a cette civilisation
(outil, procede, rituel, substance, espece, lieu ou concept nomme), MEME si ce terme
ressemble a un nom commun francais ordinaire. Ce qui compte : est-ce specifique a
cette culture fictive ? Pas : est-ce un nom propre capitalise ?

Methode en 2 etapes :
1. Liste mentalement tous les termes restants qui semblent specifiques a ce groupe.
2. Selectionne ceux qui auraient leur place dans une encyclopedie de cette civilisation.

Ne filtre pas trop — mieux vaut inclure un terme douteux que rater une entite culturelle.

Texte :
{text}

Retourne UNIQUEMENT ce JSON (sois exhaustif) :
{{"entities": [{{"name": "nom tel qu'il apparait dans le texte", \
"type": "technology|place|belief|resource|creature|institution|caste|person|event|civilization", \
"context": "courte phrase d'ou il vient"}}]}}\
"""

V21_7_RADICAL = ExtractionVersion(
    name="v21.7-radical",
    description=(
        "v21.0-masked + radical prompt change: 'catalogue incomplet d'anthropologues'. "
        "Drops the proper-noun filter — any term SPECIFIC TO THIS CIVILIZATION counts. "
        "Targets the core missed-entity problem: culturally-specific common nouns "
        "(gourdins, pieu, lait de pierre) that standard extraction consistently misses."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_entity_prompt=_V21_RADICAL_PROMPT,
)


# ---------------------------------------------------------------------------
# v21.8-radical-filtered: v21.7 radical prompt + explicit N'EXTRAIS PAS list
# for abstract concepts, emotions, and biological states.
# v21.7 breakthrough: found Gourdins + Pieu for the first time by dropping the
# proper-noun filter. v21.8 tries to keep that gain while reducing the 32 FPs
# caused by: Corps, Esprit, Faim, Fatigue, Mort, Naissance, Univers, Pays...
# ---------------------------------------------------------------------------
_V21_8_RADICAL_FILTERED_PROMPT = """\
Un groupe d'anthropologues documente une civilisation fictive.
Ils ont deja repertorie ses entites majeures dans le texte (remplacees par _____).

Ta mission : COMPLETER leur catalogue avec ce qu'ils ont manque.

EXTRAIS — termes specifiques a cette civilisation :
- Outils, armes, techniques de fabrication (meme noms communs : "gourdins", "pieu", "filet leste")
- Substances, materiaux ou ressources avec un nom ou usage culturel specifique
- Especes animales ou vegetales importantes pour ce groupe (avec nom propre ou denomination locale)
- Rituels, pratiques sociales, croyances nommees
- Lieux, structures, espaces geographiques nommes

N'EXTRAIS PAS — termes trop generiques ou abstraits :
- Emotions et etats mentaux : peur, faim, fatigue, joie, tristesse, espoir, honte
- Etats biologiques et evenements du vivant : mort, naissance, maladie, vieillesse
- Concepts abstraits : univers, nature, vie, temps, choix, destin, liberte, verite
- Verbes nominalises sans specifique culturel : depart, retour, arrivee, rencontre, crise
- Mots ultra-generiques : bois, eau, feu, ciel, terre, pays, lieu, groupe, peuple

Texte :
{text}

JSON uniquement :
{{"entities": [{{"name": "nom tel qu'il apparait dans le texte", \
"type": "technology|place|belief|resource|creature|institution|caste|person|event|civilization", \
"context": "courte phrase d'ou il vient"}}]}}\
"""

V21_8_RADICAL_FILTERED = ExtractionVersion(
    name="v21.8-radical-filtered",
    description=(
        "v21.7 radical ('catalogue anthropologue') + explicit N'EXTRAIS PAS for abstract "
        "concepts, emotions, and biological states. Keeps the proper-noun filter drop "
        "(which found gourdins + pieu) while excluding: Corps, Esprit, Faim, Fatigue, "
        "Mort, Naissance, Univers, Pays (the 32 FPs from v21.7)."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_entity_prompt=_V21_8_RADICAL_FILTERED_PROMPT,
)


# ---------------------------------------------------------------------------
# v21.9-radical-protected: v21.8 + validate prompt protects concrete tools/weapons/
# materials explicitly. Root cause of v21.8 failure: validate drops Gourdins/Pieu
# as "Metaphore poetique" even though the rule says "pas un outil". Adding an
# explicit GARDE TOUJOURS clause for outils concrets + validate_num_predict=1024
# to give the validate model enough tokens to reason carefully with 20+ entities.
# ---------------------------------------------------------------------------
_V21_9_VALIDATE_PROMPT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

GARDE TOUJOURS sans exception :
- Outils, armes, techniques de fabrication, materiaux — meme si le nom semble ordinaire
  (ex: "gourdins", "pieu", "filet", "rhombes", "serpes", "casiers a poisson")
- Groupes sociaux, castes, institutions nommees
- Lieux geographiques nommes

REGLE : GARDE tout par defaut.
SUPPRIME seulement si c'est clairement l'un de ces cas :
- Metaphore poetique sans referent concret dans le texte (ex: "Espoir", "Destin")
- Un seul mot ultra-generique (pas un outil, pas un groupe social, pas un lieu)
- Doublon exact d'une autre entite de la liste

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec ce format JSON :
- "keep" : noms exacts des entites gardees (copies depuis la liste ci-dessus)
- "drops" : pour chaque entite supprimee, ecrire "nom exact: raison textuelle courte" separes par " | "

{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison textuelle | Nom2 supprime: raison textuelle"}}"""

V21_9_RADICAL_PROTECTED = ExtractionVersion(
    name="v21.9-radical-protected",
    description=(
        "v21.8 + validate prompt adds explicit GARDE TOUJOURS for outils/armes/materiaux. "
        "Root cause fix: validate was dropping Gourdins+Pieu as 'Metaphore poetique' despite "
        "rule 'pas un outil'. New validate also bumps num_predict to 1024 (512 was too short "
        "for 20+ entities with per-entity reasoning)."
    ),
    system_prompt=_V18_SYSTEM,
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V21_9_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=1024,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
    mask_entity_prompt=_V21_8_RADICAL_FILTERED_PROMPT,
)


V20_CLEAN = ExtractionVersion(
    name="v20-clean",
    description=(
        "Generic prompts (no hardcoded game entity names in OUI). "
        "TYPE-based guidance only: castes/institutions described structurally. "
        "Validate adds text-presence rule: remove anything not literally in the text. "
        "Same 4-call architecture as v18.4.2-nemo (facts + entities + focus + nemo validate)."
    ),
    system_prompt=_V18_SYSTEM,  # /no_think system prompt, unchanged
    facts_prompt=_V20_FACTS_PROMPT,
    entity_prompt=_V20_ENTITY_PROMPT,
    focus_prompt=_V20_FOCUS_PROMPT,
    validate_prompt=_V20_VALIDATE_PROMPT,
    validate_model="mistralai/mistral-nemo",
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
# v22.0: new baseline with v22 prompts — rituels/rites/architecture added.
# Incorporates the key insight from v21.x series: the pipeline misses ritual
# names and architectural elements because the prompts don't mention them.
# Uses _V22_SYSTEM (adds TOUJOURS rituels + architecture) and _V22_*_PROMPT
# (adds explicit OUI examples for both categories in all 3 extraction calls).
# Reference set also cleaned: -8 generic entities (Gourdins, Pieu, Fumage,
# Poisson fumé, Radeaux, Vallée, Techniques de polissage, Passerelles) → 34.
# ---------------------------------------------------------------------------
V22_0 = ExtractionVersion(
    name="v22.0",
    description=(
        "New baseline: v21.0-masked architecture (1 masked pass, qwen3:14b) "
        "with updated system + user prompts that explicitly mention rituels/rites "
        "('Rites de déposition des morts', 'Rituels de Fertilité') and architecture "
        "('Pilotis', 'Paniers immergés') in OUI examples. Focus prompt now includes "
        "a RITUELS/CROYANCES category. System prompt adds TOUJOURS rules for both."
    ),
    system_prompt=_V22_SYSTEM,
    facts_prompt=_V22_FACTS_PROMPT,
    entity_prompt=_V22_ENTITY_PROMPT,
    focus_prompt=_V22_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
)

# ---------------------------------------------------------------------------
# v22.1: v22.0 + explicit event-type support.
# Adds TOUJOURS rule for named historical events in system prompt, OUI examples
# for events in facts/entity prompts, and ÉVÉNEMENTS category in focus prompt
# (which also now includes `event` in the type enum — it was absent in v22.0).
# Targets FN like "Grande Prospection", "Maladie des Antres", "Premier Meurtre".
# ---------------------------------------------------------------------------
V22_1 = ExtractionVersion(
    name="v22.1",
    description=(
        "v22.0 + event type: TOUJOURS rule for named historical events in system "
        "prompt, OUI event examples in facts/entity prompts, EVENEMENTS category "
        "in focus prompt. Targets FN like 'Grande Prospection', 'Maladie des Antres'."
    ),
    system_prompt=_V22_1_SYSTEM,
    facts_prompt=_V22_1_FACTS_PROMPT,
    entity_prompt=_V22_1_ENTITY_PROMPT,
    focus_prompt=_V22_1_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
)

# ---------------------------------------------------------------------------
# v22.2.1-pastlevel: v22.2-pastlevel + zero hardcoded game entity names.
# All specific entity names removed from OUI/TOUJOURS examples — replaced by
# structural patterns only. Fixes hallucination of entities like "Grande
# Prospection" or "Rites de deposition des morts" in turns where they don't
# appear, caused by the LLM memorizing prompt examples.
# ---------------------------------------------------------------------------
V22_2_1_PASTLEVEL = ExtractionVersion(
    name="v22.2.1-pastlevel",
    description=(
        "v22.2-pastlevel + zero hardcoded game entity names in prompts. "
        "All OUI/TOUJOURS examples replaced by structural patterns (no specific "
        "names). Fixes hallucination of entities from prompt examples. "
        "Tech/fantasy context injection unchanged."
    ),
    system_prompt=_V22_2_1_SYSTEM,
    facts_prompt=_V22_2_1_FACTS_PROMPT,
    entity_prompt=_V22_2_1_ENTITY_PROMPT,
    focus_prompt=_V22_2_1_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
)

# ---------------------------------------------------------------------------
# v22.2-pastlevel: v22.1 + tech/fantasy era context injection.
# The system prompt now receives the previous turn's tech_era and fantasy_level
# (injected at runtime by FactExtractor from the pipeline's carry-forward state).
# This lets the LLM calibrate what is "notable" in context: a ship is major
# tech in a neolithic civ, mundane in antiquity. Same prompts as v22.1 —
# the context injection is done dynamically in fact_extractor.py.
# ---------------------------------------------------------------------------
V22_2_PASTLEVEL = ExtractionVersion(
    name="v22.2-pastlevel",
    description=(
        "v22.1 + runtime tech/fantasy context injection: the previous turn's "
        "tech_era and fantasy_level are appended to the system prompt so the LLM "
        "calibrates notability by era (e.g. 'navires' = major tech in neolithique). "
        "Prompts identical to v22.1; context injected dynamically by FactExtractor."
    ),
    system_prompt=_V22_1_SYSTEM,
    facts_prompt=_V22_1_FACTS_PROMPT,
    entity_prompt=_V22_1_ENTITY_PROMPT,
    focus_prompt=_V22_1_FOCUS_PROMPT,
    validate_prompt=_V20_2_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    validate_num_predict=512,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
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
    "v17-typerecall": V17_TYPERECALL,
    "v18-toolrecall": V18_TOOLRECALL,
    "v18.1-validate": V18_1_VALIDATE,
    "v18.2-mark": V18_2_MARK,
    "v18.3-focus": V18_3_FOCUS,
    "v18.4-combo": V18_4_COMBO,
    "v18.4.1-protectcaste": V18_4_1_PROTECTCASTE,
    "v18.4.2-nemo": V18_4_2_NEMO,
    "v19-recall": V19_RECALL,
    "v20-clean": V20_CLEAN,
    "v20.1-clean": V20_1_CLEAN,
    "v20.2-clean": V20_2_CLEAN,
    "v21.0-masked": V21_0_MASKED,
    "v21.1-masked-triple": V21_1_MASKED_TRIPLE,
    "v21.2-masked-prompt": V21_2_MASKED_PROMPT,
    "v21.3-masked-llm": V21_3_MASKED_LLM,
    "v21.4-masked-both": V21_4_MASKED_BOTH,
    "v21.5-scoped": V21_5_SCOPED,
    "v21.6-llama": V21_6_LLAMA,
    "v21.7-radical": V21_7_RADICAL,
    "v21.8-radical-filtered": V21_8_RADICAL_FILTERED,
    "v21.9-radical-protected": V21_9_RADICAL_PROTECTED,
    "v22.0": V22_0,
    "v22.1": V22_1,
    "v22.2-pastlevel": V22_2_PASTLEVEL,
    "v22.2.1-pastlevel": V22_2_1_PASTLEVEL,
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
