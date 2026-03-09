"""v11-heavy: heavy prompt, agnostic to any specific civilization.

Zero game-specific examples — describes the TASK, not the answers.
Heavy user prompt with IMPORTANT/CRITICAL markers.
System prompt short, user prompt hammers the rules.
"""

from .base import ExtractionVersion

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

_VERSIONS_V11: dict[str, ExtractionVersion] = {
    "v11-heavy": V11_HEAVY,
}
