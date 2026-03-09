"""v14-certainty and variants: inline certainty score replaces validation pass.

The LLM self-assesses each entity with a certainty score in the SAME call.
No separate validation pass needed — filter by threshold in code.
Scale is configurable: (1,3) for small models, (1,10) for larger ones.

Helper functions generate scale-aware prompt fragments.
Also includes Mistral Nemo-specific prompts for v14.
"""

from .base import ExtractionVersion


# ---------------------------------------------------------------------------
# Helper functions — build scale-aware prompt fragments.
# All helpers are generic — they adapt to any (min, max) scale.
# ---------------------------------------------------------------------------

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

_VERSIONS_V14: dict[str, ExtractionVersion] = {
    "v14-certainty": V14_CERTAINTY,
    "v14-certainty-5": V14_CERTAINTY_5,
    "v14-certainty-pct": V14_CERTAINTY_PCT,
    "v14-blind": V14_BLIND,
    "v14-blind-10": V14_BLIND_10,
    "v14-certainty-10": V14_CERTAINTY_10,
    "v14-nemo-pct": V14_NEMO_PCT,
}
