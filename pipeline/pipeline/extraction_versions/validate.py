"""Validate prompt versions — for benchmark_validate.py.

Each entry in VALIDATE_VERSIONS: (prompt_str, description).
prompt_str uses {text} and {entities} placeholders.
All prompts expect JSON response: {"keep": [...], "drops": "name: reason | ..."}
"""
from .v20 import _V20_2_VALIDATE_PROMPT, _V20_3_VALIDATE_PROMPT, _V20_4_VALIDATE_PROMPT

# v1-current: the prompt currently in v22.2.1-pastlevel (baseline for comparison).
# Problem: only catches single generic words and exact duplicates.
# Keeps multi-word generics like "Piete filiale", "Village temporaire", "Outils et armes".
_VP_V1_CURRENT = _V20_2_VALIDATE_PROMPT

# v2-strict: adds a rule for generic multi-word noun phrases (no proper noun status).
# Targets: "Piete filiale", "Techniques de chasses", "Outils et armes", "Lieu de vie".
_VP_V2_STRICT = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

REGLE : GARDE tout par defaut.
SUPPRIME seulement si c'est clairement l'un de ces cas :
1. Metaphore poetique sans referent concret dans le texte
2. Un seul mot generique commun (pas un nom propre) : "feu", "ciel", "riviere", "sagesse", "mort"
3. Syntagme generique sans nom propre ni identite distincte dans le texte :
   ex: "lieu de vie", "techniques de chasse", "outils et armes", "village temporaire",
       "respect aux defunts", "piete filiale", "fumage d'un feu", "animaux de la region"
4. Concept abstrait sans denomination propre dans le texte : "croyance" seul, "religion" seul
5. Doublon exact d'une autre entite de la liste

GARDE toujours : noms propres composes, castes, institutions, technologies nommees, civilisations,
personnages, lieux specifiques (meme descriptifs), croyances avec nom propre.

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec ce format JSON :
{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison courte | Nom2: raison"}}"""

# v3-type-aware: rules tailored per entity type.
# A [technology] is never generic (tools/techniques are valid tech entities).
# A [caste] or [person] is never dropped regardless of name form.
# Aggressive only on [belief], [place], [resource] that are clearly generic.
_VP_V3_TYPE_AWARE = """Tu filtres une liste d'entites nommees extraites d'un texte de jeu de role.
Reponds UNIQUEMENT avec du JSON valide.

REGLE : GARDE tout par defaut.

Par type :
- [person], [caste], [civilization], [creature] : GARDE TOUJOURS, sans exception.
- [institution] : GARDE sauf si c'est un doublon exact d'une autre entite.
- [technology] : GARDE sauf si c'est un syntagme 100% generique sans nom propre (ex: "outils").
- [event] : GARDE si un NOM PROPRE apparait litteralement dans le texte. SUPPRIME si c'est une description generique.
- [place] : GARDE les lieux specifiques. SUPPRIME si 100% generique : "lieu de vie", "village", "territoire".
- [belief] : GARDE si nom propre ou denomination specifique. SUPPRIME si mot commun seul : "croyance", "sagesse".
- [resource] : GARDE si ressource nommee. SUPPRIME si trop generique : "animaux", "plantes", "nourriture".

SUPPRIME aussi : metaphores poetiques, doublons exacts.

Texte de reference :
{text}

Entites a valider :
{entities}

Reponds avec ce format JSON :
{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison courte | Nom2: raison"}}"""

# v4-no-text: validate without providing the reference text.
# Tests if the entity list alone is enough for filtering (cheaper, no text in prompt).
_VP_V4_NO_TEXT = """Tu filtres une liste d'entites nommees extraites d'un jeu de role de civilisation.
Reponds UNIQUEMENT avec du JSON valide.

GARDE tout par defaut.
SUPPRIME seulement :
1. Mot generique seul sans statut de nom propre : "sagesse", "mort", "ciel", "croyance", "feu"
2. Syntagme generique commun sans identite dans le jeu : "lieu de vie", "techniques de chasse",
   "outils et armes", "respect aux defunts", "piete filiale", "village temporaire"
3. Metaphore poetique : "fleuve du temps", "bras de la mort"
4. Doublon exact d'une autre entite

GARDE toujours : noms propres, castes, institutions, technologies nommees, personnages, civilisations.

Entites a valider :
{entities}

Reponds avec ce format JSON :
{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison courte | Nom2: raison"}}"""


# v5-positive: framing positif — selectionne ce qui merite une fiche dans un lexique du jeu.
# Default = exclusion. Le modele doit justifier d'inclure, pas d'exclure.
# Rationale : les modeles suivent mieux un critere d'inclusion positif qu'une liste d'exclusions.
# Nemo en particulier est "helpful/compliant" — en mode selection positive il applique le critere.
_VP_V5_POSITIVE = """Tu selectionnes les vraies entites nommees d'un jeu de civilisation.

Parmi la liste ci-dessous, retiens UNIQUEMENT les entites qui meritent une fiche dans un lexique du jeu —
c'est-a-dire qui ont une identite propre et distincte dans le monde fictif.

INCLUS si c'est clairement l'un de ces cas :
- Nom propre d'une institution, organisation ou groupe social nomme (pas un role generique)
- Technologie, outil ou technique avec un nom specifique dans le texte
- Lieu precis avec un nom propre (pas "la vallee", "la foret" generiques)
- Personnage, caste, civilisation ou creature avec une denomination propre
- Croyance ou evenement portant un nom propre litteral dans le texte

EXCLUS tout le reste — roles generiques (meres, enfants, defunts), concepts abstraits (sagesse,
croyance seul), pratiques sans denomination propre (rituel funeraire, piete filiale),
syntagmes descriptifs (lieu de vie, techniques de chasse, outils et armes).
En cas de doute : n'inclus pas.

Texte de reference :
{text}

Entites a evaluer :
{entities}

Reponds avec ce format JSON :
{{"keep": ["Nom1", "Nom2"], "drops": "Nom supprime: raison courte | Nom2: raison"}}"""


# v5.1-generics: identifie uniquement les generiques a supprimer.
# Inverse de v5 : le modele cherche activement ce qui est generique,
# on garde tout ce qui n'est pas dans sa liste DROP.
# Avantage : tache plus facile pour le modele (identifier le bruit est plus intuitif
# que selectionner les bons) — et on beneficie du biais "helpful" de nemo dans l'autre sens.
_VP_V5_1_GENERICS = """Tu identifies les termes generiques dans une liste d'entites extraites d'un jeu.

Reponds UNIQUEMENT avec du JSON valide.

Examine chaque entite et mets dans "drops" celles qui sont CLAIREMENT generiques :
- Roles sociaux communs sans denomination propre : meres, enfants, defunts, parents, anciens
- Concepts abstraits sans nom propre : sagesse, croyance seul, piete, respect
- Pratiques culturelles generiques sans nom : rituel funeraire, techniques de chasse, fumage
- Lieux descriptifs sans nom propre : lieu de vie, village temporaire, la vallee, la foret
- Activites ou outils trop vagues : outils et armes, art de la chasse, expeditions de chasse
- Doublons evidents d'une autre entite dans la liste

Tout ce qui n'est pas dans "drops" est considere garde.
En cas de doute : ne mets pas dans drops.

Texte de reference :
{text}

Entites :
{entities}

Reponds avec ce format JSON :
{{"drops": "Nom supprime: raison courte | Nom2: raison"}}"""


# v6-cautious: ultra-conservateur — le MJ a besoin de ces entites, chaque FN est une perte
# permanente d'information. Le modele doit justifier chaque suppression et n'est autorise
# a dropper QUE les cas 100% certains. Default = GARDE absolu.
# Rationale : les FN sont bien pires que les FP. Un FP se filtre ensuite ; un FN est perdu.
_VP_V6_CAUTIOUS = """Tu assistes un maitre de jeu (MJ) qui a besoin de retrouver des entites
importantes dans ses notes de jeu. Si tu supprimes une vraie entite du jeu, le MJ perd
definitivement cette information. C'est tres grave. Les faux positifs sont acceptables ;
les faux negatifs ne le sont pas.

REGLE ABSOLUE : par defaut, GARDE tout. Ne supprime une entite que si tu peux ecrire
une justification claire ET que tu es certain a 100% qu'elle n'a aucune valeur pour le jeu.

Pour chaque entite que tu envisages de supprimer, demande-toi :
"Est-il possible que le MJ veuille retrouver cette information plus tard ?"
Si OUI ou PEUT-ETRE -> garde obligatoirement.
Si NON avec certitude absolue -> tu peux la mettre dans drops.

Seuls cas autorises pour suppression (certitude absolue requise) :
- Mot francais banal sans aucune specificite de jeu : "sagesse", "parents", "enfants", "defunts"
- Doublon exact ou quasi-exact d'une autre entite dans la liste

Tout le reste : GARDE. Les noms composes, les objets, les lieux, les pratiques culturelles,
les creatures, les techniques — meme s'ils semblent generiques — GARDE-LES.
Le MJ sait ce qui est important dans son jeu, pas toi.

Texte de reference :
{text}

Entites a evaluer :
{entities}

Reponds avec ce format JSON :
{{"drops": "Nom supprime: justification precise pourquoi c'est 100% certain | Nom2: justification"}}"""


# v7-paranoid: nemo ultra-careful. Deux regles SEULEMENT, aucune autre.
# Regle 1 : tout terme avec 2+ mots ou un tiret = GARDE ABSOLU, pas de discussion.
# Regle 2 : mot unique banal du dictionnaire francais courant = peut drop.
# Tout le reste = GARDE. Zero interpretation, zero jugement de valeur.
# Rationale : les FN comme "larmes du ciel", "morsure-des-ancetres", "rituels de fertilite"
# sont droppes parce que le modele juge qu'ils sont "generiques". Avec cette regle,
# ils sont proteges automatiquement par la longueur/tiret.
_VP_V7_PARANOID = """Tu es un assistant de filtrage pour un jeu de role. Ta mission :
eliminer UNIQUEMENT les parasites evidents d'une liste d'entites extraites.

REGLES (deux seulement, dans cet ordre) :

REGLE 1 — INTOUCHABLE : Toute entite contenant un tiret OU composee de 2 mots ou plus
est INTOUCHABLE. Tu ne peux pas la supprimer, quoi qu'il arrive.
Exemples intouchables : "larmes du ciel", "rituel funeraire", "morsure-des-ancetres",
"techniques de chasse", "piete filiale", "village temporaire", "enfants du courant".
PEU IMPORTE si ca semble generique — c'est INTOUCHABLE.

REGLE 2 — SUPPRIMABLE : Un mot unique (un seul mot, sans tiret) peut etre supprime
UNIQUEMENT s'il est un mot courant du dictionnaire francais sans valeur specifique au jeu.
Exemples supprimables : "sagesse", "parents", "enfants", "defunts", "croyance", "meres".
Exemples NON supprimables meme en un mot : "Memento", "Oracle", "Shamans", "Confluence"
(car ils ont une valeur potentielle dans le jeu).

En cas de doute sur la regle 2 : GARDE.

Texte de reference :
{text}

Entites :
{entities}

Reponds avec ce format JSON :
{{"drops": "Nom: raison | Nom2: raison"}}
Si rien a supprimer : {{"drops": ""}}"""


# v7.1-hesitant: nemo en mode hesitation maximale.
# Framing : supprimer est une erreur catastrophique, ne rien supprimer est la reponse normale.
# Le modele doit douter de lui-meme avant chaque suppression.
_VP_V7_1_HESITANT = """Tu examines une liste d'entites extraites d'un jeu de role.

IMPORTANT : il est tout a fait possible — et meme probable — qu'aucune entite de cette liste
ne soit a supprimer. Une liste vide en reponse est une reponse correcte et attendue.

Supprimer une vraie entite du jeu est une CATASTROPHE IRREVERSIBLE pour le maitre de jeu.
Ne pas supprimer un terme generique est juste un petit desordre, facilement corrige apres.
Donc : dans le doute, ne supprime rien. Le doute = garde.

Tu peux envisager de supprimer uniquement si les TROIS conditions sont vraies simultanement :
1. C'est un mot unique (un seul mot, pas de tiret, pas d'espace)
2. C'est un mot du dictionnaire francais courant, banal, sans majuscule
3. Tu es certain a 100%, sans aucun doute, que ce mot n'a aucun sens dans ce jeu

Si l'une des trois conditions n'est pas remplie : ne supprime pas.
Si tu hesites sur l'une des trois : ne supprime pas.
Peut-etre que rien ne remplit ces trois conditions — c'est normal, retourne une liste vide.

Texte de reference :
{text}

Entites :
{entities}

Reponds avec ce format JSON :
{{"drops": "Nom: raison | Nom2: raison"}}
Si rien a supprimer (reponse normale) : {{"drops": ""}}"""


# v8-fewshot: exemples annotes des cas limites. Basé sur v7-paranoid mais avec
# des exemples concrets de ce qu'il FAUT garder (nos FN récurrents) et ce qu'il
# peut dropper. La recherche montre que les exemples edge-case sont le levier le
# plus fort pour les petits modèles sur les tâches de classification.
_VP_V8_FEWSHOT = """Tu filtres une liste d'entites d'un jeu de role de civilisation.
Par defaut : GARDE TOUT. Ne supprime que si c'est un mot banal isolé, sans valeur de jeu.

EXEMPLES — ce qu'il faut GARDER (meme si ca semble generique) :
- "rituels de fertilite" [belief] → GARDE : pratique culturelle nommee de cette civ
- "culte des ancetres" [belief] → GARDE : systeme de croyance propre au jeu
- "larmes du ciel" [resource] → GARDE : ressource ou concept nomme dans le jeu
- "morsure-des-ancetres" [technology] → GARDE : nom propre technique avec tiret
- "paniers immerges" [technology] → GARDE : objet technique specifique
- "rhombes en pierre" [technology] → GARDE : instrument specifique a cette civilisation
- "enfants des nuages" [caste] → GARDE : groupe social nomme de la civilisation
- "piete filiale" [belief] → GARDE : concept culturel meme si d'apparence generique

EXEMPLES — ce qui peut etre supprime :
- "sagesse" [belief] → SUPPRIME : mot banal isolé, concept abstrait generique
- "parents" [person] → SUPPRIME : role social generique, un seul mot banal
- "defunts" [person] → SUPPRIME : mot banal isolé, aucune specificite de jeu
- "enfants" [person] → SUPPRIME : mot banal isolé (different de "enfants des nuages")
- "croyance" [belief] → SUPPRIME : mot banal isolé, trop vague

REGLE ABSOLUE : tout terme avec tiret ou 2+ mots est INTOUCHABLE.
En cas de doute : GARDE.

Texte de reference :
{text}

Entites a evaluer :
{entities}

Reponds avec ce format JSON :
{{"drops": "Nom: raison | Nom2: raison"}}
Si rien a supprimer : {{"drops": ""}}"""


# Registry: name -> (prompt, description)
VALIDATE_VERSIONS: dict[str, tuple[str, str]] = {
    "v1-current": (
        _VP_V1_CURRENT,
        "Prompt actuel de v22.2.1 (baseline). Filtre: metaphores, mots generiques seuls, doublons. "
        "Probleme: garde les syntagmes generiques multi-mots (Piete filiale, Village temporaire...).",
    ),
    "v2-strict": (
        _VP_V2_STRICT,
        "v1 + regle explicite sur les syntagmes generiques sans nom propre. "
        "Cible: Lieu de vie, Techniques de chasses, Outils et armes, Piete filiale.",
    ),
    "v3-type-aware": (
        _VP_V3_TYPE_AWARE,
        "Regles par type d'entite: [caste]/[person]/[institution] immunises, "
        "[belief]/[place]/[resource] filtres si generiques, [technology] conservateur.",
    ),
    "v4-no-text": (
        _VP_V4_NO_TEXT,
        "Sans texte de reference (liste seule). Plus rapide, teste si le contexte textuel "
        "est necessaire pour filtrer. Syntagmes generiques explicitement listes.",
    ),
    "v5-positive": (
        _VP_V5_POSITIVE,
        "Framing positif : selectionne UNIQUEMENT ce qui merite une fiche dans un lexique du jeu. "
        "Default = exclusion. Inverse la charge cognitive vs v1-v4 (justifie d'inclure, pas d'exclure).",
    ),
    "v5.1-generics": (
        _VP_V5_1_GENERICS,
        "Identifie uniquement les generiques a supprimer (liste DROP). "
        "Inverse de v5 : le modele cherche activement les termes generiques, "
        "on garde tout ce qui n'est pas dans la liste DROP.",
    ),
    "v6-cautious": (
        _VP_V6_CAUTIOUS,
        "Ultra-conservateur : le MJ a besoin de ces entites, chaque FN est une perte permanente. "
        "Default=GARDE absolu. Ne supprime que si certitude 100% + justification. "
        "Seuls cas autorises : mots banals (sagesse, parents, enfants) et doublons exacts.",
    ),
    "v7-paranoid": (
        _VP_V7_PARANOID,
        "Nemo ultra-careful. 2 regles seulement : (1) tout terme 2+ mots ou avec tiret = INTOUCHABLE "
        "(protege larmes du ciel, morsure-des-ancetres, etc.), (2) mot unique banal = supprimable. "
        "Zero interpretation, zero jugement de valeur.",
    ),
    "v8-fewshot": (
        _VP_V8_FEWSHOT,
        "Few-shot exemples annotes des cas limites : nos FN recurrents explicitement marques GARDE, "
        "nos FP types marques SUPPRIME. Regle intouchable 2+mots/tiret conservee.",
    ),
    "v7.1-hesitant": (
        _VP_V7_1_HESITANT,
        "Nemo en mode hesitant : probablement rien a supprimer, supprimer est une catastrophe, "
        "mieux vaut ne rien faire. Vide = reponse normale et acceptable. "
        "Seul cas autorise : mot unique evidentment banal SANS aucun doute possible.",
    ),
    "v9-type-safe": (
        _V20_3_VALIDATE_PROMPT,
        "v1 + PROTECTION ABSOLUE pour [civilization] et [belief] — jamais supprimables. "
        "Fixe 2 FN de v1: Oracle [civilization] et Voix des cieux [belief] incorrectement droppes. "
        "Regle drop simplifiee: mot commun vague OU fragment/doublon d'une entite plus complete.",
    ),
    "v10-best": (
        _V20_4_VALIDATE_PROMPT,
        "v9 + restaure l'exception 'groupe social' pour les mots simples. "
        "Fixe la regression v9: enfants du courant [caste] (groupe social) etait droppe. "
        "Regles combinées: type-protection absolue [civilization/belief] + "
        "word drop exclusions (pas nom propre, pas outil, pas groupe social).",
    ),
}
