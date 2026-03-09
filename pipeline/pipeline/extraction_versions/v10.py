"""v10-mark: v7 base + GPT-NER style marking as 3rd LLM call.

The LLM rewrites the text with @@entity## markers — more natural for
generative models, catches entities the JSON calls miss.
"""

from .base import ExtractionVersion
from .v4 import _V4_SYSTEM_QWEN, _V4_SYSTEM_LLAMA, _V4_FACTS_PROMPT, _V4_ENTITY_PROMPT

_V10_MARK_SYSTEM_QWEN = """Tu recois un texte de jeu de civilisation. Reecris-le en marquant CHAQUE entite nommee avec @@nom## .

Entites a marquer : castes, personnes, groupes, institutions, lieux, technologies, outils, croyances, lois, evenements, civilisations, creatures.

NE marque PAS : pronoms (lui, eux), mots generiques seuls (homme, village, riviere, maison).

/no_think
Reecris le texte COMPLET. Ne saute aucune phrase."""

_V10_MARK_SYSTEM_LLAMA = _V10_MARK_SYSTEM_QWEN

_V10_MARK_PROMPT = """Texte :
{text}

Reecris ce texte en marquant chaque entite nommee avec @@nom## . Garde le texte complet, change SEULEMENT en ajoutant les marqueurs.

Exemple :
"Les Sans-ciels se reunissent a l'Arene. Ailes-Grises brandit les Lances."
->
"Les @@Sans-ciels## se reunissent a l'@@Arene##. @@Ailes-Grises## brandit les @@Lances##."

Maintenant, reecris le texte ci-dessus avec les marqueurs :"""

V10_MARK = ExtractionVersion(
    name="v10-mark",
    description="v7 + GPT-NER marking (3e appel LLM par chunk)",
    temperature=0.0,
    system_prompt=_V4_SYSTEM_LLAMA,
    system_prompt_by_model={
        "qwen3": _V4_SYSTEM_QWEN,
        "llama": _V4_SYSTEM_LLAMA,
    },
    facts_prompt=_V4_FACTS_PROMPT,
    entity_prompt=_V4_ENTITY_PROMPT,
    mark_prompt=_V10_MARK_PROMPT,
    mark_system_prompt=_V10_MARK_SYSTEM_LLAMA,
    mark_system_prompt_by_model={
        "qwen3": _V10_MARK_SYSTEM_QWEN,
        "llama": _V10_MARK_SYSTEM_LLAMA,
    },
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V10: dict[str, ExtractionVersion] = {
    "v10-mark": V10_MARK,
}
