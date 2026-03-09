"""Base dataclass and registry for extraction versions.

Defines the ExtractionVersion dataclass and the _VERSIONS dict
(populated by __init__.py after all version modules are imported).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ExtractionVersion:
    """Immutable extraction config."""
    name: str
    description: str

    # LLM parameters
    temperature: float = 0.1
    num_predict: int = 4000
    num_ctx: int = 8192
    seed: Optional[int] = None  # Fixed seed for deterministic output

    # System prompt (None = not used, everything in user prompt)
    # Can be a str (same for all models) or dict[str, str] keyed by model family
    system_prompt: Optional[str] = None
    system_prompt_by_model: Optional[dict[str, str]] = None

    # User prompt template for facts+entities call
    # Placeholders: {text}
    facts_prompt: str = ""
    # Per-model user prompt overrides (same pattern as system_prompt_by_model)
    facts_prompt_by_model: Optional[dict[str, str]] = None

    # User prompt template for entity-only call
    # Placeholders: {text}
    entity_prompt: str = ""
    # Per-model user prompt overrides
    entity_prompt_by_model: Optional[dict[str, str]] = None

    # Ollama format parameter — JSON schema to constrain output structure
    # When set, Ollama enforces the schema at generation level (not just prompt)
    facts_format: Optional[dict] = None
    entity_format: Optional[dict] = None

    # GPT-NER style marking prompt — LLM rewrites text with @@entity## markers
    # When set, adds a 3rd LLM call per chunk using this approach
    mark_prompt: Optional[str] = None
    mark_system_prompt: Optional[str] = None
    mark_system_prompt_by_model: Optional[dict[str, str]] = None

    # Validation pass — LLM filters extracted entities with a checklist
    validate_prompt: Optional[str] = None
    validate_system_prompt: Optional[str] = None
    validate_system_prompt_by_model: Optional[dict[str, str]] = None

    # Focus call — 3rd JSON extraction call focused on a specific entity type
    # (e.g. castes/institutions only). Runs per-chunk like calls 1 and 2,
    # and its results are merged into the entity list before dedup.
    focus_prompt: Optional[str] = None
    focus_prompt_by_model: Optional[dict[str, str]] = None

    # Per-call model overrides — let a cheaper/different model handle a specific pass.
    # e.g. validate_model = "meta-llama/llama-3.1-8b-instruct" for the validate pass
    #      (binary OUI/NON filter doesn't need qwen3:14b).
    # focus_model = "mistralai/mistral-nemo" for the focused extraction call.
    # None = use self.model (the main extraction model).
    validate_model: Optional[str] = None
    focus_model: Optional[str] = None

    # num_predict override specifically for the validate pass.
    # Validate responses are short (just a list of kept names), so 256 suffices.
    # When None, falls back to the global num_predict (default 4000).
    validate_num_predict: Optional[int] = None

    # Certainty score config — LLM self-assesses confidence per entity
    # certainty_scale: (min, max) — e.g. (1, 3) or (1, 10)
    # certainty_threshold: entities below this score are filtered out (0 = disabled)
    certainty_scale: tuple = (1, 3)
    certainty_threshold: int = 0  # 0 = no filtering (backwards compat)

    # Masked extraction passes — after first-pass dedup, replace found entity
    # names with _____ in the chunk text and run extra entity-only LLM calls.
    # Forces the LLM to look at what remains when dominant entities are hidden,
    # improving recall for techs/beliefs/creatures that get overshadowed otherwise.
    mask_and_retry: bool = False  # v21.0 compat — equivalent to mask_passes=1
    # mask_passes > 0 overrides mask_and_retry. 1 = one masked pass (v21.1+),
    # 2 = two sequential masked passes (v21.1 triple-pass), etc.
    mask_passes: int = 0
    # Custom prompt for the masked entity pass. If None, falls back to entity_prompt.
    # The mask prompt can explain what _____ means and focus on overlooked types.
    mask_entity_prompt: Optional[str] = None
    mask_entity_prompt_by_model: Optional[dict[str, str]] = None
    # Model for the masked pass. If None, falls back to self.model (extraction model).
    # Higher-precision models (e.g. qwen3.5-35b-a3b) may reduce hallucinations
    # when the LLM is given text stripped of its dominant entities.
    mask_model: Optional[str] = None
    # Per-pass prompts for scoped masked extraction (v21.5+).
    # If set, pass N uses mask_entity_prompts[N] (if index in range), falling back
    # to mask_entity_prompt then entity_prompt. Must be a tuple (frozen dataclass).
    # Useful to assign different entity-type scopes to each sequential masked pass,
    # e.g. pass 0 = techs/beliefs, pass 1 = persons/places.
    mask_entity_prompts: Optional[tuple] = None

    # Chunking config
    chunk_by_paragraph: bool = False
    max_chunk_words: int = 800  # only used if chunk_by_paragraph=True

    @staticmethod
    def _model_matches_prefix(model: str, prefix: str) -> bool:
        """Check if a model name matches a prefix.

        Handles both Ollama names (qwen3:8b) and OpenRouter IDs (qwen/qwen3-8b).
        """
        return model.startswith(prefix) or f"/{prefix}" in model

    def get_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the system prompt for a given model.

        Checks system_prompt_by_model first (matching by prefix),
        falls back to system_prompt.
        """
        if self.system_prompt_by_model and model:
            # Match by model family prefix: "qwen3:8b" matches "qwen3"
            for prefix, prompt in self.system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.system_prompt

    def get_mark_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the mark system prompt for a given model."""
        if self.mark_system_prompt_by_model and model:
            for prefix, prompt in self.mark_system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.mark_system_prompt

    def get_validate_system_prompt(self, model: str = "") -> Optional[str]:
        """Return the validate system prompt for a given model."""
        if self.validate_system_prompt_by_model and model:
            for prefix, prompt in self.validate_system_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.validate_system_prompt

    def get_focus_prompt(self, model: str = "") -> Optional[str]:
        """Return the focus prompt for a given model (falls back to focus_prompt)."""
        if self.focus_prompt_by_model and model:
            for prefix, prompt in self.focus_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.focus_prompt

    def get_facts_prompt(self, model: str = "") -> str:
        """Return the facts+entities user prompt for a given model.

        Checks facts_prompt_by_model first (matching by prefix),
        falls back to facts_prompt.
        """
        if self.facts_prompt_by_model and model:
            for prefix, prompt in self.facts_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.facts_prompt

    def get_entity_prompt(self, model: str = "") -> str:
        """Return the entity-only user prompt for a given model.

        Checks entity_prompt_by_model first (matching by prefix),
        falls back to entity_prompt.
        """
        if self.entity_prompt_by_model and model:
            for prefix, prompt in self.entity_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        return self.entity_prompt

    def get_mask_entity_prompt(self, model: str = "", pass_index: int = 0) -> str:
        """Return the entity prompt for a given masked pass.

        Priority order:
          1. mask_entity_prompts[pass_index] — per-pass scoped prompts (v21.5+)
          2. mask_entity_prompt_by_model — model-specific single prompt
          3. mask_entity_prompt — single custom prompt for all masked passes
          4. entity_prompt / entity_prompt_by_model — normal entity pass prompt
        """
        # Per-pass scoped prompt takes highest priority
        if self.mask_entity_prompts and pass_index < len(self.mask_entity_prompts):
            return self.mask_entity_prompts[pass_index]
        if self.mask_entity_prompt_by_model and model:
            for prefix, prompt in self.mask_entity_prompt_by_model.items():
                if self._model_matches_prefix(model, prefix):
                    return prompt
        if self.mask_entity_prompt:
            return self.mask_entity_prompt
        return self.get_entity_prompt(model)

    def effective_mask_passes(self) -> int:
        """Number of masked passes to run after first extraction.

        mask_passes takes priority over mask_and_retry (backwards compat).
        """
        if self.mask_passes > 0:
            return self.mask_passes
        if self.mask_and_retry:
            return 1
        return 0


# Populated by __init__.py after all version modules are imported.
# get_version() and list_versions() read from this dict.
_VERSIONS: dict[str, ExtractionVersion] = {}


def get_version(name: str) -> ExtractionVersion:
    """Get an extraction version by name. Raises KeyError if unknown."""
    if name not in _VERSIONS:
        available = ", ".join(sorted(_VERSIONS.keys()))
        raise KeyError(f"Unknown extraction version '{name}'. Available: {available}")
    return _VERSIONS[name]


def list_versions() -> list[str]:
    """Return list of available version names."""
    return sorted(_VERSIONS.keys())
