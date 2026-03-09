"""v1-baseline: everything in the user prompt, no system, no chunking."""

from .base import ExtractionVersion

_V1_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/savoir-faire adoptes"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI : "Cercle des Sages", "Argile Vivante", "Gouffre Humide", "Faucons Chasseurs", "Caste de l'Air", "Gourdins", "Lances", "Ciels-clairs".
NON : pronoms (lui, eux, toi, nous), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere), phrases longues."""

_V1_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Rhombes", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang", "Loi du Sang".
NON : mots communs (riviere, vallee, village, nature, neige, vent, nuit, homme, femme, artisans, pecheurs, tribus), pronoms (toi, lui, eux).
Si rien, retourne {{"entities": []}}."""

V1_BASELINE = ExtractionVersion(
    name="v1-baseline",
    description="Prompt unique, pas de system, pas de chunking",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=False,
)

_VERSIONS_V1: dict[str, ExtractionVersion] = {
    "v1-baseline": V1_BASELINE,
}
