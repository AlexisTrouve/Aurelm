"""v6-combo: best of v4 (checklist+/no_think) + v5 (temp 0, format schema).

Lessons: /no_think mandatory (otherwise thinking burns num_predict and JSON truncates),
format schema eliminates JSON malformed, temp 0 = deterministic,
prompt shorter because schema handles the structure.
"""

from .base import ExtractionVersion
from .v5 import _V5_FACTS_SCHEMA, _V5_ENTITY_SCHEMA

# Reuse v5 schemas -- they work, the problem was thinking mode
_V6_FACTS_SCHEMA = _V5_FACTS_SCHEMA
_V6_ENTITY_SCHEMA = _V5_ENTITY_SCHEMA

_V6_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent MOT POUR MOT dans le texte. ZERO invention, ZERO paraphrase.

METHODE -- pour CHAQUE categorie, relis le texte et note TOUTES les occurrences :
1. CASTES : tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des...", "Caste de..."
2. PERSONNES/GROUPES : tirets (Ailes-Grises), groupes nommes (Faucons Chasseurs, Proclamateurs, Traqueurs)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des..."
4. LIEUX : noms propres (Gouffre Humide, Arene, Confluence), "Zone + adjectif", "Antres des..."
5. TECHNOLOGIES : tout objet/outil nomme (Argile Vivante, Rhombes, Lances, Pilotis, Blocs standardises)
6. CROYANCES/LOIS : "Loi de/du...", "Rituel du...", "Yeux de...", "Culte des..."
7. EVENEMENTS : Grande Prospection, Blanc sur Blanc, etc.
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

INTERDIT : mots generiques isoles (homme, femme, riviere, village, tribu, maison, foyer, outils, briques), pronoms, entites inventees, "Chef du X" (extrais X pas "Chef du X").

Chaque mention compte, meme une seule occurrence.

/no_think"""

_V6_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation.
Extrais UNIQUEMENT des noms MOT POUR MOT du texte. Jamais d'invention.
Verifie chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
Chaque mention compte."""

# Prompts plus courts -- le format schema gere la structure, le prompt se concentre sur la tache
_V6_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie et extrais TOUTES les mentions. Noms COPIES mot pour mot du texte.

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V6_ENTITY_PROMPT = """Texte :
{text}

Relis le texte categorie par categorie. Extrais CHAQUE entite nommee, meme mentionnee une seule fois.
Noms COPIES mot pour mot du texte.

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V6_COMBO = ExtractionVersion(
    name="v6-combo",
    description="v4 checklist + /no_think + temp 0 + short prompt -- no format schema (causes truncation)",
    temperature=0.0,
    system_prompt=_V6_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V6_SYSTEM_QWEN,
        "llama": _V6_SYSTEM_LLAMA,
    },
    facts_prompt=_V6_FACTS_PROMPT,
    entity_prompt=_V6_ENTITY_PROMPT,
    # No format schema -- conflicts with /no_think on qwen3, causes truncated output
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V6: dict[str, ExtractionVersion] = {
    "v6-combo": V6_COMBO,
}
