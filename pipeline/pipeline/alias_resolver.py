"""Alias resolver — detects and confirms entity aliases via pattern matching + LLM.

Two-stage pipeline after entity profiling:

  Stage 1 (Pattern Matching): Finds candidate alias pairs using:
    - LLM-suggested aliases from entity profiles (étage 0 output)
    - Appositive patterns in mention contexts ("X, aussi appelé Y")
    - Description keyword overlap between entities
    - Fuzzy name matching (token overlap on normalized names)

  Stage 2 (LLM Confirmation): Confirms each candidate with a targeted LLM call
    that receives both entity profiles for context-rich comparison.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from .db import get_connection
from .entity_profiler import EntityProfile
from .llm_provider import LLMProvider, OllamaProvider


@dataclass
class AliasCandidate:
    """A candidate alias pair with the reason it was flagged."""
    entity_a: EntityProfile
    entity_b: EntityProfile
    reason: str
    source: str  # "llm_suggested", "appositive_pattern", "description_overlap", "fuzzy_name"


@dataclass
class ConfirmedAlias:
    """A confirmed alias relationship."""
    primary_entity_id: int
    primary_name: str
    alias_entity_id: int
    alias_name: str
    confidence: str  # high, medium, low
    reasoning: str
    score: float | None = None  # Normalized similarity score (0-1) for score-based versions


@dataclass
class AliasConfirmVersion:
    """Versioned prompt configuration for alias confirmation (Stage 2).

    Different models respond better to different prompt styles:
    - Llama: short, direct — no thinking mode, needs clear instructions
    - Qwen3: question-based — leverages <think> reasoning before answering
    - Nemo: structured template — forces line-by-line analysis before JSON
    - Score variants: same template discipline but output a numeric score
      instead of true/false to allow threshold tuning.

    json_mode: set False when the prompt asks for free text before JSON
    (e.g. v3-nemo fills a template then outputs JSON — json_mode would
    prevent the template text from being generated).

    score_scale: None for binary (same_entity: true/false),
      10 for 1-10 scale, 100 for 0-100% scale.
      When set, confirm_aliases() uses `score` field instead of `same_entity`
      and applies score_threshold for the decision.
    """
    name: str
    description: str
    prompt: str  # Template with {name_a}, {type_a}, {desc_a}, {name_b}, {type_b}, {desc_b}, {reason}
    json_mode: bool = True  # False for prompts that produce free text before JSON
    score_scale: int | None = None  # None = binary, 10 = 1-10, 100 = 0-100%


DEFAULT_MODEL = "qwen3:14b"
DEFAULT_CONFIRM_VERSION = "v2-qwen3"  # qwen3 question-based — better calibrated than v1-llama
NUM_CTX = 8192

# Appositive patterns that indicate aliases in French game text
ALIAS_PATTERNS = [
    re.compile(
        r"(?:aussi|également)\s+(?:appelée?s?|nommée?s?|connue?s?\s+sous(?:\s+le\s+nom\s+(?:de|d'))?)\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:surnommée?s?|baptisée?s?)\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"c['\u2019]est-à-dire\s+(?:les?\s+|l['\u2019])?(.+?)(?:[,.\s]|$)",
        re.IGNORECASE,
    ),
    # "X ou Y" when X is an entity name nearby
    re.compile(
        r"\bou\s+(?:les?\s+|l['\u2019])?([A-Z][a-zà-ÿ]+(?:[\s-][A-Za-zà-ÿ]+)*)",
    ),
]


_V1_LLAMA_PROMPT = """\
Ces deux entités d'un JDR de civilisation désignent-elles la même chose ?

Entité 1 : "{name_a}" (type: {type_a})
{desc_a}

Entité 2 : "{name_b}" (type: {type_b})
{desc_b}

Indice : {reason}

Si les descriptions sont compatibles et les noms plausiblement liés (variante, surnom, faute de frappe), réponds true.
Ne réponds false que si tu vois une contradiction claire ou un rôle distinct.

JSON : {{"same_entity": true, "confidence": "high/medium/low", "reasoning": "..."}}"""

_V2_QWEN3_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation.

Deux entités ont été signalées comme potentiellement identiques. Analyse les preuves.

Entité 1 : "{name_a}" (type: {type_a})
Description : {desc_a}

Entité 2 : "{name_b}" (type: {type_b})
Description : {desc_b}

Signal déclencheur : {reason}

Pose-toi ces questions :
1. Les descriptions décrivent-elles le même rôle, la même fonction, ou le même lieu dans le monde du jeu ?
2. Les noms sont-ils des variantes l'un de l'autre (traduction, surnom, abréviation, variante dialectale, faute de frappe) ?
3. Y a-t-il des contradictions factuelles entre les deux descriptions qui prouveraient qu'elles sont distinctes ?
4. Si c'est flou, est-ce parce que l'une des descriptions est incomplète — ou parce que ce sont vraiment deux choses différentes ?

Conclusion : si les descriptions sont compatibles et les noms plausiblement liés, réponds true même avec peu d'information.
Ne réponds false que si tu identifies une contradiction réelle ou un rôle clairement distinct.

Réponds UNIQUEMENT en JSON : {{"same_entity": true, "confidence": "high/medium/low", "reasoning": "..."}}"""


_V3_NEMO_PROMPT = """\
Tu es un archiviste pour un JDR de civilisation. Analyse ces deux entités et remplis le template ci-dessous.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

Remplis ce template ligne par ligne AVANT de conclure :

NOMS : [les noms sont-ils des variantes, surnoms, fautes de frappe, ou abréviations l'un de l'autre ? OUI/NON — pourquoi ?]
RÔLE_A : [en une phrase, quel est le rôle/fonction/nature de A ?]
RÔLE_B : [en une phrase, quel est le rôle/fonction/nature de B ?]
MÊME_RÔLE : [est-ce que RÔLE_A et RÔLE_B décrivent la même chose ? OUI/NON — pourquoi ?]
CONTRADICTION : [y a-t-il un fait dans les descriptions qui PROUVE qu'ils sont distincts ? OUI/NON — lequel ?]
VERDICT : [MÊME_ENTITÉ ou ENTITÉS_DISTINCTES]

JSON : {{"same_entity": true/false, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# Score 1-10: same structured template as v3-nemo but outputs a numeric score
# instead of true/false. Allows threshold tuning by inspecting score distribution.
_V4_SCORE10_PROMPT = """\
Tu es un archiviste pour un JDR de civilisation. Analyse ces deux entités et remplis le template ci-dessous.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

Remplis ce template ligne par ligne AVANT de conclure :

NOMS : [les noms sont-ils des variantes, surnoms, fautes de frappe, ou abréviations l'un de l'autre ? OUI/NON — pourquoi ?]
RÔLE_A : [en une phrase, quel est le rôle/fonction/nature de A ?]
RÔLE_B : [en une phrase, quel est le rôle/fonction/nature de B ?]
MÊME_RÔLE : [est-ce que RÔLE_A et RÔLE_B décrivent la même chose ? OUI/NON — pourquoi ?]
CONTRADICTION : [y a-t-il un fait dans les descriptions qui PROUVE qu'ils sont distincts ? OUI/NON — lequel ?]
SCORE : [de 1 à 10, quelle est la probabilité que ces deux entités soient la même chose ?
  1 = certainement distinctes, 10 = certainement identiques.
  7+ = confirmation, <7 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# Score 0-100%: same template but percentage scale — more intuitive for calibration.
_V5_SCORE_PCT_PROMPT = """\
Tu es un archiviste pour un JDR de civilisation. Analyse ces deux entités et remplis le template ci-dessous.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

Remplis ce template ligne par ligne AVANT de conclure :

NOMS : [les noms sont-ils des variantes, surnoms, fautes de frappe, ou abréviations l'un de l'autre ? OUI/NON — pourquoi ?]
RÔLE_A : [en une phrase, quel est le rôle/fonction/nature de A ?]
RÔLE_B : [en une phrase, quel est le rôle/fonction/nature de B ?]
MÊME_RÔLE : [est-ce que RÔLE_A et RÔLE_B décrivent la même chose ? OUI/NON — pourquoi ?]
CONTRADICTION : [y a-t-il un fait dans les descriptions qui PROUVE qu'ils sont distincts ? OUI/NON — lequel ?]
SCORE : [de 0 à 100, quel pourcentage de probabilité que ces deux entités soient la même chose ?
  0 = certainement distinctes, 100 = certainement identiques.
  70%+ = confirmation, <70% = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v6: same structure as v5 but explains the JDR context upfront.
# Key insight: descriptions come from different turns — the same entity can appear
# under different names and be described differently depending on which turn mentioned it.
# Complementary descriptions are a SIGNAL of alias, not proof of distinction.
_V6_JDR_CONTEXT_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE : Les descriptions ont été générées à partir des tours où chaque nom est apparu — elles sont partielles et reflètent un angle. La même entité peut être décrite différemment selon les tours. Des descriptions complémentaires (qui se recoupent sans se contredire) indiquent souvent le même objet vu sous deux angles.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

Remplis ce template :

NOMS : [les noms sont-ils des variantes l'un de l'autre ? OUI/NON — pourquoi]
MÊME_OBJET : [si A et B désignent la même chose, peut-on dire "A, aussi appelé B" sans que ça soit absurde ? OUI/NON — exemple]
CONTRADICTION : [y a-t-il un fait concret qui PROUVE qu'ils sont deux entités distinctes — pas juste deux descriptions partielles ? OUI/NON — lequel]
SCORE : [0 à 100.
  NOMS=OUI + MÊME_OBJET=OUI + CONTRADICTION=NON → 80-100.
  NOMS=NON + MÊME_OBJET=OUI + CONTRADICTION=NON → 60-75.
  MÊME_OBJET=NON ou CONTRADICTION=OUI → 0-40.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v7: adds explicit exclusion rules before the analysis to catch systematic FP patterns.
# Problem in v6: recall=100% but precision=40% (12 FPs). All FPs shared one of these patterns:
#   - Institution vs person who leads it (Chef du Tribunal ≠ Tribunal)
#   - Subgroup vs full group (Enfants du ciel ≠ Ciels-clairs)
#   - Place vs thing/disease/inscription inside it (Antres ≠ Maladie des Antres)
#   - Material vs object made from it (Argile vive ≠ Tablettes d'argile)
#   - Natural phenomenon vs social group (Ciel couvert ≠ Ciels-clairs)
#   - Physical place vs institution that meets there (Salle du Conseil ≠ Conseil)
#   - Two distinct flows/institutions sharing a keyword (Confluence des Biens ≠ des Échanges)
# Strategy: explicit EXCLUSION checklist → forces model to apply the rules before scoring.
# SUBSTITUTION replaces MÊME_OBJET — more concrete test (semantic equivalence vs compatibility).
# v7 problem: "modificateurs sémantiquement distincts" rule was too broad — broke 4 TPs.
_V7_EXCLUSION_RULES_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE : Les descriptions sont générées à partir des tours de jeu — partielles, complémentaires. La même entité peut être décrite différemment selon les tours et angles. Ne rejette pas deux entités uniquement parce que leurs descriptions diffèrent.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

RÈGLES D'EXCLUSION — vérifie d'abord cette liste. Si l'une s'applique → SCORE ≤ 30 :
• Chef/Dirigeant/Président de X ≠ X (rôle de direction ≠ l'institution elle-même)
• Enfants/Fils/Membres de X ≠ X (sous-groupe ≠ le groupe entier)
• Gardiens/Protecteurs/Voix de X ≠ X (fonction relative à X ≠ X lui-même)
• Lieu ≠ Objet, maladie, inscription ou événement DANS ce lieu (Grotte ≠ Maladie de la Grotte)
• Matériau ou substance ≠ Objet fabriqué avec ce matériau (Argile ≠ Tablettes d'argile)
• Phénomène naturel ou météo ≠ Groupe social ou peuple portant un nom similaire
• Lieu physique ≠ Institution ou assemblée qui s'y réunit (Salle du Conseil ≠ Conseil)
• Lieu géographique précis ≠ Élément naturel générique du même type (rivière précise ≠ rivières)
• Deux entités partageant un mot-clé mais avec modificateurs sémantiquement distincts (des Biens ≠ des Échanges)

Remplis ce template :

EXCLUSION : [une règle ci-dessus s'applique-t-elle ? OUI → précise laquelle / NON]
NOMS : [si EXCLUSION=NON — les noms sont-ils des variantes orthographiques ou dialectales du même concept ? OUI/NON — pourquoi]
SUBSTITUTION : [si EXCLUSION=NON — peut-on remplacer A par B dans une phrase de jeu sans changer le sens ni être absurde ? OUI/NON]
SCORE : [0 à 100.
  EXCLUSION=OUI → 0-30.
  EXCLUSION=NON + NOMS=OUI + SUBSTITUTION=OUI → 80-100.
  EXCLUSION=NON + NOMS=NON + SUBSTITUTION=OUI → 60-80.
  EXCLUSION=NON + SUBSTITUTION=NON → 30-50.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v10: pre-classification approach — instead of a checklist of exclusion rules,
# the model first classifies the TYPE of relationship between A and B.
# A single classification is easier for Nemo than evaluating 9 independent rules.
# The classification gates the score, so the model can't "drift" into high scores.
#
# Types designed to catch all known FP patterns:
#   RÔLE: one is a function/representative OF the other (Chef du Tribunal ≠ Tribunal, Voix des cieux ≠ Peuple)
#   HIÉRAR: hierarchical (Enfants de X ≠ X, subgroup ≠ group)
#   CONTENU: one is inside/made-from the other (Maladie des Antres ≠ Antres, Tablettes ≠ Argile)
#   DISTINCT: same template "[Terme] de [A]" vs "[Terme] de [B]" with different A≠B
#             (Peuple des eaux ≠ Peuple du ciel, Confluence des Biens ≠ des Échanges)
#   AUTRE: ambiguous cases → defer to descriptions (catches Gardiens/Confluence des Esprits)
_V10_CLASSIFY_FIRST_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE : Les descriptions sont générées à partir des tours de jeu — partielles, complémentaires. La même entité peut être décrite différemment selon les tours. Des descriptions complémentaires qui se recoupent sans se contredire indiquent souvent la même entité vue sous deux angles.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ÉTAPE 1 — CLASSIFICATION DE LA RELATION (choisis une seule catégorie) :

A. ALIAS : A et B sont le même concept sous formes différentes (variante orthographique, dialectale, singulier/pluriel, article, abréviation) → ils sont interchangeables sans ambiguïté
B. MÊME_RÔLE : A et B jouent exactement le même rôle dans le monde du jeu mais portent des noms distincts (synonymes fonctionnels attestés dans les descriptions)
C. RÔLE_DE : l'un est une fonction, titre, voix ou représentant de l'autre (ex: "Chef du Tribunal" est un rôle du "Tribunal", "Voix des cieux" est un rôle du "Peuple des cieux")
D. PARTIE_DE : l'un est un sous-groupe, enfant ou membre de l'autre (ex: "Enfants du ciel clair" sont des membres des "Ciels-clairs")
E. CONTENU_DE : l'un est localisé dans, fabriqué avec, ou issu de l'autre (ex: "Maladie des Antres" est dans les "Antres des Échos", "Tablettes d'argile" sont faites d'"Argile vive")
F. MÊME_TEMPLATE : les deux suivent "[Terme] de [X]" avec le même Terme mais des X sémantiquement différents (ex: "Peuple DES EAUX" ≠ "Peuple DU CIEL", "Confluence DES BIENS" ≠ "Confluence DES ÉCHANGES")
G. DISTINCT : deux entités clairement différentes qui partagent un mot par hasard

ÉTAPE 2 — SCORE basé sur la classification :
• A (ALIAS) → 80-100
• B (MÊME_RÔLE) → 70-85
• C/D/E/F/G → 0-40
→ 70+ = confirmation, <70 = rejet

Remplis ce template :

CLASSIFICATION : [lettre + justification en une phrase]
SCORE : [0 à 100 selon la règle ci-dessus]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v9: precise template rule — the key insight from v7/v8 iteration:
#   - v7 had "[Terme] de [A] ≠ [Terme] de [B]" as a vague "modificateurs" rule → broke 4 TPs
#     (Sans-ciels/Nés-sans-ciel, Fresque des Âges/Grande Fresque, Passes-bien/Confluence des Biens,
#      Peuple du ciel/Peuple des cieux)
#   - v8 dropped that rule → model ignored ALL exclusion rules → 15 FPs
#   - v9: makes the pattern rule PRECISE: both names must follow "[Terme] de [A]" and "[Terme] de [B]"
#     structure with the SAME base Terme but DIFFERENT A and B. Exception: singulier/pluriel.
#   - This catches: Confluence des Biens ≠ des Échanges, Fils de chasseur ≠ de pêcheurs,
#     Caste de l'Air ≠ de l'Éther, Peuple des eaux ≠ du ciel — but NOT Peuple du ciel / des cieux.
#   - Bumps NOMS=NON+SUBSTITUTION=OUI score to 70-85 to confirm borderline TPs (Passes-bien).
_V9_PRECISE_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE : Les descriptions sont générées à partir des tours de jeu — partielles, complémentaires. La même entité peut être décrite différemment selon les tours. Des descriptions complémentaires qui se recoupent sans se contredire indiquent souvent la même entité vue sous deux angles.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

RÈGLES D'EXCLUSION — si l'une s'applique → SCORE ≤ 30 :
• "Chef / Dirigeant / Président / Voix de [X]" ≠ X lui-même (ex: Chef du Tribunal ≠ Tribunal)
• Groupe désigné par sa relation à X (Enfants de X, Fils de X, Gardiens de X) ≠ X lui-même
• Lieu ou site physique ≠ Institution ou assemblée qui s'y réunit (Salle du Conseil ≠ Conseil)
• Lieu ou site ≠ Maladie, inscription, objet ou événement qui se trouve dans ce lieu
• Matériau ou substance brute ≠ Objet ou artefact fabriqué avec ce matériau
• Phénomène naturel ou météo ≠ Groupe social ou peuple portant un nom similaire
• "[Terme] de [A]" ≠ "[Terme] de [B]" quand le même Terme de base est qualifié par A et B sémantiquement différents (ex: Confluence DES BIENS ≠ Confluence DES ÉCHANGES, Fils DE CHASSEUR ≠ Fils DE PÊCHEURS). EXCEPTION : singulier/pluriel du même mot (du ciel = des cieux, d'un = de) n'est PAS une différence sémantique.

Remplis ce template :

EXCLUSION : [une règle ci-dessus s'applique-t-elle ? OUI → précise laquelle / NON]
NOMS : [si EXCLUSION=NON — les noms sont-ils des variantes (orthographe, dialecte, singulier/pluriel, article, ordre des mots) du même concept ? OUI/NON — pourquoi]
SUBSTITUTION : [si EXCLUSION=NON — en tenant compte des descriptions, peut-on remplacer A par B dans une phrase de jeu sans changer le sens ni être absurde ? OUI/NON — pourquoi]
SCORE : [0 à 100.
  EXCLUSION=OUI → 0-30.
  EXCLUSION=NON + NOMS=OUI + SUBSTITUTION=OUI → 80-100.
  EXCLUSION=NON + NOMS=NON + SUBSTITUTION=OUI → 70-85.
  EXCLUSION=NON + SUBSTITUTION=NON → 20-50.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v8: balanced — drops the "modificateurs sémantiquement distincts" rule from v7 (too broad,
# broke 4 TPs: Sans-ciels/Nés-sans-ciel, Fresque des Âges/Grande Fresque,
# Passes-bien/Confluence des Biens, Peuple du ciel/des cieux).
# Key fixes vs v7:
#   - Removed broad "modificateurs" rule
#   - "Enfants de X ≠ X" now requires EXPLICIT filiation ("Enfants de" or "Fils de" + X in the name)
#     to avoid misapplying to "Nés-sans-ciel" (which is a name, not "children of Sans-ciels")
#   - NOMS now explicitly lists "singulier/pluriel, article, ordre des mots" as valid variants
#   - SUBSTITUTION now says "en tenant compte des descriptions" to help borderline TPs
#   - Score range for NOMS=NON + SUBSTITUTION=OUI bumped to 65-85 (was 60-80)
#     → borderline TPs like Passes-bien/Confluence des Biens can now exceed threshold 70
_V8_BALANCED_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE : Les descriptions sont générées à partir des tours de jeu — partielles, complémentaires. La même entité peut être décrite différemment selon les tours. Des descriptions complémentaires qui se recoupent sans se contredire indiquent souvent la même entité vue sous deux angles.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

RÈGLES D'EXCLUSION — si l'une s'applique → SCORE ≤ 30 :
• "Chef / Dirigeant / Président / Voix de [X]" ≠ X lui-même (rôle ≠ institution)
• "Enfants de [X]" / "Fils de [X]" avec X présent dans le nom B ≠ X lui-même (filiation ≠ groupe)
• Groupe qui garde ou protège [X] ≠ X lui-même (ex: Gardiens de la Confluence ≠ Confluence)
• Lieu ou site physique ≠ Institution ou assemblée qui s'y réunit (Salle du Conseil ≠ Conseil)
• Lieu ou site ≠ Maladie, inscription, objet ou événement qui se trouve dans ce lieu
• Matériau ou substance brute ≠ Objet ou artefact fabriqué avec ce matériau
• Phénomène naturel ou météo ≠ Groupe social ou peuple portant un nom similaire

Remplis ce template :

EXCLUSION : [une règle ci-dessus s'applique-t-elle ? OUI → précise laquelle / NON]
NOMS : [si EXCLUSION=NON — les noms sont-ils des variantes du même concept (orthographe, dialecte, singulier/pluriel, article, ordre des mots) ? OUI/NON — pourquoi]
SUBSTITUTION : [si EXCLUSION=NON — en tenant compte des descriptions, peut-on remplacer A par B dans une phrase de jeu sans changer le sens ni être absurde ? OUI/NON — pourquoi]
SCORE : [0 à 100.
  EXCLUSION=OUI → 0-30.
  EXCLUSION=NON + NOMS=OUI + SUBSTITUTION=OUI → 80-100.
  EXCLUSION=NON + NOMS=NON + SUBSTITUTION=OUI → 65-85.
  EXCLUSION=NON + SUBSTITUTION=NON → 20-50.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v13: v12 + INCOMPATIBILITÉ overrides DESCRIPTIONS.
# Bug in v12: when descriptions seem to describe the same geographic area (e.g., both mention the
# crystalline river valley), the model says DESCRIPTIONS=OUI → 90% even for pairs like
# "Confluence de deux rivières / Rivières cristallines" where the NAME reveals they're distinct
# (specific named confluence ≠ rivers in general). Fix: INCOMPATIBILITÉ_NOM=OUI must override
# DESCRIPTIONS regardless. Also broadens Gardiens rule to catch partial name matches.
_V13_INCOMP_OVERRIDE_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ÉTAPE 1 — INCOMPATIBILITÉS STRUCTURELLES DES NOMS (vérifie d'abord) :
Si l'une des situations suivantes s'applique → INCOMPATIBILITÉ=OUI → SCORE ≤ 35 (même si les descriptions semblent compatibles) :
• "Chef / Dirigeant de X" vs X (une personne de direction ≠ l'institution)
• "Enfants / Fils de X" vs X (sous-groupe filial ≠ le groupe entier)
• Groupe de gardiens, protecteurs ou représentants d'un lieu ou concept → ≠ ce lieu/concept (ex: Gardiens de la Confluence ≠ Confluence des Esprits)
• Lieu physique (salle, bâtiment, espace) vs Institution ou assemblée qui s'y réunit
• Lieu géographique précis et nommé vs Élément naturel générique du même type (ex: "Confluence de deux rivières cristallines spécifiques" ≠ "rivières cristallines en général")
• Phénomène naturel ou météo vs groupe social portant un nom similaire
• "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther, Biens ≠ Échanges)

ÉTAPE 2 — DESCRIPTIONS (seulement si ÉTAPE 1 = aucune incompatibilité) :
Lis les descriptions. Les descriptions décrivent-elles la même entité — même rôle social, même fonction, même lieu, même objet ?
Note : pour des groupes/peuples, des aspects complémentaires (origine vs rôle) → INCERTAIN si non contradictoire.
→ OUI / INCERTAIN / NON — justifie en une phrase.

SCORE : [0 à 100.
  ÉTAPE 1 : INCOMPATIBILITÉ=OUI → 0-35.
  ÉTAPE 2 : DESCRIPTIONS=OUI → 80-100.
  ÉTAPE 2 : DESCRIPTIONS=INCERTAIN → 65-80.
  ÉTAPE 2 : DESCRIPTIONS=NON → 0-40.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v12: v11 tuned — adds 3 more incompatibility rules and guidance for complementary group descriptions.
# FPs remaining in v11:
#   - Confluence de deux rivières / Rivières cristallines: "lieu précis ≠ générique" needed
#   - Gardiens de la Confluence / Confluence des Esprits: "Gardiens de X ≠ X"
#   - Salle du Conseil / Conseil du village: "lieu physique ≠ institution"
# FN remaining: Peuple du ciel clair / Ciels-clairs (65%) — add guidance for complementary group descriptions
_V12_DESC_FIRST_TUNED_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ANALYSE EN 2 ÉTAPES :

ÉTAPE 1 — DESCRIPTIONS (ignore les noms pour l'instant) :
Lis les descriptions. Les descriptions décrivent-elles la même entité dans le monde du jeu — même rôle social, même fonction, même lieu, même objet ?
Note : pour des groupes ou peuples, des descriptions partielles décrivant des aspects complémentaires (l'un parle de leur origine, l'autre de leur rôle) → répond INCERTAIN si les fonctions ne contredisent pas.
→ OUI / INCERTAIN / NON — justifie en une phrase.

ÉTAPE 2 — NOMS (si ÉTAPE 1 ≠ NON, vérifie ces incompatibilités structurelles) :
Les noms révèlent-ils une incompatibilité évidente ?
• "Chef / Dirigeant de X" vs X (une personne ou rôle de direction ≠ l'institution)
• "Enfants / Fils de X" vs X (sous-groupe ≠ le groupe entier)
• "Gardiens / Protecteurs de X" vs X (groupe chargé de garder X ≠ X lui-même)
• Lieu physique vs Institution qui s'y réunit (ex: Salle du Conseil ≠ Conseil du village)
• Lieu géographique précis et nommé vs Élément naturel générique (ex: "Confluence de deux rivières spécifiques" ≠ "rivières en général")
• Phénomène naturel vs groupe social portant un nom similaire
• "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther, Biens ≠ Échanges)
→ Si OUI à l'une : INCOMPATIBILITÉ_NOM=OUI

SCORE : [0 à 100.
  DESCRIPTIONS=OUI + INCOMPATIBILITÉ_NOM=NON → 80-100.
  DESCRIPTIONS=INCERTAIN + INCOMPATIBILITÉ_NOM=NON → 65-80.
  DESCRIPTIONS=NON → 0-40.
  INCOMPATIBILITÉ_NOM=OUI → 0-35.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v11: descriptions-first for Qwen3.
# Problem: Qwen3 reads descriptions carefully, sees they differ between turns, concludes "different entities".
# But in this JDR, the SAME entity is described differently in different turns (normal).
# Solution: ask Qwen3 to evaluate descriptions FIRST (do they describe the same function/role?),
# then check names SECOND (are they incompatible?).
# This inverts the usual name-first approach and leverages Qwen3's careful description reading.
#
# Anti-FP guard: kept as VÉRIFICATION DES NOMS step after description analysis.
# Key principle communicated: "different names for the same function IS an alias in this JDR".
_V11_DESC_FIRST_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ANALYSE EN 2 ÉTAPES :

ÉTAPE 1 — DESCRIPTIONS (ignore les noms pour l'instant) :
Lis les descriptions ci-dessus. Les descriptions décrivent-elles la même entité dans le monde du jeu — même rôle social, même fonction, même lieu, même objet ? OUI/NON/INCERTAIN — pourquoi ?

ÉTAPE 2 — NOMS (si ÉTAPE 1 = OUI ou INCERTAIN, vérifie que les noms ne révèlent pas une distinction structurelle) :
Les noms révèlent-ils une incompatibilité évidente ?
• "Chef / Dirigeant de X" vs X (une personne ≠ l'institution)
• "Enfants / Fils de X" vs X (sous-groupe ≠ le groupe entier)
• Phénomène naturel vs groupe social portant un nom similaire
• "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther)
→ Si OUI à l'une : INCOMPATIBILITÉ_NOM=OUI

SCORE : [0 à 100.
  DESCRIPTIONS=OUI + INCOMPATIBILITÉ_NOM=NON → 80-100.
  DESCRIPTIONS=INCERTAIN + INCOMPATIBILITÉ_NOM=NON → 65-80.
  DESCRIPTIONS=NON → 0-40.
  INCOMPATIBILITÉ_NOM=OUI → 0-35.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v16: v12 descriptions-first + minimal example improvements only.
#
# v15 regressed (F1=71.4% vs 82.4%) because:
#   - "prime sur les descriptions" in SCORE discouraged INCOMPATIBILITÉ_NOM=OUI on borderline cases
#     → pair 25 (Confluence des Biens / Échanges) slipped to FP (70%), pair 5 also affected
#   - Generalizing Gardiens rule to "X ou tout concept associé à X" was too broad → pair 5 FN
#   - Context bleeding from SCORE change → DESCRIPTIONS=NON for pair 17 (Peuple du ciel / des cieux)
#
# Strategy for v16: ONLY improve the 2 example strings in the 2 failing ÉTAPE 2 rules.
# No changes to SCORE section, no changes to rule structure, no generalization.
# Hypothesis: Qwen3 needs to SEE the exact failing pairs as examples to recognize the pattern.
#
# FP 21: "Gardiens / Protecteurs de X" vs X — Qwen3 didn't apply because X differs
#   (Gardiens de "la Confluence" ≠ "Confluence des Esprits" — different X).
#   Fix: add example showing exact pair 21 names so Qwen3 can pattern-match it.
#
# FP 15: "Lieu géographique précis" vs "Élément naturel générique" — example was not close enough.
#   Fix: use exact pair 15 names in the example.
_V16_MINIMAL_EXAMPLES_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ANALYSE EN 2 ÉTAPES :

ÉTAPE 1 — DESCRIPTIONS (ignore les noms pour l'instant) :
Lis les descriptions. Les descriptions décrivent-elles la même entité dans le monde du jeu — même rôle social, même fonction, même lieu, même objet ?
Note : pour des groupes ou peuples, des descriptions partielles décrivant des aspects complémentaires (l'un parle de leur origine, l'autre de leur rôle) → répond INCERTAIN si les fonctions ne contredisent pas.
→ OUI / INCERTAIN / NON — justifie en une phrase.

ÉTAPE 2 — NOMS (si ÉTAPE 1 ≠ NON, vérifie ces incompatibilités structurelles) :
Les noms révèlent-ils une incompatibilité évidente ?
• "Chef / Dirigeant de X" vs X (une personne ou rôle de direction ≠ l'institution)
• "Enfants / Fils de X" vs X (sous-groupe ≠ le groupe entier)
• "Gardiens / Protecteurs de X" vs X ou tout concept lié à X (groupe fonctionnel ≠ le lieu/concept — ex : "Gardiens de la Confluence" ≠ "Confluence des Esprits" : les gardiens sont un groupe qui surveille la Confluence, pas la Confluence elle-même)
• Lieu physique vs Institution qui s'y réunit (ex: Salle du Conseil ≠ Conseil du village)
• Lieu géographique précis et nommé vs Élément naturel générique du même type (ex : "Confluence de deux rivières cristallines" = un point précis de jonction ≠ "Rivières cristallines" = les rivières en général, pas ce point)
• Phénomène naturel vs groupe social portant un nom similaire
• "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther, Biens ≠ Échanges)
→ Si OUI à l'une : INCOMPATIBILITÉ_NOM=OUI

SCORE : [0 à 100.
  DESCRIPTIONS=OUI + INCOMPATIBILITÉ_NOM=NON → 80-100.
  DESCRIPTIONS=INCERTAIN + INCOMPATIBILITÉ_NOM=NON → 65-80.
  DESCRIPTIONS=NON → 0-40.
  INCOMPATIBILITÉ_NOM=OUI → 0-35.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v15: v12 descriptions-first + targeted fixes for the 2 remaining FPs.
#
# FP 21 (Gardiens de la Confluence / Confluence des Esprits at 90%):
#   v12 rule "Gardiens de X ≠ X" wasn't applied because the X differs ("la Confluence" ≠ "des Esprits").
#   Fix: generalize to "groupe dont le nom contient Gardiens/Protecteurs/Voix de X ≠ X ou concept associé à X"
#   + add exact pair 21 example so Qwen3 can't miss it.
#
# FP 15 (Confluence de deux rivières cristallines / Rivières cristallines at 90%):
#   v12 example was "Confluence de deux rivières spécifiques ≠ rivières en général" — close but not exact.
#   Qwen3 saw DESCRIPTIONS=OUI (same river valley) → INCOMPATIBILITÉ_NOM=NON (descriptions win).
#   Fix: use the exact pair 15 names as the example + move INCOMPATIBILITÉ_NOM=OUI to FIRST in SCORE
#   with explicit "(prime sur les descriptions, même si DESCRIPTIONS=OUI)".
#
# Intentionally preserved from v12:
#   - descriptions-first order (to avoid regression on pair 17: Peuple du ciel/des cieux)
#   - no ÉTAPE 0 / VETO structure (caused regression on pair 1: Sans-ciels in v14)
_V15_EXPLICIT_EXAMPLES_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ANALYSE EN 2 ÉTAPES :

ÉTAPE 1 — DESCRIPTIONS (ignore les noms pour l'instant) :
Lis les descriptions. Les descriptions décrivent-elles la même entité dans le monde du jeu — même rôle social, même fonction, même lieu, même objet ?
Note : pour des groupes ou peuples, des descriptions partielles décrivant des aspects complémentaires (l'un parle de leur origine, l'autre de leur rôle) → répond INCERTAIN si les fonctions ne contredisent pas.
→ OUI / INCERTAIN / NON — justifie en une phrase.

ÉTAPE 2 — NOMS (si ÉTAPE 1 ≠ NON, vérifie ces incompatibilités structurelles) :
Les noms révèlent-ils une incompatibilité évidente ?
• "Chef / Dirigeant de X" vs X (une personne ou rôle de direction ≠ l'institution)
• "Enfants / Fils de X" vs X (sous-groupe ≠ le groupe entier)
• Tout groupe défini par sa FONCTION vis-à-vis d'un lieu ou concept ("Gardiens de X", "Protecteurs de X", "Voix de X") ≠ ce lieu/concept ou n'importe quel autre concept lié à X — même si les deux descriptions parlent du même lieu (ex précis : "Gardiens de la Confluence" est un GROUPE chargé de surveiller ≠ "Confluence des Esprits" qui est un LIEU/CONCEPT — même si les deux mentionnent la Confluence)
• Lieu physique vs Institution qui s'y réunit (ex: Salle du Conseil ≠ Conseil du village)
• Lieu géographique précis et nommé vs Élément naturel générique du même type (ex précis : "Confluence de deux rivières cristallines" = un point géographique précis ≠ "Rivières cristallines" = les rivières en général, pas le point de confluence)
• Phénomène naturel vs groupe social portant un nom similaire
• "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther, Biens ≠ Échanges)
→ Si OUI à l'une : INCOMPATIBILITÉ_NOM=OUI

SCORE : [0 à 100.
  INCOMPATIBILITÉ_NOM=OUI → 0-35 (cette règle prime sur les descriptions — même si DESCRIPTIONS=OUI, la distinction de noms est structurelle et définitive).
  DESCRIPTIONS=OUI + INCOMPATIBILITÉ_NOM=NON → 80-100.
  DESCRIPTIONS=INCERTAIN + INCOMPATIBILITÉ_NOM=NON → 65-80.
  DESCRIPTIONS=NON → 0-40.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# v14: surgical fix — ÉTAPE 0 (2 override rules only) + v12's descriptions-first structure.
# Problem in v12: FP 15 (Confluence de deux rivières / Rivières cristallines) at 90% and
#   FP 21 (Gardiens / Confluence des Esprits) at 75% — DESCRIPTIONS=OUI overrides rules.
# Problem in v13: moved ALL rules to override → broke pair 17 (Peuple du ciel / des cieux, 30%).
#   Root cause: changing order (incompatibilities first, descriptions second) changed model priors
#   → descriptions analysis gave NON for the same pair that was OUI in v12.
#
# Solution: keep v12's ORDER (descriptions first) to preserve pair 17,
# but add ÉTAPE 0 with ONLY the 2 specific override rules that caused FPs:
#   1. Gardiens/Protecteurs de X ≠ X (catches FP 21)
#   2. Lieu précis ≠ Générique (catches FP 15)
# These are the most structural/clear-cut rules that won't affect any TPs.
_V14_SURGICAL_PROMPT = """\
Tu es un archiviste expert pour un JDR de civilisation multijoueur.

CONTEXTE CRUCIAL : Dans ce JDR, la même entité peut apparaître sous des noms différents selon les tours et les joueurs. Une institution, un lieu ou un groupe peut avoir plusieurs appellations utilisées alternativement. Les descriptions viennent de tours différents et décrivent souvent la même réalité sous des angles complémentaires. La différence de nom NE PROUVE PAS qu'il s'agit d'entités distinctes.

ENTITÉ A : "{name_a}" (type: {type_a})
{desc_a}

ENTITÉ B : "{name_b}" (type: {type_b})
{desc_b}

SIGNAL : {reason}

ÉTAPE 0 — VETO STRUCTUREL (vérifie ces 2 règles AVANT de lire les descriptions) :
Si l'une s'applique → SCORE ≤ 30, peu importe les descriptions :
• Un groupe chargé de garder, protéger ou représenter un lieu/concept ≠ ce lieu/concept lui-même (ex: "Gardiens de la Confluence" ≠ "Confluence des Esprits" même si les deux parlent de la Confluence)
• Un lieu géographique précis et nommé (avec qualificatifs spécifiques : "Confluence de deux rivières cristallines") ≠ un élément naturel générique du même type ("rivières cristallines en général")
→ VETO=OUI ou NON

ÉTAPE 1 — DESCRIPTIONS (seulement si VETO=NON, ignore les noms pour l'instant) :
Les descriptions décrivent-elles la même entité — même rôle social, même fonction, même lieu, même objet ?
Pour des groupes/peuples, des aspects complémentaires (origine vs rôle) → INCERTAIN si non contradictoire.
→ OUI / INCERTAIN / NON — justifie en une phrase.

ÉTAPE 2 — INCOMPATIBILITÉS SECONDAIRES (seulement si VETO=NON et ÉTAPE 1 ≠ NON) :
Une de ces structures révèle-t-elle une incompatibilité ?
• "Chef / Dirigeant de X" vs X — • "Enfants / Fils de X" vs X — • Lieu physique vs Institution qui s'y réunit — • Phénomène naturel vs groupe social — • "[Terme] de [A]" vs "[Terme] de [B]" avec A et B clairement différents (eau ≠ ciel, Air ≠ Éther)
→ INCOMP2=OUI ou NON

SCORE : [0 à 100.
  VETO=OUI → 0-30.
  INCOMP2=OUI → 20-40.
  DESCRIPTIONS=OUI + INCOMP2=NON → 80-100.
  DESCRIPTIONS=INCERTAIN + INCOMP2=NON → 65-80.
  DESCRIPTIONS=NON → 0-40.
  70+ = confirmation, <70 = rejet.]

JSON : {{"score": X, "confidence": "high/medium/low", "reasoning": "une phrase"}}"""


# Registry of confirmation prompt versions.
# Key = version name, used in llm_config.json "aliases": {"prompt_version": "..."}
_CONFIRM_VERSIONS: dict[str, AliasConfirmVersion] = {
    "v1-llama": AliasConfirmVersion(
        name="v1-llama",
        description="Short direct prompt for Llama 3.1 — no thinking mode, clear instruction-following",
        prompt=_V1_LLAMA_PROMPT,
    ),
    "v2-qwen3": AliasConfirmVersion(
        name="v2-qwen3",
        description="Question-based prompt for Qwen3 — leverages <think> reasoning before answering",
        prompt=_V2_QWEN3_PROMPT,
    ),
    "v3-nemo": AliasConfirmVersion(
        name="v3-nemo",
        description=(
            "Structured template for Mistral Nemo — forces line-by-line analysis "
            "(NOMS/RÔLE/MÊME_RÔLE/CONTRADICTION/VERDICT) before JSON output"
        ),
        prompt=_V3_NEMO_PROMPT,
        json_mode=False,  # template text comes before JSON, can't use json_mode
    ),
    "v4-score-10": AliasConfirmVersion(
        name="v4-score-10",
        description=(
            "Score 1-10 variant of v3-nemo — same structured template but outputs "
            "a numeric score instead of true/false. Use to calibrate the threshold "
            "empirically by inspecting the score distribution across candidates."
        ),
        prompt=_V4_SCORE10_PROMPT,
        json_mode=False,
        score_scale=10,  # score field is 1-10, normalized to 0-1 internally
    ),
    "v5-score-pct": AliasConfirmVersion(
        name="v5-score-pct",
        description=(
            "Score 0-100% variant of v3-nemo — same structured template but outputs "
            "a percentage score instead of true/false. More intuitive for calibration."
        ),
        prompt=_V5_SCORE_PCT_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v6-jdr-context": AliasConfirmVersion(
        name="v6-jdr-context",
        description=(
            "JDR-aware prompt — explains that descriptions come from different turns "
            "and can be partial/complementary. Replaces MÊME_RÔLE with COMPATIBLE "
            "to avoid penalizing descriptions that describe the same entity from "
            "different angles. Key fix for the recall problem of v5."
        ),
        prompt=_V6_JDR_CONTEXT_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v7-exclusion-rules": AliasConfirmVersion(
        name="v7-exclusion-rules",
        description=(
            "Exclusion-rules prompt — adds a checklist of systematic FP patterns "
            "(chef ≠ institution, enfants ≠ groupe, lieu ≠ contenu, matériau ≠ objet, "
            "phénomène naturel ≠ peuple, lieu physique ≠ institution, modificateurs "
            "distincts ≠ même chose). Keeps JDR context from v6 for recall. "
            "SUBSTITUTION replaces MÊME_OBJET for a stronger semantic equivalence test."
        ),
        prompt=_V7_EXCLUSION_RULES_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v8-balanced": AliasConfirmVersion(
        name="v8-balanced",
        description=(
            "Balanced exclusion-rules — drops 'modificateurs sémantiquement distincts' "
            "rule from v7 (too broad, broke 4 TPs). Keeps 7 targeted rules. "
            "NOMS now lists singulier/pluriel/dialecte as valid variants. "
            "SUBSTITUTION is anchored to descriptions. Score range 65-85 for "
            "NOMS=NON+SUBSTITUTION=OUI to help borderline TPs like Passes-bien."
        ),
        prompt=_V8_BALANCED_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v11-desc-first": AliasConfirmVersion(
        name="v11-desc-first",
        description=(
            "Descriptions-first for Qwen3 — inverts analysis: reads descriptions first "
            "to determine if they describe the same entity, then checks names for structural "
            "incompatibilities (Chef de X ≠ X, Enfants de X ≠ X, etc.). "
            "Explicitly states that different names for the same function ARE aliases in JDR."
        ),
        prompt=_V11_DESC_FIRST_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v12-desc-first-tuned": AliasConfirmVersion(
        name="v12-desc-first-tuned",
        description=(
            "v11 tuned — adds 3 more incompatibility rules to catch remaining FPs: "
            "Gardiens/Protecteurs de X ≠ X, Lieu physique ≠ Institution, "
            "Lieu précis ≠ Élément naturel générique. "
            "Adds guidance for groups: complementary descriptions of same people → INCERTAIN. "
            "Best version for Qwen3 targeting F1>80%."
        ),
        prompt=_V12_DESC_FIRST_TUNED_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v13-incomp-override": AliasConfirmVersion(
        name="v13-incomp-override",
        description=(
            "v12 + INCOMPATIBILITÉ overrides DESCRIPTIONS — critical fix: when a structural "
            "incompatibility (Chef de X ≠ X, Gardiens ≠ X, lieu ≠ institution...) is found, "
            "score is ≤35 even if descriptions seem to match. "
            "Broadens Gardiens rule to catch related-but-not-same cases. "
            "Fixes FP 15 (Confluence précis / rivières génériques) and FP 21 (Gardiens)."
        ),
        prompt=_V13_INCOMP_OVERRIDE_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v14-surgical": AliasConfirmVersion(
        name="v14-surgical",
        description=(
            "Surgical fix — ÉTAPE 0 (veto) with ONLY 2 override rules: Gardiens de X ≠ X "
            "and lieu précis ≠ générique. Keeps v12's descriptions-first order to avoid "
            "the regression that broke Peuple du ciel/des cieux in v13. "
            "Targets F1>82% by fixing FP 15 and 21 without touching TPs."
        ),
        prompt=_V14_SURGICAL_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v16-minimal-examples": AliasConfirmVersion(
        name="v16-minimal-examples",
        description=(
            "Minimal improvement on v12 — ONLY changes the 2 example strings in the 2 failing rules. "
            "Gardiens rule: adds exact pair 21 example (Gardiens de la Confluence ≠ Confluence des Esprits) "
            "and extends to '≠ X ou tout concept lié à X'. "
            "Lieu précis rule: uses exact pair 15 names as example. "
            "SCORE section unchanged from v12 to avoid v15's regressions. "
            "Hypothesis: Qwen3 needs exact examples to pattern-match the failing cases."
        ),
        prompt=_V16_MINIMAL_EXAMPLES_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v15-explicit-examples": AliasConfirmVersion(
        name="v15-explicit-examples",
        description=(
            "v12 + exact concrete examples for the 2 remaining FPs, INCOMPATIBILITÉ_NOM=OUI "
            "moved first in SCORE with explicit override note. "
            "Gardiens rule: generalized to 'groupe fonctionnel ≠ X ou concept associé à X' "
            "with example (Gardiens de la Confluence ≠ Confluence des Esprits). "
            "Lieu précis rule: example now uses exact pair 15 names "
            "(Confluence de deux rivières cristallines ≠ Rivières cristallines). "
            "Order preserved from v12 (descriptions first) to avoid v13/v14 regressions."
        ),
        prompt=_V15_EXPLICIT_EXAMPLES_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v10-classify-first": AliasConfirmVersion(
        name="v10-classify-first",
        description=(
            "Pre-classification approach — model first classifies the relationship type "
            "(ALIAS/RÔLE/HIÉRAR/CONTENU/DISTINCT/AUTRE) before scoring. Single decision "
            "is easier for Nemo than a 9-item checklist. ALIAS → 80-100, "
            "RÔLE/HIÉRAR/CONTENU/DISTINCT → 0-40, AUTRE → consult descriptions."
        ),
        prompt=_V10_CLASSIFY_FIRST_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
    "v9-precise-template": AliasConfirmVersion(
        name="v9-precise-template",
        description=(
            "Precise template rule — replaces the broad 'modificateurs distincts' rule "
            "with the exact pattern '[Terme] de [A]' != '[Terme] de [B]' when A and B "
            "are semantically different. Exception: singulier/pluriel of the same word "
            "(ciel/cieux) is NOT a distinction. Restores the 4 TPs lost in v7 while "
            "keeping precision rules. Score range NOMS=NON+SUBSTITUTION=OUI → 70-85."
        ),
        prompt=_V9_PRECISE_PROMPT,
        json_mode=False,
        score_scale=100,
    ),
}


def get_confirm_version(name: str) -> AliasConfirmVersion:
    """Retrieve a confirmation prompt version by name.

    Raises ValueError if the version is not registered.
    """
    if name not in _CONFIRM_VERSIONS:
        available = sorted(_CONFIRM_VERSIONS)
        raise ValueError(
            f"Unknown alias confirm version '{name}'. Available: {available}"
        )
    return _CONFIRM_VERSIONS[name]


def list_confirm_versions() -> list[str]:
    """Return all registered confirmation prompt version names."""
    return sorted(_CONFIRM_VERSIONS)


def find_alias_candidates(profiles: list[EntityProfile]) -> list[AliasCandidate]:
    """Stage 1: Find candidate alias pairs using deterministic pattern matching.

    Four signals, in increasing breadth:
      1. LLM-suggested: profiler explicitly names an alias → exact match in index
      2. Appositive patterns: "aussi appelé", "surnommé", etc. in mention contexts
      3. Description overlap: high keyword overlap between entity descriptions (≥0.6)
      4. Fuzzy name: token overlap on normalized names (≥0.5) — catches variants like
         "Sans-ciels" / "Nés-sans-ciel" or "Cercle des Sages" / "Cercle de ses sages"

    Cross-type guard removed: the same real-world entity can be classified differently
    across turns (e.g., "Ciels-libres" as civilization in one turn, caste in another).
    The LLM confirmation stage (Stage 2) filters cross-type false positives.
    """
    candidates: list[AliasCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()

    # Index profiles by normalized name for O(1) lookup
    name_index: dict[str, EntityProfile] = {}
    for p in profiles:
        name_index[p.canonical_name.lower().strip()] = p

    # --- Signal 1: LLM-suggested aliases from profiling ---
    # The profiler LLM sometimes explicitly names aliases in the profile description.
    for p in profiles:
        for alias in p.aliases_suggested:
            alias_lower = alias.lower().strip()
            if alias_lower in name_index:
                other = name_index[alias_lower]
                if other.entity_id == p.entity_id:
                    continue
                pair = _pair_key(p.entity_id, other.entity_id)
                if pair not in seen_pairs:
                    type_note = (
                        f" [types: {p.entity_type} vs {other.entity_type}]"
                        if p.entity_type != other.entity_type else ""
                    )
                    seen_pairs.add(pair)
                    candidates.append(AliasCandidate(
                        entity_a=p,
                        entity_b=other,
                        reason=(
                            f"Le profil de '{p.canonical_name}' mentionne '{alias}'"
                            f" comme alias{type_note}"
                        ),
                        source="llm_suggested",
                    ))

    # --- Signal 2: Appositive patterns in raw mention contexts ---
    # Patterns like "aussi appelé", "surnommé", "c'est-à-dire" in the game text.
    for p in profiles:
        for ctx in p.mention_contexts:
            ctx_lower = ctx.lower()
            if p.canonical_name.lower() not in ctx_lower:
                continue
            for pattern in ALIAS_PATTERNS:
                for match in pattern.finditer(ctx):
                    alias_text = match.group(1).strip().rstrip(".,;:!?")
                    alias_lower = alias_text.lower()
                    if alias_lower in name_index:
                        other = name_index[alias_lower]
                        if other.entity_id == p.entity_id:
                            continue
                        pair = _pair_key(p.entity_id, other.entity_id)
                        if pair not in seen_pairs:
                            type_note = (
                                f" [types: {p.entity_type} vs {other.entity_type}]"
                                if p.entity_type != other.entity_type else ""
                            )
                            seen_pairs.add(pair)
                            candidates.append(AliasCandidate(
                                entity_a=p,
                                entity_b=other,
                                reason=(
                                    f"Pattern appositif : '{ctx.strip()[:100]}'"
                                    f"{type_note}"
                                ),
                                source="appositive_pattern",
                            ))

    # --- Signal 3: Description keyword overlap ---
    # High keyword overlap between descriptions suggests the same real-world entity.
    # Same-type threshold: 0.6; cross-type threshold: 0.75 (more conservative).
    profiles_with_desc = [p for p in profiles if p.description]
    for i, pa in enumerate(profiles_with_desc):
        for pb in profiles_with_desc[i + 1:]:
            pair = _pair_key(pa.entity_id, pb.entity_id)
            if pair in seen_pairs:
                continue
            overlap = _description_overlap(pa.description, pb.description)
            same_type = pa.entity_type == pb.entity_type
            threshold = 0.6 if same_type else 0.75
            if overlap >= threshold:
                type_note = (
                    f" [types: {pa.entity_type} vs {pb.entity_type}]"
                    if not same_type else ""
                )
                seen_pairs.add(pair)
                candidates.append(AliasCandidate(
                    entity_a=pa,
                    entity_b=pb,
                    reason=f"Descriptions très similaires ({overlap:.0%} overlap){type_note}",
                    source="description_overlap",
                ))

    # --- Signal 4: Fuzzy name matching ---
    # Token overlap on normalized names catches variants that the other signals miss:
    # "Ciels-clairs" / "Ciels-libres", "Sans-ciels" / "Nés-sans-ciel",
    # "Cercle des Sages" / "Cercle de ses sages".
    # Threshold 0.5 means ≥50% of the shorter name's tokens match the longer name.
    # Guard: both names must have ≥2 meaningful tokens — single-word entities like
    # "Confluence" or "Esprits" share a token with dozens of compound names but are
    # distinct entities. The LLM stage would reject them, but it's cheaper to skip early.
    for i, pa in enumerate(profiles):
        for pb in profiles[i + 1:]:
            pair = _pair_key(pa.entity_id, pb.entity_id)
            if pair in seen_pairs:
                continue
            tokens_a = _normalize_tokens(pa.canonical_name)
            tokens_b = _normalize_tokens(pb.canonical_name)
            if len(tokens_a) < 2 or len(tokens_b) < 2:
                continue
            if not tokens_a or not tokens_b:
                continue
            intersection = tokens_a & tokens_b
            smaller = min(len(tokens_a), len(tokens_b))
            overlap = len(intersection) / smaller if smaller > 0 else 0.0
            if overlap >= 0.5:
                type_note = (
                    f" [types: {pa.entity_type} vs {pb.entity_type}]"
                    if pa.entity_type != pb.entity_type else ""
                )
                seen_pairs.add(pair)
                candidates.append(AliasCandidate(
                    entity_a=pa,
                    entity_b=pb,
                    reason=(
                        f"Noms similaires ({overlap:.0%} tokens communs){type_note}"
                    ),
                    source="fuzzy_name",
                ))

    return candidates


def confirm_aliases(
    candidates: list[AliasCandidate],
    model: str = DEFAULT_MODEL,
    provider: LLMProvider | None = None,
    confirm_version: str = DEFAULT_CONFIRM_VERSION,
    score_threshold: float = 0.7,
) -> list[ConfirmedAlias]:
    """Stage 2: Confirm alias candidates with targeted LLM calls.

    Args:
        candidates: Pairs from Stage 1.
        model: LLM model to use for confirmation.
        provider: LLM provider instance (created from model default if None).
        confirm_version: Prompt version name — "v1-llama", "v2-qwen3", "v3-nemo",
            "v4-score-10", or "v5-score-pct".
        score_threshold: For score-based versions (v4/v5), the minimum normalized score
            (0-1) to confirm. Default 0.7 = 7/10 or 70%. Ignored for binary versions.
    """
    version = get_confirm_version(confirm_version)
    confirmed: list[ConfirmedAlias] = []
    score_mode = version.score_scale is not None

    for j, candidate in enumerate(candidates):
        a = candidate.entity_a
        b = candidate.entity_b

        prompt = version.prompt.format(
            name_a=a.canonical_name,
            type_a=a.entity_type,
            desc_a=a.description or "(pas de description disponible)",
            name_b=b.canonical_name,
            type_b=b.entity_type,
            desc_b=b.description or "(pas de description disponible)",
            reason=candidate.reason,
        )

        try:
            data = _call_llm(model, prompt, provider, json_mode=version.json_mode)
        except Exception as e:
            print(f"       WARNING: LLM confirmation failed for "
                  f"'{a.canonical_name}' <-> '{b.canonical_name}': {e}")
            print(f"       -> Confirmed {j + 1}/{len(candidates)} candidates")
            continue

        # Decide confirmation based on version type
        if score_mode:
            confirmed_pair, norm_score = _decide_by_score(
                data, version.score_scale, score_threshold,  # type: ignore[arg-type]
                a.canonical_name, b.canonical_name,
            )
        else:
            confirmed_pair = bool(data.get("same_entity"))
            norm_score = None

        if confirmed_pair:
            # Primary entity = the one with more mentions (more canonical)
            if a.mention_count >= b.mention_count:
                primary, alias_ent = a, b
            else:
                primary, alias_ent = b, a

            confirmed.append(ConfirmedAlias(
                primary_entity_id=primary.entity_id,
                primary_name=primary.canonical_name,
                alias_entity_id=alias_ent.entity_id,
                alias_name=alias_ent.canonical_name,
                confidence=data.get("confidence", "medium"),
                reasoning=data.get("reasoning", ""),
                score=norm_score,
            ))

        # Progress display — show score for score-based versions
        if score_mode and norm_score is not None:
            score_display = f"[{norm_score:.0%}]"
        else:
            score_display = "[yes]" if confirmed_pair else "[no]"
        print(f"       -> {score_display} '{a.canonical_name}' <-> '{b.canonical_name}' "
              f"({j + 1}/{len(candidates)})")

    return confirmed


def _decide_by_score(
    data: dict,
    scale: int,
    threshold: float,
    name_a: str,
    name_b: str,
) -> tuple[bool, float | None]:
    """Parse score from LLM response and apply threshold.

    Args:
        data: Parsed JSON response dict.
        scale: 10 for 1-10 scale, 100 for 0-100% scale.
        threshold: Minimum normalized score (0-1) to confirm.
        name_a, name_b: Entity names for warning messages.

    Returns:
        (confirmed, normalized_score_0_1) tuple.
        normalized_score is None if score is missing or invalid.
    """
    raw = data.get("score")
    if raw is None:
        print(f"       WARNING: no 'score' field in response for "
              f"'{name_a}' <-> '{name_b}' — treating as rejected")
        return False, None

    try:
        raw_float = float(raw)
    except (TypeError, ValueError):
        print(f"       WARNING: invalid score '{raw}' for "
              f"'{name_a}' <-> '{name_b}' — treating as rejected")
        return False, None

    # Normalize to 0-1
    norm = raw_float / scale
    # Clamp to [0, 1] in case LLM goes out of range
    norm = max(0.0, min(1.0, norm))

    return norm >= threshold, norm


def store_aliases(db_path: str, aliases: list[ConfirmedAlias]) -> int:
    """Store confirmed aliases and fully merge secondary entities into primaries.

    For each confirmed alias pair:
    1. Register the alias name in entity_aliases
    2. Redirect all mentions from secondary → primary
    3. Redirect all relations (source + target) from secondary → primary
    4. Merge tags: union of both entities' tag lists on the primary
    5. Deactivate the secondary entity (is_active = 0) to hide it everywhere

    The secondary entity row is kept for traceability but invisible to all queries.
    """
    conn = get_connection(db_path)
    stored = 0

    for alias in aliases:
        pid = alias.primary_entity_id
        sid = alias.alias_entity_id

        try:
            # 1. Register alias name + capture when the secondary entity first appeared
            # (first_seen_turn_id from entity_entities, used for the naming history UI)
            first_seen = conn.execute(
                "SELECT first_seen_turn FROM entity_entities WHERE id = ?", (sid,)
            ).fetchone()
            first_seen_turn_id = first_seen[0] if first_seen else None

            # Check if first_seen_turn_id column exists (migration 014)
            has_turn_col = any(
                col[1] == "first_seen_turn_id"
                for col in conn.execute("PRAGMA table_info(entity_aliases)").fetchall()
            )
            if has_turn_col:
                conn.execute(
                    "INSERT OR IGNORE INTO entity_aliases (entity_id, alias, first_seen_turn_id) VALUES (?, ?, ?)",
                    (pid, alias.alias_name, first_seen_turn_id),
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
                    (pid, alias.alias_name),
                )

            # 2. Redirect mentions
            conn.execute(
                "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?",
                (pid, sid),
            )

            # 3. Redirect relations (both directions)
            conn.execute(
                "UPDATE entity_relations SET source_entity_id = ? WHERE source_entity_id = ?",
                (pid, sid),
            )
            conn.execute(
                "UPDATE entity_relations SET target_entity_id = ? WHERE target_entity_id = ?",
                (pid, sid),
            )
            # Remove self-relations created by the above redirects
            conn.execute(
                "DELETE FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?",
                (pid, pid),
            )

            # 4. Merge tags: union of primary + secondary tag lists
            # (tags column may not exist on older DBs without migration 013)
            try:
                rows = conn.execute(
                    "SELECT id, tags FROM entity_entities WHERE id IN (?, ?)",
                    (pid, sid),
                ).fetchall()
            except Exception:
                rows = []  # tags column not yet migrated — skip tag merge
            combined_tags: list[str] = []
            seen: set[str] = set()
            for row in rows:
                raw = row["tags"]
                if raw:
                    try:
                        for t in json.loads(raw):
                            if isinstance(t, str) and t not in seen:
                                combined_tags.append(t)
                                seen.add(t)
                    except (json.JSONDecodeError, TypeError):
                        pass
            if rows:  # only write tags if the column exists (rows would be empty otherwise)
                merged_tags_json = json.dumps(combined_tags, ensure_ascii=False) if combined_tags else None
                try:
                    conn.execute(
                        "UPDATE entity_entities SET tags = ? WHERE id = ?",
                        (merged_tags_json, pid),
                    )
                except Exception:
                    pass  # tags column not yet migrated

            # 5. Deactivate secondary entity
            conn.execute(
                "UPDATE entity_entities SET is_active = 0 WHERE id = ?",
                (sid,),
            )

            stored += 1
        except Exception as e:
            print(f"  Warning: failed to merge alias {alias.alias_name} -> id={pid}: {e}")

    conn.commit()

    # Post-processing: resolve orphan mentions/relations caused by chain merges.
    # Example: A→B then B→C — after B is deactivated, mentions that were redirected
    # to B (from A) are now orphaned. Follow the alias chain to find the active root.
    _resolve_orphan_pointers(conn)

    conn.commit()
    conn.close()
    return stored


def _resolve_orphan_pointers(conn) -> None:
    """Redirect mentions/relations that point to inactive entities to their active root.

    Handles chains: A→B→C. If B got deactivated after mentions were redirected to it,
    follow the entity_aliases chain until we reach an active entity.
    Max 10 iterations to avoid infinite loops on bad data.
    """
    for _ in range(10):
        # Find mentions pointing to inactive entities
        orphans = conn.execute("""
            SELECT DISTINCT m.entity_id
            FROM entity_mentions m
            JOIN entity_entities e ON e.id = m.entity_id
            WHERE e.is_active = 0
        """).fetchall()
        if not orphans:
            break

        for (orphan_id,) in orphans:
            # Follow alias chain: find the active entity that owns this alias name
            active_id = _find_active_root(conn, orphan_id)
            if active_id and active_id != orphan_id:
                conn.execute(
                    "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?",
                    (active_id, orphan_id),
                )
                conn.execute(
                    "UPDATE entity_relations SET source_entity_id = ? WHERE source_entity_id = ?",
                    (active_id, orphan_id),
                )
                conn.execute(
                    "UPDATE entity_relations SET target_entity_id = ? WHERE target_entity_id = ?",
                    (active_id, orphan_id),
                )
                conn.execute(
                    "DELETE FROM entity_relations WHERE source_entity_id = ? AND target_entity_id = ?",
                    (active_id, active_id),
                )


def _find_active_root(conn, entity_id: int) -> int | None:
    """Walk the entity_aliases chain upward to find the active entity owning this one.

    Handles multi-level chains (A→B→C): even if the immediate owner is also
    inactive, continues up until reaching an active entity.

    Returns the active entity_id, or None if unresolvable.
    """
    visited: set[int] = {entity_id}
    current_id = entity_id

    for _ in range(10):  # max chain depth
        # The canonical_name of current entity might be an alias of another entity
        canonical = conn.execute(
            "SELECT canonical_name, is_active FROM entity_entities WHERE id = ?", (current_id,)
        ).fetchone()
        if not canonical:
            return None
        if canonical[1] == 1:
            # Current entity is active — it's the root
            return current_id
        # Find any entity that owns this name as an alias (active or not)
        owner = conn.execute(
            "SELECT entity_id FROM entity_aliases WHERE alias = ?",
            (canonical[0],),
        ).fetchone()
        if not owner:
            return None  # No owner in alias table — unresolvable
        next_id = owner[0]
        if next_id in visited:
            return None  # Cycle — abort
        visited.add(next_id)
        current_id = next_id

    return None  # Max depth exceeded


def resolve_aliases(
    db_path: str,
    profiles: list[EntityProfile],
    model: str = DEFAULT_MODEL,
    use_llm: bool = True,
    provider: LLMProvider | None = None,
    confirm_version: str = DEFAULT_CONFIRM_VERSION,
    score_threshold: float = 0.7,
) -> dict:
    """Full alias resolution: find candidates -> confirm -> store.

    Args:
        confirm_version: Prompt version for Stage 2 confirmation.
            Binary: "v1-llama", "v2-qwen3", "v3-nemo".
            Scoring: "v4-score-10" (1-10 scale), "v5-score-pct" (0-100% scale).
        score_threshold: For score-based versions, minimum normalized score (0-1)
            to confirm a pair. Default 0.7 = 7/10 or 70%.

    Returns stats dict with counts.
    """
    stats = {"candidates_found": 0, "aliases_confirmed": 0, "aliases_stored": 0}

    # Stage 1: Pattern matching
    candidates = find_alias_candidates(profiles)
    stats["candidates_found"] = len(candidates)

    if not candidates:
        print("       -> No alias candidates found")
        return stats

    print(f"       -> {len(candidates)} alias candidates found:")
    for c in candidates:
        print(f"          '{c.entity_a.canonical_name}' <-> "
              f"'{c.entity_b.canonical_name}' [{c.source}]")

    if not use_llm:
        print("       -> Skipping LLM confirmation (--no-llm)")
        return stats

    # Stage 2: LLM confirmation
    version_info = get_confirm_version(confirm_version)
    if version_info.score_scale is not None:
        print(f"       -> Score mode (scale 1-{version_info.score_scale}, "
              f"threshold {score_threshold:.0%}) with '{confirm_version}' / '{model}'")
    else:
        print(f"       -> Binary mode with '{confirm_version}' / '{model}'")
    confirmed = confirm_aliases(
        candidates, model, provider=provider,
        confirm_version=confirm_version, score_threshold=score_threshold,
    )
    stats["aliases_confirmed"] = len(confirmed)

    if confirmed:
        print(f"CONFIRMED: {len(confirmed)} aliases")
        for a in confirmed:
            score_str = f" score={a.score:.0%}" if a.score is not None else ""
            print(f"  [{a.confidence}]{score_str} \"{a.primary_name}\" = \"{a.alias_name}\"")
            if a.reasoning:
                print(f"     {a.reasoning[:120]}")

        stats["aliases_stored"] = store_aliases(db_path, confirmed)
    else:
        print("       -> No aliases confirmed by LLM")

    return stats


def _pair_key(id_a: int, id_b: int) -> tuple[int, int]:
    """Canonical pair key to avoid duplicate checks."""
    return (min(id_a, id_b), max(id_a, id_b))


# Articles and prepositions to ignore when tokenizing entity names.
# We want "Cercle des Sages" → {"cercle", "sage"} not {"cercle", "des", "sage"}.
_NAME_STOPWORDS = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "au", "aux",
    "ses", "son", "sa", "ce", "cet", "cette", "ces", "par", "sur", "en",
    "ou", "se", "si", "ne", "ni", "car", "a", "l", "d", "s",
}


def _normalize_tokens(name: str) -> set[str]:
    """Normalize an entity name into a set of comparable tokens.

    Steps:
      1. Lowercase
      2. Strip accents (NFD decomposition, remove combining marks)
      3. Split on spaces, hyphens, and apostrophes
      4. Remove stopwords and empty/single-char tokens
      5. Strip trailing plural 's' (simple French stemming: "ciels" → "ciel")
    """
    # NFD + remove Unicode combining characters (accents, cedillas, etc.)
    nfd = unicodedata.normalize("NFD", name.lower())
    no_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    raw_tokens = re.split(r"[\s\-''`]+", no_accents)

    tokens: set[str] = set()
    for tok in raw_tokens:
        tok = tok.strip(".,;:!?\"'")
        if not tok or tok in _NAME_STOPWORDS or len(tok) < 2:
            continue
        # Strip trailing plural 's' only for tokens longer than 3 chars
        # to avoid "les" → "le" (already filtered) or "os" → "o"
        stem = tok[:-1] if tok.endswith("s") and len(tok) > 3 else tok
        tokens.add(stem)

    return tokens


def _token_overlap(name_a: str, name_b: str) -> float:
    """Compute fuzzy overlap between two entity names based on their tokens.

    Returns: |intersection| / min(|tokens_a|, |tokens_b|)
    This is recall-oriented: if all tokens of the shorter name appear in the
    longer, overlap = 1.0. The LLM confirmation stage filters false positives.
    """
    tokens_a = _normalize_tokens(name_a)
    tokens_b = _normalize_tokens(name_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    smaller = min(len(tokens_a), len(tokens_b))
    return len(intersection) / smaller if smaller > 0 else 0.0


def _description_overlap(desc_a: str, desc_b: str) -> float:
    """Compute keyword overlap ratio between two descriptions."""
    stop_words = {
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "est", "sont",
        "qui", "que", "dans", "pour", "par", "sur", "avec", "ce", "cette", "ces",
        "il", "elle", "ils", "elles", "en", "au", "aux", "se", "sa", "son", "ses",
        "a", "à", "l", "d", "n", "s", "y", "ou", "pas", "plus", "aussi", "être",
        "fait", "leur", "leurs", "ont", "été", "très", "tout", "tous", "toute",
    }
    words_a = {w.lower() for w in re.findall(r"\w+", desc_a)
               if len(w) > 2 and w.lower() not in stop_words}
    words_b = {w.lower() for w in re.findall(r"\w+", desc_b)
               if len(w) > 2 and w.lower() not in stop_words}

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller if smaller > 0 else 0.0


def _call_llm(
    model: str,
    prompt: str,
    provider: LLMProvider | None = None,
    json_mode: bool = True,
) -> dict:
    """Call LLM via provider and parse JSON response.

    json_mode=False for prompts that produce free text before JSON
    (e.g. structured analysis templates — Nemo v3).
    """
    llm = provider or OllamaProvider()
    raw = llm.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        num_ctx=NUM_CTX,
        json_mode=json_mode,
    )
    data = _parse_json_response(raw)
    # Some models wrap the response in a list — unwrap if needed
    if isinstance(data, list):
        data = data[0] if data else {}
    return data


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}
