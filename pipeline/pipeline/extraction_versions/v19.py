"""v19-recall: v18.4.2-nemo with relaxed social-role NON lists.

Root cause of T05/T04 under-extraction: _V18_FACTS_PROMPT and _V18_ENTITY_PROMPT
had "artisans, chasseurs, pecheurs, tribus" explicitly in the NON list, and
"mots communs" as a catch-all. This blocked game-specific social group names
(marginaux, artisans as a caste, tribunal special) that use common French vocab.

Fix: remove social role words from NON lists, add NOTE clarifying they can be
named castes/groups. entity_filter.py handles structural noise; semantic noise
(truly generic words) is handled in post-processing.
"""

from .base import ExtractionVersion
from .v18 import (
    _V18_SYSTEM,
    _V18_FACTS_PROMPT,
    _V18_ENTITY_PROMPT,
    _V18_4_1_FOCUS_PROMPT,
    _V18_4_1_VALIDATE_PROMPT,
)

# v19 reuses v18 prompts which already have the NOTE about social roles.
# The "relaxed" change was applied directly to _V18_FACTS_PROMPT/_V18_ENTITY_PROMPT
# (those prompts already contain the NOTE about marginaux/artisans/pecheurs/chasseurs).
V19_RECALL = ExtractionVersion(
    name="v19-recall",
    description=(
        "v18.4.2-nemo with relaxed social-role NON lists. Removes 'artisans, chasseurs, "
        "pecheurs, tribus' from NON mots communs — these can be named castes. Adds NOTE "
        "in all 3 extraction prompts clarifying social groups may be named entities."
    ),
    # _V18_SYSTEM unchanged — its JAMAIS list only blocks clearly generic single words
    system_prompt=_V18_SYSTEM,
    # facts + entity prompts now use the updated NON lists (modified in-place above)
    facts_prompt=_V18_FACTS_PROMPT,
    entity_prompt=_V18_ENTITY_PROMPT,
    # focus prompt also updated (artisans removed from NON)
    focus_prompt=_V18_4_1_FOCUS_PROMPT,
    validate_prompt=_V18_4_1_VALIDATE_PROMPT,
    validate_model="mistralai/mistral-nemo",
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V19: dict[str, ExtractionVersion] = {
    "v19-recall": V19_RECALL,
}
