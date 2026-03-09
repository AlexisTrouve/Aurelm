"""v9-neginuser: v4 system prompt (concise, proven) + temp 0 +
negative examples in the USER prompt instead of system prompt.

Lesson from v8: system prompt too big -> LLM drowns -> 0 output.
"""

from .base import ExtractionVersion
from .v4 import _V4_SYSTEM_QWEN, _V4_SYSTEM_LLAMA

_V9_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie (castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures) et extrais TOUT.

ATTENTION -- erreurs courantes a eviter :
- "Chef du Cercle des Sages" -> extrais "Cercle des Sages" (pas le titre)
- "argile qui vit" -> extrais "Argile Vivante" (nom exact, pas paraphrase)
- "maison", "foyer", "briques", "outils" seuls -> N'EXTRAIS PAS (trop generique)
- "Rhombes geants" -> extrais "Rhombes" (nom exact sans adjectif ajoute)

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V9_ENTITY_PROMPT = """Texte :
{text}

CHECKLIST -- relis le texte pour chaque categorie et extrais TOUT ce que tu trouves :
- Castes ? (noms avec tirets, "Enfants de/du...", "Caste de...")
- Personnes/groupes ? (noms avec tirets, titres de groupes)
- Institutions ? ("Cercle des...", "Hall des...", "Tribunal des...", "Maison des...")
- Lieux ? (noms propres, "Zone + adjectif", "Antres des...")
- Technologies/outils ? (tout objet, technique, invention nomme)
- Croyances/lois ? ("Loi de...", "Rituel du...", "Culte des...")
- Evenements ?
- Civilisations ?
- Creatures ?

ATTENTION : pas de mots generiques seuls (maison, foyer, briques), pas de "Chef du X", pas de paraphrases.

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V9_NEGINUSER = ExtractionVersion(
    name="v9-neginuser",
    description="v4 system (concis) + temp 0 + negative examples dans user prompt",
    temperature=0.0,
    # Reuse v4 system prompt -- proven to work, right size for 8B model
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V9_FACTS_PROMPT,
    entity_prompt=_V9_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V9: dict[str, ExtractionVersion] = {
    "v9-neginuser": V9_NEGINUSER,
}
