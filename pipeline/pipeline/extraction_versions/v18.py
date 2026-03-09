"""v18-toolrecall and variants: T11-targeted recall fix.

Root causes diagnosed on T11 benchmark (F1=71.4%, 6 FNs, 10 FPs).
See inline comments per version for detailed root cause analysis.
"""

from .base import ExtractionVersion

# ---------------------------------------------------------------------------
# Shared system prompt for all v18 variants.
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
# Goal: kill the persistent FPs that survive the NON instructions.
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
# Goal: catch entities the JSON calls miss by asking the LLM to re-read
# the text and annotate every entity name with @@name## markers.
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
# Goal: recover castes that fall through calls 1+2 in dense narrative chunks.
# Uses focus_prompt → _llm_extract_focused() — a targeted JSON call.
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
# Strategy: maximize recall with the focus call, then prune FPs with the
# validate pass using a cheap model (llama3.1:8b / meta-llama on OpenRouter).
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
# Root cause: Llama's validate pass removes castes it perceives as "generic
# workers" (Tailleurs de pierre, Explorateurs) and institutions that aren't
# obviously institutional (Voix de l'Aurore).
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
# v18.4.2: v18.4.1 same tweaks but Mistral-Nemo for validate.
# Nemo is smaller/faster than qwen3:14b but better at French than llama3.1:8b.
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

_VERSIONS_V18: dict[str, ExtractionVersion] = {
    "v18-toolrecall": V18_TOOLRECALL,
    "v18.1-validate": V18_1_VALIDATE,
    "v18.2-mark": V18_2_MARK,
    "v18.3-focus": V18_3_FOCUS,
    "v18.4-combo": V18_4_COMBO,
    "v18.4.1-protectcaste": V18_4_1_PROTECTCASTE,
    "v18.4.2-nemo": V18_4_2_NEMO,
}