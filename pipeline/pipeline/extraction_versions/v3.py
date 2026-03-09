"""v3-recall: optimized for high recall without sacrificing too much precision.

Key changes vs v2: softer exclusion list, richer few-shot, explicit
instruction to extract ALL mentions even minor ones.
"""

from .base import ExtractionVersion

_V3_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

MISSION : Extrais TOUTES les entites nommees du texte. Prefere extraire trop que pas assez. En cas de doute, EXTRAIS.

TYPES VALIDES : person, place, technology, institution, resource, creature, event, civilization, caste, belief

CE QUI EST UNE ENTITE (extrais toujours) :
- Noms avec majuscule ou tirets : "Ailes-Grises", "Sans-ciels", "Passes-bien", "Regards-Libres"
- Groupes nommes : "Faucons Chasseurs", "Enfants du Courant", "Enfants des Echos", "Proclamateurs", "Traqueurs"
- Institutions : "Cercle des Sages", "Hall des Serments", "Confluence des Echanges", "Tribunal des Moeurs"
- Lieux nommes, meme descriptifs : "Zone chaude", "Zone froide", "Zone humide", "Zone seche", "Antres des Echos", "Basses terres"
- Technologies et outils : "Argile Vivante", "Lances", "Gourdins", "Rhombes", "Ideoglyphes", "Pilotis", "Blocs standardises"
- Croyances et lois : "Loi du Sang et de la Bete", "Yeux de l'aurore", "Culte des Ancetres"
- Evenements : "Grande Prospection", "Rituel du Regard Partage", "Blanc sur Blanc"
- Civilisations : "Cheveux de Sang", "Nanzagouets", "Confluents", "Siliaska"

CE QUI N'EST PAS UNE ENTITE (n'extrais jamais) :
- Pronoms : lui, eux, toi, nous, elle, on, il
- Mots isoles generiques sans contexte de jeu : homme, femme, eau, bois, pierre, riviere, montagne, village
- Phrases completes ou descriptions longues

ATTENTION AUX PIEGES :
- "Proclamateurs" = entite (groupe nomme), pas un mot generique
- "Lances" = entite (technologie du jeu), pas juste un nom commun
- "Zone chaude" = entite (lieu dans la Maison des Decouvertes), pas une description
- "Antres des Echos" = entite (lieu), meme si "antre" est un mot courant
- "Basses terres" = entite (region), meme si ca ressemble a une description
- "Passes-bien" = entite (caste), meme si ca ne ressemble pas a un nom propre

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Le Cercle des Sages se reunit dans la Zone chaude de la Maison des Decouvertes. Les Passes-bien et les Sans-ciels debattent. Les Proclamateurs annoncent que les Lances seront distribuees aux Faucons Chasseurs. Ailes-Grises invoque la Loi du Sang."

Reponse :
{
  "technologies": ["Lances"],
  "resources": [],
  "beliefs": ["Loi du Sang"],
  "geography": ["Zone chaude", "Maison des Decouvertes"],
  "entities": [
    {"name": "Cercle des Sages", "type": "institution", "context": "se reunit"},
    {"name": "Zone chaude", "type": "place", "context": "dans la Maison des Decouvertes"},
    {"name": "Maison des Decouvertes", "type": "institution", "context": "lieu de reunion"},
    {"name": "Passes-bien", "type": "caste", "context": "debattent"},
    {"name": "Sans-ciels", "type": "caste", "context": "debattent"},
    {"name": "Proclamateurs", "type": "person", "context": "annoncent la distribution"},
    {"name": "Lances", "type": "technology", "context": "distribuees"},
    {"name": "Faucons Chasseurs", "type": "person", "context": "recoivent les lances"},
    {"name": "Ailes-Grises", "type": "person", "context": "invoque la Loi"},
    {"name": "Loi du Sang", "type": "belief", "context": "invoquee par Ailes-Grises"}
  ]
}"""

_V3_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

MISSION : Extrais TOUTES les entites nommees. En cas de doute, extrais.

Types : person, place, technology, institution, resource, creature, event, civilization, caste, belief

Inclus : noms avec majuscules/tirets, groupes nommes, institutions, lieux (meme descriptifs comme "Zone chaude"), technologies/outils, croyances, evenements, civilisations.
Exclus : pronoms, mots isoles generiques (homme, femme, eau, bois, pierre).

Reponds UNIQUEMENT en JSON valide."""

_V3_FACTS_PROMPT = """Texte :
{text}

Extrais TOUTES les entites et faits. Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/outils nommes"],
  "resources": ["ressources nommees"],
  "beliefs": ["croyances/rituels/lois nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom exact du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

IMPORTANT : N'oublie aucune entite. Chaque nom propre, groupe, lieu, institution, technologie, caste mentionne dans le texte doit apparaitre."""

_V3_ENTITY_PROMPT = """Texte :
{text}

Extrais TOUTES les entites nommees. Cherche particulierement :
- Castes et groupes sociaux (noms avec tirets, "Enfants de/du...")
- Lieux specifiques (meme "Zone X", "Antres de...")
- Technologies et outils (meme simples comme "Lances", "Pilotis")
- Institutions et lois
- Personnes et creatures nommees

JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event|person|creature|resource", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V3_RECALL = ExtractionVersion(
    name="v3-recall",
    description="Optimise pour le recall -- prompt plus permissif, few-shot riche",
    system_prompt=_V3_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V3_SYSTEM_QWEN,
        "llama": _V3_SYSTEM_LLAMA,
    },
    facts_prompt=_V3_FACTS_PROMPT,
    entity_prompt=_V3_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V3: dict[str, ExtractionVersion] = {
    "v3-recall": V3_RECALL,
}
