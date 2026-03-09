"""v13-validate, v13.1-validate, v13.2-validate:

v13: v11 extraction + LLM validation pass post-extraction.
v13.1: same extraction, heavier validation prompt targeting 5 remaining FP patterns.
v13.2: v13.1 + less aggressive validation — emphasizes KEEP on doubt.
"""

from .base import ExtractionVersion
from .v11 import _V11_SYSTEM_QWEN, _V11_SYSTEM_LLAMA, _V11_FACTS_PROMPT, _V11_ENTITY_PROMPT

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


# v13.1: same extraction, heavier validation with explicit examples of remaining FP patterns
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


# v13.2: v13.1 but validation less aggressive.
# v13.1 was killing TPs (Proclamateurs, Regards-Libres, Arbitre des Esprits).
# Cause: REJECT rules too strong vs "in case of doubt KEEP".
# Fix: insist MUCH more on "KEEP on doubt", reduce REJECT rules.
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

_VERSIONS_V13: dict[str, ExtractionVersion] = {
    "v13-validate": V13_VALIDATE,
    "v13.1-validate": V13_1_VALIDATE,
    "v13.2-validate": V13_2_VALIDATE,
}
