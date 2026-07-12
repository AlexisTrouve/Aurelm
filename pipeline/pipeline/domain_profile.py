"""Domain profiles — the configurable ontology per "customer" corpus.

WHAT: A DomainProfile bundles the ONTOLOGY GATE for one kind of corpus: the set
of valid `entity_type` values and valid `relation_type` values. The pipeline has
exactly two hard ontology gates (entity types in fact_extractor, relation types
in entity_profiler); both now read from the active profile instead of a
hardcoded constant.

WHY: to turn Aurelm into a generic engine, the ontology must stop being baked
into Python constants. This module is the single source of truth. The `civ`
profile carries the EXACT historical values, so the existing civ game pipeline
is byte-for-byte unchanged (see the aliases in entity_filter / entity_profiler).
A second profile (`novel`) opens the door to non-civ corpora.

DESIGN: standalone — this module imports nothing from the pipeline, so it can be
imported by the low-level filter/profiler modules without any import cycle. It
holds ONLY the gate vocabulary; the prompts that mention that vocabulary live
where they belong (extraction prompts in extraction_versions/, the profiling
prompt in entity_profiler) and are selected by profile name.

An ExtractionVersion names its profile via its `profile` field (default "civ");
the runner resolves it with get_profile() and threads it to the profiling stage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainProfile:
    """The ontology gate for one corpus kind.

    entity_types / relation_types are the ONLY values the pipeline will accept
    from the LLM; anything else is dropped at the gate. Stored lowercased for
    relation types because the relation gate lowercases LLM output before check.
    """
    name: str
    entity_types: frozenset[str]
    relation_types: frozenset[str]
    # Entity types allowed at BOTH ends of a relation. None = any (civ default).
    # A hard, deterministic gate that enforces what the profiling prompt can only
    # ask for softly — e.g. a person-centred novel keeps person↔person edges only,
    # dropping relations the LLM drew from a place/group despite the instruction.
    relation_endpoint_types: frozenset[str] | None = None
    # When True, the profiler scopes each entity's context to the SENTENCE(S)
    # mentioning it, not a fixed ±400-char window. Prevents descriptions bleeding
    # between characters in dense narrative (a neighbour's trait landing on the
    # wrong person). Off for civ (the wider window is the proven behaviour there).
    tight_profiling_context: bool = False
    # Alias-confirmation prompt version for this profile (None = use the llm_config
    # value, i.e. civ's tuned default). The novel profile overrides it with an
    # antonymy-aware judge so opposite entities (rival peoples) are not merged.
    alias_prompt_version: str | None = None


# --- civ profile: the historical ontology, unchanged --------------------------
# QUOI: valeurs EXACTES d'avant P2 (entity_filter.VALID_ENTITY_TYPES et
# entity_profiler.VALID_RELATION_TYPES). POURQUOI figées ici: elles redeviennent
# la source unique dont ces deux modules deviennent de simples alias -> le
# pipeline civ ne change pas d'un octet (garde-fou de non-regression).
_CIV_ENTITY_TYPES = frozenset({
    "person", "place", "technology", "institution", "resource",
    "creature", "event", "civilization", "caste", "belief",
})
_CIV_RELATION_TYPES = frozenset({
    "located_in", "member_of", "created_by", "allied_with", "controls",
    "part_of", "produces", "worships", "enemy_of", "trades_with",
})

CIV_PROFILE = DomainProfile(
    name="civ",
    entity_types=_CIV_ENTITY_TYPES,
    relation_types=_CIV_RELATION_TYPES,
)


# --- novel profile: person-centred narrative ontology -------------------------
# QUOI: ontologie du roman (customer #1). Centrée sur les personnes et leurs
# liens intimes/thématiques — coeur du récit. POURQUOI ces relations: la mindmap
# vise "les persos, pas le reste" (filtre entity_type=person à l'export), et les
# liens de filiation / mentorat / héritage-du-geste sont ce que le roman raconte.
# COMMENT: relations stockées lowercased (le gate lowercase la sortie LLM). Les
# accents sont conservés (SQLite/Python gèrent l'Unicode); le rendu remplace les
# tirets par des espaces à l'affichage.
_NOVEL_ENTITY_TYPES = frozenset({
    "person",    # star of the mindmap
    "place",
    "creature",  # e.g. Cendre (grue)
    "event",
    "group",     # peoples / lineages
    "object",    # named artefacts
    "belief",
})
_NOVEL_RELATION_TYPES = frozenset({
    "parent-de",           # filiation (genetic)
    "enfant-de",           # inverse of parent-de (LLM may phrase either way)
    "marié-à",             # marriage
    "mentor-de",           # e.g. Shaman <-> apprentice
    "héritier-du-geste",   # thematic (non-genetic) lineage — core of the novel
    "même-peuple",         # shared people/origin
    "observe",             # the immortal Oracle vs the mortals
    "ami-de",
    "ennemi-de",
})

NOVEL_PROFILE = DomainProfile(
    name="novel",
    entity_types=_NOVEL_ENTITY_TYPES,
    relation_types=_NOVEL_RELATION_TYPES,
    # The mindmap is person-centred ("les persos, pas le reste"): keep only
    # relations between two named characters. Deterministically drops the
    # place/group edges the LLM emits despite the prompt asking for person↔person.
    relation_endpoint_types=frozenset({"person"}),
    # Novels are character-dense — scope profiling context tightly to avoid
    # one character's traits bleeding into another's description.
    tight_profiling_context=True,
    # Antonymy-aware alias judge: don't merge two opposite/rival entities.
    alias_prompt_version="v14-antonymy-generic",
)


# --- registry -----------------------------------------------------------------
PROFILES: dict[str, DomainProfile] = {
    CIV_PROFILE.name: CIV_PROFILE,
    NOVEL_PROFILE.name: NOVEL_PROFILE,
}


def get_profile(name: str | None) -> DomainProfile:
    """Return the DomainProfile for a name, defaulting to civ.

    None/empty -> civ (so any code path that doesn't set a profile keeps the
    historical behaviour). Unknown name -> KeyError with the available list, so a
    typo fails loudly instead of silently extracting nothing.
    """
    if not name:
        return CIV_PROFILE
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES))
        raise KeyError(f"Unknown domain profile '{name}'. Available: {available}")
    return PROFILES[name]
