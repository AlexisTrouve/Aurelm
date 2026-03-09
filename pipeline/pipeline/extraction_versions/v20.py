"""v20-clean, v20.1-clean, v20.2-clean: generic prompts (no game-specific entity names).

Root cause of contamination in v18/v19: OUI lists contained hardcoded entity names
from the game (Cheveux de Sang, Gorge Profonde, Hall des Serments, etc.) which caused
the LLM to hallucinate those entities even when absent from text.

Approach:
  - Extraction prompts: TYPE-based guidance only, no specific entity names
  - Focus prompt: describes caste/institution STRUCTURE, not specific names
  - Validate: adds text-presence rule
  - Same 4-call architecture as v18.4.2-nemo

IMPORTANT: _V22_FACTS_PROMPT is defined here (not in v22.py) to resolve a
circular import — v22.py imports from v20.py.
_V20_FACTS_PROMPT is an alias for _V22_FACTS_PROMPT (v22 prompt is a superset
with added OUI lines for rituels/architecture, but the alias is safe for v20 usage).
"""

from .base import ExtractionVersion
from .v18 import _V18_SYSTEM

# ---------------------------------------------------------------------------
# _V22_FACTS_PROMPT is defined HERE to avoid circular import.
# v22.py imports _V22_FACTS_PROMPT from .v20, not the other way around.
# This prompt was added in the v22 family and also aliased as _V20_FACTS_PROMPT.
# ---------------------------------------------------------------------------
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

# v20-clean: generic prompts, validate adds text-presence rule
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
# v20.1-clean: v20-clean + redesigned nemo validate prompt.
# Positive framing (GARDE by default), type protections first,
# few-shot examples covering technology/caste/institution cases.
# validate_num_predict=256 (validate responses are ~100 chars).
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
# v20.2-clean: v20.1 + per-entity reasoning in nemo validate.
# Output format: {"keep": [...], "drops": "name: reason | name2: reason2"}.
# validate_num_predict bumped to 512 to fit ~15 entries with reasons.
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

# v20.3: type-aware protection — [civilization] and [belief] are NEVER droppable.
# Fixes 2 FN from v20.2: Oracle [civilization] was dropped as "mot generique",
# Voix des cieux [belief] was dropped as "metaphore poetique". Both are legit.
# Rule: single generic word still droppable BUT not if type is civilization/belief.
# Doublon rule still applies (fragment of longer entity in same list).
_V20_3_VALIDATE_PROMPT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

REGLE : GARDE tout par defaut.

PROTECTION ABSOLUE — ne jamais supprimer :
- Toute entite labelisee [civilization] : nom de civilisation ou faction, pas un mot ordinaire
- Toute entite labelisee [belief] : croyance etablie dans le jeu, pas une metaphore

SUPPRIME seulement si c'est clairement l'un de ces cas :
- Mot commun francais dont le sens est trop vague pour identifier quoi que ce soit de precis dans ce jeu (ex: "enfants", "ancetres", "chasseur", "defunts")
- Doublon exact ou fragment d'une autre entite plus complete de la meme liste (ex: "Cercle" quand "Cercle des sages" est aussi present)

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec ce format JSON :
- "keep" : noms exacts des entites gardees (copies depuis la liste ci-dessus)
- "drops" : pour chaque entite supprimee, ecrire "nom exact: raison textuelle courte" separes par " | "

{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison textuelle | Nom2 supprime: raison textuelle"}}"""

# v20.4: combines v20.3 type-protection with v20.2's "pas un groupe social" exclusion.
# v20.3 regression: removing "pas un groupe social" caused "enfants du courant [caste]"
# to be dropped — it's a 3-word social group, not a simple generic word.
# Result on T1-T8 benchmark: F1=73.8% (vs v20.2=69.6%, v20.3=71.9%)
_V20_4_VALIDATE_PROMPT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

REGLE : GARDE tout par defaut.

PROTECTION ABSOLUE — ne jamais supprimer :
- Toute entite labelisee [civilization] : nom de civilisation ou faction, pas un mot ordinaire
- Toute entite labelisee [belief] : croyance etablie dans le jeu, pas une metaphore

SUPPRIME seulement si c'est clairement l'un de ces cas :
- Metaphore poetique sans referent concret dans le texte
- Un seul mot generique commun (pas un nom propre, pas un outil, pas un groupe social)
- Doublon exact ou fragment d'une autre entite plus complete de la meme liste (ex: "Cercle" quand "Cercle des sages" est aussi present)

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

_VERSIONS_V20: dict[str, ExtractionVersion] = {
    "v20-clean": V20_CLEAN,
    "v20.1-clean": V20_1_CLEAN,
    "v20.2-clean": V20_2_CLEAN,
}
