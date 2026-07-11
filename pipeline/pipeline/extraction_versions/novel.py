"""novel extraction version — non-civ corpus (customer #1: the roman).

This is the first NON-civ extraction profile. It selects the `novel` domain
profile (domain_profile.NOVEL_PROFILE), so the ontology gate accepts narrative
entity types (person/place/creature/event/group/object/belief) and the profiling
stage asks for narrative relations (parent-de, mentor-de, héritier-du-geste…).

Prompts are French (the roman's canonical chapters are French) and person-
centred (the mindmap targets "les persos, pas le reste"). They return only the
`entities` list — the civ-specific facts arrays (technologies/resources/…) are
irrelevant for a novel and the parser defaults them to empty.

STATUS: structural starting point (P2a). Prompt QUALITY is tuned against real
chapters in a later LLM pass (P2b); the low-trust rule from the wishlist applies
— intimate links (who is whose parent) must not be hallucinated.
"""
from .base import ExtractionVersion

_NOVEL_SYSTEM = """Tu extrais les entités nommées d'un roman. Règles :
- Extrais le nom EXACT tel qu'il apparaît (majuscules, tirets, forme composée complète).
- Une seule forme par entité (ne mélange pas singulier et pluriel du même nom).
- Priorité aux PERSONNAGES : toute personne nommée ou clairement désignée.
- Aussi : lieux nommés, créatures nommées, événements nommés, peuples/lignées, objets nommés, croyances nommées.
- JAMAIS de pronoms (il, elle, eux), de mots génériques seuls (l'homme, la femme, la rivière, le village), ni de descriptions/phrases.
- JAMAIS de préfixe "Un/Une/Le/La/Les" dans le nom extrait."""

_NOVEL_FACTS_PROMPT = """Extrait les entités nommées de ce passage de roman. Réponds UNIQUEMENT avec du JSON.

Texte :
{text}

Réponds avec ce JSON UNIQUEMENT :
{{"entities": [{{"name": "Nom propre", "type": "person|place|creature|event|group|object|belief", "context": "phrase courte"}}]}}

OUI : personnages nommés, lieux nommés, créatures nommées (ex. une bête compagnon), événements nommés, peuples ou lignées, objets nommés, croyances/rites nommés.
NON : pronoms, mots génériques seuls (homme, femme, rivière, forêt, village), descriptions longues, métaphores.
NON : variantes d'un même nom — extrais UNE seule forme (la plus complète).
Si rien, retourne {{"entities": []}}."""

_NOVEL_ENTITY_PROMPT = """Extrait UNIQUEMENT les personnages nommés de ce passage de roman, plus les lieux, créatures, peuples et objets nommés. JSON uniquement.

Texte :
{text}

Réponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "person|place|creature|group|object", "context": "phrase courte"}}]}}

OUI : toute personne nommée ou désignée par un nom propre ; lieux, créatures, peuples/lignées, objets nommés.
NON : mots génériques seuls, pronoms, descriptions.
Si rien, retourne {{"entities": []}}."""

NOVEL_V1 = ExtractionVersion(
    name="novel-v1",
    description=(
        "First non-civ extraction profile (customer #1: the roman). Uses the "
        "'novel' domain profile (narrative ontology). Person-centred French "
        "prompts returning only the entities list. Structural baseline — prompt "
        "quality tuned against real chapters in a later LLM pass."
    ),
    profile="novel",
    system_prompt=_NOVEL_SYSTEM,
    facts_prompt=_NOVEL_FACTS_PROMPT,
    entity_prompt=_NOVEL_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_NOVEL: dict[str, ExtractionVersion] = {
    "novel-v1": NOVEL_V1,
}
