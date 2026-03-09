"""v2-fewshot: system prompt + few-shot example + paragraph chunking.

System prompt adapte par modele (llama vs qwen3).
"""

from .base import ExtractionVersion

# Llama 3.1 — needs explicit encouragement to extract enough
_V2_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Tu recois du texte narratif et tu retournes du JSON.

Regles :
- Extrais TOUTES les entites nommees : institutions, castes, technologies, outils, lieux, civilisations, croyances, rituels, evenements, personnes, creatures.
- Inclus les outils simples (gourdins, lances, pieux, rhombes) et les castes (Caste de l'Air, Ciels-clairs, Sans-ciels).
- N'extrais JAMAIS : pronoms (lui, eux, toi, nous, elle), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere, nature, oiseaux, arbre), phrases completes, descriptions generiques.
- Chaque entite doit avoir un nom exact tel qu'il apparait dans le texte.
- Reponds UNIQUEMENT en JSON valide, rien d'autre.

Exemple :
Texte : "Le Cercle des Sages a ordonne la fabrication de gourdins et de lances. Les Faucons Chasseurs partent vers le Gouffre Humide. La Caste de l'Air refuse de suivre les Ciels-clairs dans leur quete."

Reponse :
{
  "technologies": ["gourdins", "lances"],
  "resources": [],
  "beliefs": [],
  "geography": ["Gouffre Humide"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "ordonne la fabrication"},
    {"name": "Gourdins", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Lances", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "partent vers le Gouffre"},
    {"name": "Gouffre Humide", "type": "place", "context": "destination des Faucons"},
    {"name": "Caste de l'Air", "type": "caste", "context": "refuse de suivre"},
    {"name": "Ciels-clairs", "type": "caste", "context": "quete refusee"}
  ]
}"""

# Qwen3 — much stricter, needs to be told what NOT to extract
_V2_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE CRITIQUE : Extrais UNIQUEMENT les NOMS PROPRES et TERMES SPECIFIQUES au jeu. Pas de noms communs francais.

EXTRAIS (noms propres du jeu) :
- Institutions nommees : "Cercle des Sages", "Hall des Serments", "Tribunal des Moeurs", "Conseil du village"
- Castes nommees : "Ciels-clairs", "Sans-ciels", "Caste de l'Air", "Enfants du Courant", "Faconneurs de Pierre"
- Technologies nommees : "Argile Vivante", "Lait de Pierre", "Rhombes", "Glyphes du Gouffre", "Ideoglyphes"
- Outils specifiques nommes : "Gourdins", "Lances", "Pieux", "Pointes de fleches"
- Lieux propres : "Gouffre Humide", "Gorge Profonde", "Morsure-des-Ancetres", "Route-riviere"
- Civilisations : "Cheveux de Sang", "Nanzagouets", "Confluents"
- Personnes nommees : "Ailes-Grises", "Faucons Chasseurs", "Voix de l'Aurore", "Porteurs de Flamme"
- Creatures nommees : "Regards-Libres", "Nantons"
- Croyances/rituels nommes : "Loi du Sang et de la Bete", "Rituel du Regard Partage", "Culte des Ancetres"
- Evenements nommes : "Grande Prospection", "Blanc sur Blanc", "Maladie des Antres"

N'EXTRAIS JAMAIS (noms communs francais, meme s'ils apparaissent dans le texte) :
- Generiques : homme, femme, enfant, tribu, peuple, vallee, riviere, montagne, village, ciel, cave, galerie, surface, grotte, antre, autels
- Animaux generiques : oiseaux, poissons, animaux, grues, mollusques, bete
- Ressources generiques : graines, baies, eau, bois, pierre, nourriture
- Activites : chasse, peche, rituels, expedition, celebration, ecriture, gravure, creusage
- Croyances vagues : esprits, ancetres, mission sacree, lois anciennes, rituels sacres
- Descriptions : vieil homme, creature, basses terres, large vallee, etendue d'eau
- Pronoms : lui, eux, toi, nous, elle, on, il

TEST : Si le mot existe dans un dictionnaire francais standard et n'est PAS un nom propre invente pour ce jeu, NE L'EXTRAIS PAS.

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Le Cercle des Sages a ordonne la fabrication de gourdins et de lances. Les Faucons Chasseurs partent vers le Gouffre Humide avec des poissons seches et de l'eau."

Reponse :
{
  "technologies": ["gourdins", "lances"],
  "resources": [],
  "beliefs": [],
  "geography": ["Gouffre Humide"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "ordonne la fabrication"},
    {"name": "Gourdins", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Lances", "type": "technology", "context": "fabrication ordonnee"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "partent vers le Gouffre"},
    {"name": "Gouffre Humide", "type": "place", "context": "destination des Faucons"}
  ]
}
NOTE : "poissons", "eau" ne sont PAS extraits car ce sont des noms communs."""

_V2_FACTS_PROMPT = """Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/outils"],
  "resources": ["ressources"],
  "beliefs": ["croyances/rituels"],
  "geography": ["lieux"],
  "entities": [{{"name": "Nom exact", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V2_ENTITY_PROMPT = """Texte :
{text}

Extrais TOUTES les entites nommees en JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event|person|creature|resource", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V2_FEWSHOT = ExtractionVersion(
    name="v2-fewshot",
    description="System prompt + few-shot + chunking par paragraphes",
    system_prompt=_V2_SYSTEM_LLAMA,  # default fallback
    system_prompt_by_model={
        "qwen3": _V2_SYSTEM_QWEN,
        "llama": _V2_SYSTEM_LLAMA,
    },
    facts_prompt=_V2_FACTS_PROMPT,
    entity_prompt=_V2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V2: dict[str, ExtractionVersion] = {
    "v2-fewshot": V2_FEWSHOT,
}
