"""v21.0 through v21.9: masked extraction passes.

After first-pass dedup, replaces found entity names with _____ in the chunk text
and runs extra entity-only LLM calls. Forces the LLM to look at what remains
when dominant entities are hidden — improves recall for techs/beliefs/creatures.
"""

from .base import ExtractionVersion
from .v18 import _V18_SYSTEM
from .v20 import _V20_FACTS_PROMPT, _V20_ENTITY_PROMPT, _V20_FOCUS_PROMPT, _V20_2_VALIDATE_PROMPT

# v21.0-masked: v20.2-clean + masked second-pass extraction (mask_and_retry=True)
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

# v21.1-masked-triple: 2 sequential masked passes (triple-pass total)
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

# v21.2-masked-prompt: 1 masked pass with a targeted prompt
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

# v21.3-masked-llm: 1 masked pass with a higher-precision model
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

# v21.4-masked-both: 1 masked pass with targeted prompt + high-precision model
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

# v21.6-llama: 2 masked passes using llama3.1:8b as the mask-pass model
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
# Frames the task as completing an archaeologist's catalog — drops the
# proper-noun requirement and biases toward exhaustiveness.
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

# v21.8-radical-filtered: v21.7 + explicit N'EXTRAIS PAS list for abstract concepts
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

# v21.9-radical-protected: v21.8 + validate prompt protects concrete tools/weapons
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

_VERSIONS_V21: dict[str, ExtractionVersion] = {
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
}
