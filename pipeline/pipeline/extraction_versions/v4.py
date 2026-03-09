"""v4-strict-recall: maximum recall with anti-hallucination guard.

Strategy: exhaustive category checklist + "copy from text" rule.
Also includes V7_V4T0 (v4 + temperature 0, single variable change).
"""

from .base import ExtractionVersion

_V4_SYSTEM_QWEN = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE ABSOLUE : Extrais UNIQUEMENT des noms qui apparaissent TEXTUELLEMENT dans le passage. JAMAIS de paraphrase, synonyme, ou invention. Si le texte dit "Argile Vivante", extrais "Argile Vivante" -- pas "Argile qui vit", pas "argile".

METHODE : Lis le texte, puis passe en revue CHAQUE categorie ci-dessous. Pour chaque categorie, relis le texte et cherche TOUTES les mentions.

CATEGORIES A VERIFIER (dans cet ordre) :
1. CASTES : noms avec tirets (Sans-ciels, Passes-bien, Ciels-clairs), "Enfants de/du/des..." (Enfants du Courant, Enfants des Echos), "Caste de..."
2. PERSONNES/GROUPES : noms avec tirets (Ailes-Grises), titres de groupes (Faucons Chasseurs, Proclamateurs, Traqueurs, Porteurs de Flamme)
3. INSTITUTIONS : "Cercle des...", "Hall des...", "Tribunal des...", "Assemblee des...", "Maison des...", "Confluence des...", "Conseil..."
4. LIEUX : noms propres (Gouffre Humide, Confluence, Arene), "Zone + adjectif" (Zone chaude, Zone froide), "Antres des...", tout lieu avec majuscule
5. TECHNOLOGIES : objets nommes (Argile Vivante, Rhombes, Glyphes du Gouffre, Ideoglyphes, Lances, Gourdins, Pieux, Pilotis, Blocs standardises, Lait de Pierre)
6. CROYANCES/LOIS : "Loi de/du...", "Culte des...", "Rituel du...", "Yeux de..."
7. EVENEMENTS : "Grande Prospection", "Blanc sur Blanc", "Maladie des..."
8. CIVILISATIONS : Cheveux de Sang, Nanzagouets, Confluents, Siliaska, etc.
9. CREATURES : Regards-Libres, Nantons

INTERDIT :
- Inventer des entites absentes du texte
- Paraphraser (le nom doit etre COPIE du texte tel quel)
- Extraire des mots generiques isoles : homme, femme, eau, bois, pierre, riviere, village, tribu, peuple
- Extraire des pronoms : lui, eux, toi, nous

/no_think
Reponds UNIQUEMENT en JSON valide. Pas de texte avant ou apres le JSON.

Exemple :
Texte : "Les Sans-ciels et les Enfants du Courant se reunissent a l'Arene pres de la Zone chaude. Ailes-Grises brandit les Lances devant le Cercle des Sages. Les Proclamateurs invoquent la Loi du Sang et de la Bete."

Reponse :
{
  "technologies": ["Lances"],
  "resources": [],
  "beliefs": ["Loi du Sang et de la Bete"],
  "geography": ["Arene", "Zone chaude"],
  "entities": [
    {"name": "Sans-ciels", "type": "caste", "context": "se reunissent a l'Arene"},
    {"name": "Enfants du Courant", "type": "caste", "context": "se reunissent a l'Arene"},
    {"name": "Arene", "type": "place", "context": "lieu de reunion"},
    {"name": "Zone chaude", "type": "place", "context": "pres de l'Arene"},
    {"name": "Ailes-Grises", "type": "person", "context": "brandit les Lances"},
    {"name": "Lances", "type": "technology", "context": "brandies par Ailes-Grises"},
    {"name": "Cercle des Sages", "type": "institution", "context": "devant le Cercle"},
    {"name": "Proclamateurs", "type": "person", "context": "invoquent la Loi"},
    {"name": "Loi du Sang et de la Bete", "type": "belief", "context": "invoquee par Proclamateurs"}
  ]
}
NOTE : 9 entites extraites pour 3 phrases. Sois aussi exhaustif."""

_V4_SYSTEM_LLAMA = """Tu es un extracteur d'entites pour un jeu de civilisation. Texte narratif -> JSON.

REGLE : Extrais UNIQUEMENT des noms qui apparaissent TEXTUELLEMENT. Jamais de paraphrase ou invention.
Passe en revue chaque categorie : castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures.
Sois exhaustif -- chaque mention compte.

Reponds UNIQUEMENT en JSON valide."""

_V4_FACTS_PROMPT = """Texte :
{text}

Passe en revue CHAQUE categorie (castes, personnes, institutions, lieux, technologies, croyances, evenements, civilisations, creatures) et extrais TOUT.

JSON UNIQUEMENT :
{{
  "technologies": ["noms exacts du texte"],
  "resources": ["noms exacts du texte"],
  "beliefs": ["noms exacts du texte"],
  "geography": ["noms exacts du texte"],
  "entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}"""

_V4_ENTITY_PROMPT = """Texte :
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

JSON :
{{"entities": [{{"name": "Nom COPIE du texte", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Si aucune entite, retourne {{"entities": []}}."""

V4_STRICT_RECALL = ExtractionVersion(
    name="v4-strict-recall",
    description="Recall maximum -- checklist par categorie + anti-hallucination",
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V4_FACTS_PROMPT,
    entity_prompt=_V4_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# v7-v4t0: v4 exact + temperature 0 (single variable change).
# Defined inline in _VERSIONS dict in the source; extracted here as a named variable.
V7_V4T0 = ExtractionVersion(
    name="v7-v4t0",
    description="v4 exact + temperature 0 (single variable change)",
    temperature=0.0,
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V4_FACTS_PROMPT,
    entity_prompt=_V4_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V4: dict[str, ExtractionVersion] = {
    "v4-strict-recall": V4_STRICT_RECALL,
    "v7-v4t0": V7_V4T0,
}
