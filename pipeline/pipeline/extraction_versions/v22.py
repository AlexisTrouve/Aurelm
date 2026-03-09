"""v22 extraction versions: rituels/architecture/events support."""
from .base import ExtractionVersion
from .v20 import _V22_FACTS_PROMPT, _V20_2_VALIDATE_PROMPT, _V20_3_VALIDATE_PROMPT, _V20_4_VALIDATE_PROMPT

# ---------------------------------------------------------------------------
# v22.0 prompts: adds explicit guidance for rituels/rites/architecture.
# Root insight: pipeline consistently misses ritual practices and architectural
# elements because prompts focus on weapons/institutions.
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

# ---------------------------------------------------------------------------
# Version definitions
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

# v22.2.1-no-validate: same as v22.2.1-pastlevel but with validate disabled.
# Used for A/B comparison to isolate the effect of the validate pass.
V22_2_1_NO_VALIDATE = ExtractionVersion(
    name="v22.2.1-no-validate",
    description="v22.2.1-pastlevel sans validate — pour comparaison A/B.",
    system_prompt=_V22_2_1_SYSTEM,
    facts_prompt=_V22_2_1_FACTS_PROMPT,
    entity_prompt=_V22_2_1_ENTITY_PROMPT,
    focus_prompt=_V22_2_1_FOCUS_PROMPT,
    validate_prompt=None,
    validate_model=None,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
)

# v22.2.2-pastlevel: uses v20.4 validate prompt (best on T1-T8 benchmark, F1=73.8%).
# Fixes 2 FN from v22.2.1: Oracle [civilization] and Voix des cieux [belief]
# incorrectly dropped. Adds [civilization]/[belief] absolute protection while
# restoring "pas un groupe social" exclusion (prevents "enfants du courant" regression).
V22_2_2_PASTLEVEL = ExtractionVersion(
    name="v22.2.2-pastlevel",
    description=(
        "v22.2.1-pastlevel + type-aware validate (v20.4, F1=73.8% on T1-T8). "
        "Absolute protection for [civilization] and [belief] labels + "
        "'pas un groupe social' exclusion — best validate prompt as of 2026-03-08."
    ),
    system_prompt=_V22_2_1_SYSTEM,
    facts_prompt=_V22_2_1_FACTS_PROMPT,
    entity_prompt=_V22_2_1_ENTITY_PROMPT,
    focus_prompt=_V22_2_1_FOCUS_PROMPT,
    validate_prompt=_V20_4_VALIDATE_PROMPT,
    validate_model="qwen3:14b",
    chunk_by_paragraph=True,
    max_chunk_words=800,
    mask_passes=1,
)

_VERSIONS_V22: dict[str, ExtractionVersion] = {
    "v22.0": V22_0,
    "v22.1": V22_1,
    "v22.2-pastlevel": V22_2_PASTLEVEL,
    "v22.2.1-pastlevel": V22_2_1_PASTLEVEL,
    "v22.2.1-no-validate": V22_2_1_NO_VALIDATE,
    "v22.2.2-pastlevel": V22_2_2_PASTLEVEL,
}
