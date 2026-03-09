"""v12-think: v11 base + thinking tree in user prompt.

The LLM must first list ALL candidates, then decide for each.
Reasoning forced in the JSON output via "keep" and "reason" fields.
num_predict increased to 6000 for reasoning budget.
"""

from .base import ExtractionVersion

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

_VERSIONS_V12: dict[str, ExtractionVersion] = {
    "v12-think": V12_THINK,
}
