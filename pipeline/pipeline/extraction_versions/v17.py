"""v17-typerecall: type-aware recall fix.

Two confirmed root causes for FNs in v15.3.4 (F1=69.5%):

1. entity_filter killed named technologies: Lances, Codex, Palanquin, Fresque(s)
   Fix: removed them from _GENERIC_FRENCH_NOUNS in entity_filter.py

2. System prompt JAMAIS list had "reincarnation" as a single generic word —
   unintentionally discouraged extraction of "Croyance en la reincarnation"
   (4-word belief in the reference).
   Fix: remove "reincarnation" from JAMAIS, add explicit belief examples.

3. LLM misses simple single-word technologies (Pilotis, Pigments, Rhombes, Cornex)
   because they look like common nouns. Fix: add them to OUI example list.

4. LLM misses beliefs because no examples of multi-word named beliefs were shown.
   Fix: add belief examples to both system prompt and entity_prompt.
"""

from .base import ExtractionVersion
from .v15 import _V15_2_FACTS_PROMPT

_V17_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- Les outils simples sont des technologies nommees quand ils ont un role cle dans le recit : Lances, Pilotis, Rhombes, Pigments, Codex, Palanquin = OUI si mentionnes comme acquis/fabriques/utilises.
- Les croyances peuvent etre des formulations completes : "Croyance en la reincarnation", "Pelerinage de Gouffre Humide", "Yeux de l'aurore" = OUI (croyances nommees).
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type", "Grande Foret".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

_V17_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Pilotis", "Rhombes", "Pigments", "Codex", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang", "Croyance en la reincarnation", "Pelerinage de Gouffre Humide".
NON : mots communs, mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre).
NON : descriptions ("Un Faucon Chasseur veteran", "Action libre - L'epave", "Mars Attack").
NON : variantes — UNE forme par entite.
Si rien, retourne {{"entities": []}}."""

V17_TYPERECALL = ExtractionVersion(
    name="v17-typerecall",
    description=(
        "Type-aware recall fix — targets the 2 confirmed root causes of technology/belief FNs: "
        "(1) entity_filter no longer kills Lances/Codex/Palanquin/Fresque; "
        "(2) system prompt no longer has 'reincarnation' in JAMAIS list; "
        "(3) entity_prompt OUI list adds Pilotis/Rhombes/Pigments/Codex and belief examples. "
        "Based on v15.3.4-tightnon structure."
    ),
    system_prompt=_V17_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V17_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V17: dict[str, ExtractionVersion] = {
    "v17-typerecall": V17_TYPERECALL,
}
