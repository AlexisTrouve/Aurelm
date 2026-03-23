"""
Structured fact and entity extractor for game turns.

Extracts from turn segments via LLM calls:
- Technologies/tools discovered
- Resources mentioned
- Beliefs/rituals/social systems
- Geography/environment
- Named entities (persons, places, technologies, institutions, etc.)
- Media links (YouTube, images) — regex-based
- Choices proposed by the GM — pattern-based

Supports versioned extraction strategies via extraction_versions module.
"""

import json
import re
import unicodedata
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from functools import lru_cache

from . import llm_stats
from .entity_filter import ExtractedEntity, is_noise_entity, VALID_ENTITY_TYPES
from .extraction_versions import ExtractionVersion, get_version, V1_BASELINE
from .llm_provider import LLMProvider, OllamaProvider


@dataclass
class StructuredFacts:
    """Container for extracted structured facts from a turn."""
    media_links: List[Dict[str, str]]  # [{type: 'youtube', url: str, title?: str}]
    technologies: List[str]
    resources: List[str]
    beliefs: List[str]
    geography: List[str]
    choices_proposed: List[str]
    entities: List[ExtractedEntity] = field(default_factory=list)


class FactExtractor:
    """Extracts structured facts and entities from turn segments using LLM."""

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        version: Optional[ExtractionVersion] = None,
        provider: Optional[LLMProvider] = None,
        focus_model: Optional[str] = None,
        validate_model: Optional[str] = None,
        mask_model: Optional[str] = None,
    ):
        """
        Initialize the fact extractor.

        Args:
            ollama_base_url: Base URL for Ollama API (ignored if provider is set)
            model: Model to use for extraction (calls 1 + 2)
            version: Extraction version config (defaults to v1-baseline)
            provider: LLM provider instance (defaults to OllamaProvider)
            focus_model: Model for the focus call (call 3). Overrides version.focus_model.
            validate_model: Model for the validate call (call 4). Overrides version.validate_model.
            mask_model: Model for masked entity passes. Overrides version.mask_model.
        """
        self.model = model
        self.version = version or V1_BASELINE
        # Use provided provider, or fall back to OllamaProvider for backwards compat
        self.provider = provider or OllamaProvider(base_url=ollama_base_url)
        # Per-stage model overrides from external config (higher priority than version defaults)
        self.focus_model = focus_model
        self.validate_model = validate_model
        self.mask_model = mask_model
        # Stats from the last extract_facts() call — updated each call.
        # Exposed for runner.py per-turn logging.
        self.last_stats: dict = {}

    def extract_facts(
        self,
        segments: List[Dict[str, Any]],
        raw_content: str = "",
        entity_lookup: Optional[Dict[str, Dict]] = None,
        validation_model: Optional[str] = None,
        prev_tech_era: Optional[str] = None,
        prev_fantasy_level: Optional[str] = None,
        on_llm_call: Optional[Callable[[str], None]] = None,
    ) -> StructuredFacts:
        """
        Extract structured facts and entities from turn segments.

        Single LLM call extracts facts + entities together.
        Entity-based pattern pass adds known entities from DB.

        Args:
            segments: List of segment dicts with 'segment_type' and 'content'
            raw_content: Optional raw Discord message content for media link extraction
            entity_lookup: Optional {name_lower: {canonical_name, entity_type, ...}}
                           built from DB entities for the current civ.
            validation_model: Optional model override for the validation LLM call.
                              If None, uses self.model (same as extraction).
            prev_tech_era: Tech era label from the previous turn (e.g. "neolithique").
                           Appended to the system prompt so the LLM knows the context.
            prev_fantasy_level: Fantasy level label from the previous turn (e.g. "realiste").
                                Appended to the system prompt alongside tech_era.

        Returns:
            StructuredFacts object with all extracted information
        """
        # Extract media links from raw content (regex-based, no LLM needed)
        media_links = self._extract_media_links(raw_content)

        # Exclude choice segments from entity extraction — choice option bullets
        # (e.g. "- Des tambours en peau d'herbivore") are unchosen options that
        # never enter the canon. Extracting them produces false entities.
        # Named entities that matter will appear in the narrative text of this
        # turn or be confirmed in the PJ/next-MJ segment.
        relevant_text = "\n\n".join(
            seg["content"] for seg in segments
            if seg.get("segment_type") != "choice"
        )

        # Extract choices proposed (pattern-based, runs on choice segments only)
        choices_proposed = self._extract_choices_proposed(segments)

        if not relevant_text.strip():
            self.last_stats = {
                "text_chars": 0, "sys_prompt_chars": 0, "chunks": 0,
                "raw": 0, "after_dedup": 0, "final": 0,
            }
            return StructuredFacts(
                media_links=media_links,
                technologies=[],
                resources=[],
                beliefs=[],
                geography=[],
                choices_proposed=choices_proposed,
                entities=[],
            )

        # Chunk text if version requires it
        chunks = self._chunk_text(relevant_text)
        # Estimate system prompt size once (same for all chunks)
        sys_prompt = self.version.get_system_prompt(self.model) or ""

        # Inject tech/fantasy context from the previous turn so the LLM can
        # calibrate what counts as a "notable" named entity in this era.
        # Example: "Navires" is a major tech in a neolithic context but mundane later.
        if prev_tech_era or prev_fantasy_level:
            context_lines = ["\nContexte de la civilisation (tour precedent) :"]
            if prev_tech_era:
                context_lines.append(f"- Niveau technologique : {prev_tech_era}")
            if prev_fantasy_level:
                context_lines.append(f"- Niveau fantastique : {prev_fantasy_level}")
            context_lines.append(
                "Utilise ce contexte pour calibrer ce qui est 'notable' : "
                "une technologie simple est remarquable en contexte neolithique, "
                "un element surnaturel est rare en contexte realiste."
            )
            sys_prompt = sys_prompt + "\n" + "\n".join(context_lines)

        # Merge helper
        def merge(a: List[str], b: List[str]) -> List[str]:
            seen: set = set()
            result: List[str] = []
            for item in a + b:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(item.strip())
            return result

        # Accumulate results across all chunks
        all_technologies: List[str] = []
        all_resources: List[str] = []
        all_beliefs: List[str] = []
        all_geography: List[str] = []
        all_entities: List[ExtractedEntity] = []

        for chunk in chunks:
            # Build known-entity hints for this chunk: fuzzy-match entity_lookup
            # against the chunk text so the LLM gets a list of candidates to look for.
            # Hint section is appended to each prompt AFTER {text} to avoid polluting
            # the text reference used by the validate pass.
            known_hints = self._build_known_hints(chunk, entity_lookup or {})

            # LLM call 1: facts + entities together
            llm_result = self._llm_extract_facts_and_entities(chunk, known_hints)
            if on_llm_call: on_llm_call("extraction")

            # LLM call 2: dedicated entity extraction
            dedicated_entities = self._llm_extract_entities_only(chunk, known_hints)
            if on_llm_call: on_llm_call("extraction")

            # LLM call 3 (optional): GPT-NER style marking
            marked_entities = self._llm_mark_entities(chunk)
            if on_llm_call and self.version.mark_prompt:
                on_llm_call("extraction")

            # LLM call 3b (optional): focused entity call (e.g. castes/institutions only).
            # Only fires if version has a focus_prompt — otherwise returns [] immediately.
            focused_entities = self._llm_extract_focused(chunk)
            if on_llm_call and self.version.get_focus_prompt(self.model):
                on_llm_call("extraction")

            all_technologies = merge(all_technologies, llm_result.get("technologies", []))
            all_resources = merge(all_resources, llm_result.get("resources", []))
            all_beliefs = merge(all_beliefs, llm_result.get("beliefs", []))
            all_geography = merge(all_geography, llm_result.get("geography", []))
            all_entities.extend(llm_result.get("entities", []))
            all_entities.extend(dedicated_entities)
            all_entities.extend(marked_entities)
            all_entities.extend(focused_entities)

        # Pattern pass: known entity names from DB (runs on full text)
        pattern_facts = self._pattern_extract_facts(relevant_text, entity_lookup or {})
        all_technologies = merge(all_technologies, pattern_facts.get("technologies", []))
        all_resources = merge(all_resources, pattern_facts.get("resources", []))
        all_beliefs = merge(all_beliefs, pattern_facts.get("beliefs", []))
        all_geography = merge(all_geography, pattern_facts.get("geography", []))
        all_entities.extend(pattern_facts.get("entities", []))

        # Capture raw count before dedup/filtering for funnel stats
        raw_entity_count = len(all_entities)

        # Dedup entities by name (first occurrence wins for type).
        # Normalize accents so "Assemblee des Chefs" and "Assemblée des Chefs"
        # are treated as the same entity (the focus call prompt uses no accents).
        def _dedup_key(text: str) -> str:
            t = text.lower().strip()
            return "".join(
                c for c in unicodedata.normalize("NFD", t)
                if unicodedata.category(c) != "Mn"
            )

        seen_entities: set = set()
        merged_entities: List[ExtractedEntity] = []
        for ent in all_entities:
            key = _dedup_key(ent.text)
            if key not in seen_entities:
                seen_entities.add(key)
                merged_entities.append(ent)

        after_dedup_count = len(merged_entities)

        # --- Masked extraction passes ---
        # For each masked pass: replace found entity names with _____ in each chunk,
        # run an entity-only call on the stripped text, merge, re-dedup.
        # Without dominant entities monopolizing attention, the LLM is forced to find
        # what it previously overlooked (techs, beliefs, minor creatures).
        # Supports 1..N sequential passes (each pass uses all entities found so far).
        n_mask_passes = self.version.effective_mask_passes()
        if n_mask_passes > 0 and merged_entities:
            for _pass in range(n_mask_passes):
                for chunk in chunks:
                    masked_text = self._mask_entities_in_text(chunk, merged_entities)
                    # Skip chunks where masking left too little useful text
                    useful_remaining = masked_text.replace("_____", "").strip()
                    if masked_text != chunk and len(useful_remaining) >= 100:
                        # Uses mask_entity_prompts[pass] or mask_entity_prompt (if set)
                        new_ents = self._llm_extract_entities_masked(masked_text, pass_index=_pass)
                        merged_entities.extend(new_ents)

                # Re-dedup after each pass (accent-normalized key reused)
                seen_masked: set = set()
                deduped_masked: List[ExtractedEntity] = []
                for ent in merged_entities:
                    key = _dedup_key(ent.text)
                    if key not in seen_masked:
                        seen_masked.add(key)
                        deduped_masked.append(ent)
                merged_entities = deduped_masked
                after_dedup_count = len(merged_entities)  # update funnel stat

        # Certainty filtering: if the version defines a threshold, filter entities
        # by their LLM-assigned certainty score. Replaces validation pass for v14+.
        if self.version.certainty_threshold > 0:
            before_count = len(merged_entities)
            merged_entities = [
                e for e in merged_entities
                # Keep entities with certainty >= threshold, or certainty 0 (not set —
                # e.g. from pattern pass or mark pass which don't produce certainty)
                if e.certainty >= self.version.certainty_threshold or e.certainty == 0
            ]
            filtered_count = before_count - len(merged_entities)
            if filtered_count > 0:
                print(f"  Certainty filter: {before_count} -> {len(merged_entities)} entities "
                      f"(removed {filtered_count} below threshold {self.version.certainty_threshold})")

        # Validation pass (optional): LLM filters entities with a checklist
        # Skipped when certainty filtering is active (v14+) — the two are alternatives.
        # Priority: external config (self.validate_model) > version default > caller arg > extraction model.
        validate_dropped_names: list[str] = []
        if self.version.certainty_threshold <= 0 and self.version.validate_prompt:
            before_validate = list(merged_entities)
            merged_entities = self._llm_validate_entities(
                merged_entities, relevant_text[:3000],
                model_override=self.validate_model or self.version.validate_model or validation_model,
            )
            if on_llm_call: on_llm_call("validation")
            kept_names = {e.text.lower() for e in merged_entities}
            validate_dropped_names = [e.text for e in before_validate if e.text.lower() not in kept_names]
            if validate_dropped_names:
                print(f"  Validate dropped ({len(validate_dropped_names)}): {validate_dropped_names}")

        # Populate last_stats for runner.py per-turn logging.
        # Funnel: raw (post-noise-filter) -> dedup -> validate -> final
        self.last_stats = {
            "text_chars": len(relevant_text),
            "sys_prompt_chars": len(sys_prompt),
            "chunks": len(chunks),
            "raw": raw_entity_count,           # after noise filter, before dedup
            "after_dedup": after_dedup_count,  # after accent-normalized dedup
            "validate_dropped": validate_dropped_names,  # names dropped by validate
            "final": len(merged_entities),     # after validate/certainty pass
        }

        return StructuredFacts(
            media_links=media_links,
            technologies=all_technologies,
            resources=all_resources,
            beliefs=all_beliefs,
            geography=all_geography,
            choices_proposed=choices_proposed,
            entities=merged_entities,
        )

    def extract_pj_entities(
        self,
        pj_text: str,
        entity_lookup: Optional[Dict[str, Dict]] = None,
        on_llm_call: Optional[Callable[[str], None]] = None,
    ) -> List[ExtractedEntity]:
        """Extract named entities from player (PJ) response text.

        Lighter than extract_facts(): entity_only + focused calls, no facts
        extraction, no validation pass. PJ text is trusted canon lore — we want
        to capture entities the player introduces (creatures, foods, technologies)
        without over-filtering them through a genericity checker.

        Pattern pass also runs so known DB entities get their mentions registered
        even when the player references them without introducing new ones.
        """
        if not pj_text.strip():
            return []

        chunks = self._chunk_text(pj_text)
        all_entities: List[ExtractedEntity] = []

        for chunk in chunks:
            known_hints = self._build_known_hints(chunk, entity_lookup or {})

            # Call 1: dedicated entity-only extraction
            ents = self._llm_extract_entities_only(chunk, known_hints)
            all_entities.extend(ents)
            if on_llm_call: on_llm_call("pj_extraction")

            # Call 2: focused extraction (catches types entity_only misses)
            focused = self._llm_extract_focused(chunk)
            all_entities.extend(focused)
            if on_llm_call and self.version.get_focus_prompt(self.model):
                on_llm_call("pj_extraction")

        # Pattern pass: add mentions of known DB entities found in PJ text
        pattern_facts = self._pattern_extract_facts(pj_text, entity_lookup or {})
        all_entities.extend(pattern_facts.get("entities", []))

        # Accent-normalized dedup (same logic as extract_facts)
        seen: set = set()
        result: List[ExtractedEntity] = []
        for ent in all_entities:
            key = "".join(
                c for c in unicodedata.normalize("NFD", ent.text.lower().strip())
                if unicodedata.category(c) != "Mn"
            )
            if key not in seen:
                seen.add(key)
                result.append(ent)

        return result

    @staticmethod
    def _robust_json_parse(text: str) -> Optional[dict]:
        """Parse JSON from LLM output with recovery for common malformations.

        LLMs (especially smaller ones) frequently produce broken JSON:
        truncated at max_tokens, missing trailing brackets, stray commas,
        or text before/after the JSON object. This method tries multiple
        strategies to extract a usable dict.

        Returns None only if all recovery strategies fail.
        """
        if not text or not text.strip():
            return None

        # Strategy 1: direct parse of the full text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: extract outermost { ... } and parse
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # Strategy 3: repair truncated JSON — close open brackets/braces
        # Find the first '{' and attempt incremental repair
        start = text.find('{')
        if start == -1:
            return None

        fragment = text[start:]
        # Try closing progressively: the JSON may be cut mid-array or mid-object
        for suffix in [']}', '"}]}', '"]}]}', '}', '}}', '"}}']:
            try:
                return json.loads(fragment + suffix)
            except json.JSONDecodeError:
                continue

        # Strategy 4: truncate at the last valid comma and close
        # Find the last complete array element (last '},')
        last_complete = fragment.rfind('},')
        if last_complete > 0:
            truncated = fragment[:last_complete + 1]  # up to and including '}'
            for suffix in [']}', ']}]}', ']}}}']:
                try:
                    return json.loads(truncated + suffix)
                except json.JSONDecodeError:
                    continue

        # Strategy 5: extract individual arrays by key (last resort)
        # If the top-level object is broken, try to salvage individual fields
        result: dict = {}
        for key in ["entities", "technologies", "resources", "beliefs", "geography"]:
            # Look for "key": [...] pattern
            pattern = rf'"{key}"\s*:\s*\[[\s\S]*?\]'
            arr_match = re.search(pattern, fragment)
            if arr_match:
                try:
                    result[key] = json.loads('{' + arr_match.group(0) + '}')[key]
                except (json.JSONDecodeError, KeyError):
                    pass

        return result if result else None

    def _mask_entities_in_text(self, text: str, entities: List[ExtractedEntity]) -> str:
        """Replace each extracted entity name with _____ in the text.

        Used for the masked second-pass: after first-pass extraction, dominant
        entities are hidden so the LLM focuses on what it previously overlooked.

        Sorts by length descending so "Cercle des Sages" is masked before "Cercle",
        preventing partial masking ("_____ des Sages" instead of "_____").
        Matching is case-insensitive.
        """
        masked = text
        # Longest names first — prevents shorter names from creating partial masks
        sorted_ents = sorted(entities, key=lambda e: len(e.text), reverse=True)
        for ent in sorted_ents:
            pattern = re.compile(re.escape(ent.text), re.IGNORECASE)
            masked = pattern.sub("_____", masked)
        return masked

    def _llm_extract_entities_masked(self, masked_text: str, pass_index: int = 0) -> List[ExtractedEntity]:
        """Entity extraction call on masked text (_____ = already-found entities).

        pass_index selects the prompt when mask_entity_prompts (per-pass scoped
        prompts) is set (v21.5+). Falls back to mask_entity_prompt then entity_prompt.
        Uses version.mask_model / self.mask_model if set, else extraction model.
        No known_hints — masked pass is pure discovery, not confirmation.
        """
        v = self.version
        # Priority: external config > version default > extraction model
        model_to_use = self.mask_model or v.mask_model or self.model
        prompt = v.get_mask_entity_prompt(model_to_use, pass_index=pass_index).format(text=masked_text)
        sys_prompt = v.get_system_prompt(model_to_use)

        try:
            llm_stats.increment("entity_extraction")
            self.provider.current_stage = "entity_extraction"
            response_text = self.provider.generate(
                model=model_to_use,
                prompt=prompt,
                system=sys_prompt,
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                json_mode=True,
                json_schema=v.entity_format if isinstance(v.entity_format, dict) else None,
            )
            data = self._robust_json_parse(response_text)
            if data:
                return self._coerce_entity_list(data.get("entities", []))
            return []
        except Exception as e:
            print(f"Error during masked entity extraction: {e}")
            return []

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on version config.

        If chunk_by_paragraph is False, returns the full text as a single chunk.
        Otherwise splits on paragraph boundaries, merging small paragraphs
        until max_chunk_words is reached.
        """
        if not self.version.chunk_by_paragraph:
            return [text]

        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return [text]

        chunks: List[str] = []
        current: List[str] = []
        current_words = 0

        for para in paragraphs:
            para_words = len(para.split())
            if current_words + para_words > self.version.max_chunk_words and current:
                chunks.append("\n\n".join(current))
                current = [para]
                current_words = para_words
            else:
                current.append(para)
                current_words += para_words

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def _extract_media_links(self, raw_content: str) -> List[Dict[str, str]]:
        """Extract YouTube links and other media from raw Discord content."""
        media_links = []

        # YouTube pattern
        youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
        for match in re.finditer(youtube_pattern, raw_content):
            media_links.append({
                "type": "youtube",
                "url": match.group(0),
                "video_id": match.group(1)
            })

        # Image attachments (Discord CDN pattern)
        image_pattern = r'https?://cdn\.discordapp\.com/attachments/[^\s]+'
        for match in re.finditer(image_pattern, raw_content):
            media_links.append({
                "type": "image",
                "url": match.group(0)
            })

        return media_links

    def _extract_choices_proposed(self, segments: List[Dict[str, Any]]) -> List[str]:
        """Extract choices proposed by GM from choice segments."""
        choices = []

        for seg in segments:
            if seg["segment_type"] == "choice":
                content = seg["content"]

                # Pattern 1: Markdown list (- choice, - choice)
                list_items = re.findall(r'^\s*[-*]\s+(.+)$', content, re.MULTILINE)
                if list_items:
                    choices.extend([item.strip() for item in list_items if item.strip()])
                    continue

                # Pattern 2: Numbered list (1. choice, 2. choice)
                numbered_items = re.findall(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
                if numbered_items:
                    choices.extend([item.strip() for item in numbered_items if item.strip()])
                    continue

                # Pattern 3: "Choix" header followed by lines
                if "choix" in content.lower():
                    # Split by newlines after "Choix"
                    lines = content.split('\n')
                    in_choices = False
                    for line in lines:
                        if "choix" in line.lower():
                            in_choices = True
                            continue
                        if in_choices and line.strip() and not line.strip().startswith('['):
                            # Clean up formatting
                            choice = re.sub(r'^[-*\d\.]\s*', '', line.strip())
                            if choice:
                                choices.append(choice)

        # Deduplicate while preserving order
        seen = set()
        unique_choices = []
        for choice in choices:
            if choice not in seen:
                seen.add(choice)
                unique_choices.append(choice)

        return unique_choices

    @staticmethod
    def _coerce_list(val: Any) -> List[str]:
        """Coerce any LLM output value to a clean List[str].

        Handles common LLM misbehaviour: bare strings, None, nested lists,
        lists containing ints or None.
        """
        if val is None:
            return []
        if isinstance(val, str):
            return [val] if val.strip() else []
        if isinstance(val, list):
            result = []
            for item in val:
                if item is None or item == "":
                    continue
                if isinstance(item, list):
                    # Flatten one level of nesting
                    for sub in item:
                        if sub and isinstance(sub, str):
                            result.append(sub)
                elif isinstance(item, str):
                    result.append(item)
                else:
                    # Convert non-string scalars (int, float, ...) to string
                    s = str(item).strip()
                    if s:
                        result.append(s)
            return result
        return []

    @staticmethod
    def _coerce_entity_list(val: Any) -> List[ExtractedEntity]:
        """Coerce LLM entity output to List[ExtractedEntity].

        Expected format: [{"name": "...", "type": "...", "context": "..."}]
        Filters noise and validates types.
        """
        if not isinstance(val, list):
            return []

        entities: List[ExtractedEntity] = []
        seen: set = set()

        for item in val:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            etype = str(item.get("type", "")).strip().lower()
            context = str(item.get("context", "")).strip()

            if not name or not etype:
                continue

            # Strip leading French articles for cleaner canonical names
            # "Le Cheveux de Sang" -> "Cheveux de Sang"
            # "La Caste de l'Air" -> "Caste de l'Air"
            name = re.sub(
                r"^(?:les?\s+|la\s+|l')",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()
            # Re-capitalize first letter after stripping
            if name and name[0].islower():
                name = name[0].upper() + name[1:]

            if not name:
                continue

            # Validate entity type
            if etype not in VALID_ENTITY_TYPES:
                continue

            # Filter noise
            if is_noise_entity(name):
                continue

            # Parse certainty score (default 0 = not set by LLM)
            raw_certainty = item.get("certainty", 0)
            try:
                certainty = int(raw_certainty)
            except (TypeError, ValueError):
                certainty = 0

            # Dedup by name|type
            dedup_key = f"{name.lower()}|{etype}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entities.append(ExtractedEntity(
                text=name,
                label=etype,
                context=context[:200] if context else "",
                certainty=certainty,
            ))

        return entities

    def _llm_extract_facts_and_entities(self, text: str, known_hints: str = "") -> Dict[str, Any]:
        """Use LLM to extract facts and entities in a single call.

        known_hints: optional section appended after the main prompt body listing
        known entities fuzzy-matched to this chunk. Helps recall for entities the
        LLM might overlook in dense narrative text.
        """
        v = self.version
        prompt = v.get_facts_prompt(self.model).format(text=text)
        if known_hints:
            prompt += known_hints
        sys_prompt = v.get_system_prompt(self.model)

        try:
            llm_stats.increment("fact_extraction")
            self.provider.current_stage = "fact_extraction"
            response_text = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=sys_prompt,
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                # Always request JSON mode — we parse the response as JSON.
                # The schema (if set) gives Ollama structured output; json_mode
                # gives OpenRouter response_format: json_object.
                json_mode=True,
                json_schema=v.facts_format if isinstance(v.facts_format, dict) else None,
            )

            # Parse JSON with recovery for malformed LLM output
            facts = self._robust_json_parse(response_text)
            if facts:
                return {
                    "technologies": self._coerce_list(facts.get("technologies")),
                    "resources": self._coerce_list(facts.get("resources")),
                    "beliefs": self._coerce_list(facts.get("beliefs")),
                    "geography": self._coerce_list(facts.get("geography")),
                    "entities": self._coerce_entity_list(facts.get("entities")),
                }
            else:
                print(f"Warning: LLM response not valid JSON: {response_text[:200]}")
                return {"technologies": [], "resources": [], "beliefs": [], "geography": [], "entities": []}

        except Exception as e:
            print(f"Error during LLM fact extraction: {e}")
            return {"technologies": [], "resources": [], "beliefs": [], "geography": [], "entities": []}

    def _llm_extract_entities_only(self, text: str, known_hints: str = "") -> List[ExtractedEntity]:
        """Dedicated LLM call for entity extraction only.

        Simpler prompt focused solely on finding named entities,
        catches what the combined facts+entities call tends to miss.
        known_hints: same fuzzy-matched entity hints as the facts call.
        """
        v = self.version
        prompt = v.get_entity_prompt(self.model).format(text=text)
        if known_hints:
            prompt += known_hints
        sys_prompt = v.get_system_prompt(self.model)

        try:
            llm_stats.increment("entity_extraction")
            self.provider.current_stage = "entity_extraction"
            response_text = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=sys_prompt,
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                # Always request JSON — entity extraction returns JSON.
                json_mode=True,
                json_schema=v.entity_format if isinstance(v.entity_format, dict) else None,
            )

            data = self._robust_json_parse(response_text)
            if data:
                return self._coerce_entity_list(data.get("entities"))
            else:
                return []

        except Exception as e:
            print(f"Error during dedicated entity extraction: {e}")
            return []

    def _llm_mark_entities(self, text: str) -> List[ExtractedEntity]:
        """GPT-NER style: LLM rewrites text with @@entity## markers.

        More natural for generative models — they copy the text word by word
        and add markers, instead of having to remember everything for a JSON blob.
        Typically catches entities the JSON-based calls miss.
        """
        v = self.version
        if not v.mark_prompt:
            return []

        prompt = v.mark_prompt.format(text=text)

        mark_sys = v.get_mark_system_prompt(self.model)

        try:
            llm_stats.increment("mark_extraction")
            # Mark extraction returns free-form text, not JSON
            marked_text = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=mark_sys,
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                json_mode=False,
            )

            # Parse @@entity## markers
            entities: List[ExtractedEntity] = []
            seen: set = set()
            for match in re.finditer(r'@@(.+?)##', marked_text):
                name = match.group(1).strip()
                if not name or is_noise_entity(name):
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(marked_text), match.end() + 50)
                context = marked_text[start:end]
                context = re.sub(r'@@|##', '', context).strip()[:100]

                entities.append(ExtractedEntity(
                    text=name,
                    label="unknown",  # marking doesn't provide types
                    context=context,
                ))
            return entities

        except Exception as e:
            print(f"Error during mark-based entity extraction: {e}")
            return []

    def _llm_extract_focused(self, text: str, known_hints: str = "") -> List[ExtractedEntity]:
        """Optional focused 3rd extraction call targeting a specific entity type.

        Like call 2 (entities-only) but with a narrower prompt — e.g. castes and
        institutions only. Runs per-chunk and merges into the main entity list.
        Useful when calls 1+2 systematically miss one category (e.g. social castes
        in dense narrative chunks).

        Uses focus_prompt / focus_prompt_by_model from the version config.
        Falls back to an empty list if no focus_prompt is set (backwards-compat).
        Can optionally use a different model via focus_prompt_by_model (e.g. use
        llama3.1:8b or Mistral-Nemo for a cheaper/different-angle focused pass).
        """
        v = self.version
        focus_p = v.get_focus_prompt(self.model)
        if not focus_p:
            return []

        prompt = focus_p.format(text=text)
        if known_hints:
            prompt += known_hints

        # Priority: external config (self.focus_model) > version default > extraction model.
        model_to_use = self.focus_model or v.focus_model or self.model

        try:
            llm_stats.increment("focused_extraction")
            self.provider.current_stage = "focus_extraction"
            response_text = self.provider.generate(
                model=model_to_use,
                prompt=prompt,
                system=None,  # focus prompts are self-contained
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                json_mode=True,
            )

            data = self._robust_json_parse(response_text)
            if not data:
                return []

            return self._coerce_entity_list(data.get("entities", []))

        except Exception as e:
            print(f"Error during focused entity extraction: {e}")
            return []

    def _llm_validate_entities(
        self, entities: List[ExtractedEntity], text: str,
        model_override: Optional[str] = None,
    ) -> List[ExtractedEntity]:
        """Post-extraction validation pass: LLM filters entities with a checklist.

        Sends the extracted entity list + original text to the LLM,
        which validates each entity against 4 questions and returns only the good ones.

        Args:
            entities: Entities to validate
            text: Original turn text for context
            model_override: If set, use this model instead of self.model
        """
        v = self.version
        if not v.validate_prompt:
            return entities

        if not entities:
            return []

        # Format entities for the prompt
        entity_lines = "\n".join(
            f"- {ent.text} [{ent.label}]" for ent in entities
        )

        # Support both {text} and text-free validation prompts
        try:
            prompt = v.validate_prompt.format(text=text, entities=entity_lines)
        except KeyError:
            prompt = v.validate_prompt.format(entities=entity_lines)

        # Use override model for validation if specified (per-stage config)
        validation_model = model_override or self.model
        validate_sys = v.get_validate_system_prompt(validation_model)

        try:
            llm_stats.increment("entity_validation")
            self.provider.current_stage = "entity_validation"
            response_text = self.provider.generate(
                model=validation_model,
                prompt=prompt,
                system=validate_sys,
                temperature=v.temperature,
                max_tokens=v.validate_num_predict or v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                json_mode=True,
            )

            data = self._robust_json_parse(response_text)
            if data:
                # Format 1 (v20.2+): {"decisions": [{"name": ..., "keep": bool, "reason": ...}]}
                # Format 2 (v20.1):  {"keep": ["name1", ...]}
                # Format 3 (legacy): {"entities": [...]}
                if "keep" in data:
                    # Normalize both sides with _normalize_for_fuzzy to handle
                    # encoding mismatches — nemo sometimes returns accented chars
                    # as garbled bytes (\ufffd), which breaks exact lower() match.
                    keep_names = {
                        self._normalize_for_fuzzy(n)
                        for n in data["keep"] if isinstance(n, str)
                    }
                    validated = [
                        e for e in entities
                        if self._normalize_for_fuzzy(e.text) in keep_names
                    ]
                    # Parse optional "drops" reasons (v20.2+ pipe-separated string).
                    # Nemo only supports flat strings reliably — nested JSON objects
                    # cause hallucination loops (generates thousands of dots).
                    drops_reasons: dict[str, str] = {}
                    drops_raw = data.get("drops", "")
                    if drops_raw and isinstance(drops_raw, str) and drops_raw.strip():
                        for entry in drops_raw.split("|"):
                            entry = entry.strip()
                            if ":" in entry:
                                name_part, reason_part = entry.split(":", 1)
                                drops_reasons[self._normalize_for_fuzzy(name_part.strip())] = reason_part.strip()
                    # Log all dropped entities by exclusion so we always see what nemo removed.
                    for e in entities:
                        if self._normalize_for_fuzzy(e.text) not in keep_names:
                            reason = drops_reasons.get(self._normalize_for_fuzzy(e.text), "?")
                            print(f"    DROP: {e.text} [{e.label}] -- {reason}")
                else:
                    validated = self._coerce_entity_list(data.get("entities"))
                print(f"  Validation: {len(entities)} -> {len(validated)} entities")
                return validated
            else:
                print(f"Warning: Validation LLM response not valid JSON: {response_text[:500]}")
                return entities

        except Exception as e:
            print(f"Error during entity validation: {e}, keeping all entities")
            return entities

    @staticmethod
    def _normalize_for_fuzzy(text: str) -> str:
        """Normalize text for fuzzy entity matching.

        Strips accents, lowercases, and normalizes hyphens/dashes to spaces.
        Does NOT strip plurals — keeps exact word forms for accurate substring check.
        """
        # Expand ligatures before NFD (NFD doesn't decompose œ/æ)
        text = text.lower()
        text = text.replace("\u0153", "oe").replace("\u0152", "oe")
        text = text.replace("\u00e6", "ae").replace("\u00c6", "ae")
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        # Normalize hyphens and en-dashes to space for flexible matching
        text = re.sub(r"[-\u2013\u2014]+", " ", text)
        return text

    def fuzzy_prefilter_entities(
        self, text: str, entity_lookup: Dict[str, Dict]
    ) -> List[Dict]:
        """Filter known entities to those likely present in text via fuzzy matching.

        Uses normalized comparison (accents, case, hyphens→space) plus plural
        stripping to catch entities the exact substring check misses.
        e.g. lookup has "sans-ciel" → normalized "sans ciel",
             text has "sans-ciels" → normalized "sans ciels"
             → strip trailing 's': "sans ciel" found in "sans ciels" ✓

        Returns a deduplicated list of {canonical_name, entity_type}.
        """
        if not entity_lookup:
            return []

        norm_text = self._normalize_for_fuzzy(text)
        matches: List[Dict] = []
        seen_canonical: set = set()

        for name_lower, entity in entity_lookup.items():
            canonical = entity["canonical_name"]
            if canonical in seen_canonical:
                continue  # already matched via another alias

            norm_name = self._normalize_for_fuzzy(name_lower)
            if len(norm_name) < 4:
                continue  # too short, high false-positive risk

            # Check normalized exact substring
            found = norm_name in norm_text
            # Check with plural stripped: "sans ciel" matches "sans ciels"
            if not found and norm_name.endswith("s") and len(norm_name) > 5:
                found = norm_name[:-1] in norm_text
            # Check all-token overlap for compound names (len >= 4 per token)
            # e.g. "enfants du courant" → all of ["enfants", "courant"] in text
            if not found:
                tokens = [t for t in norm_name.split() if len(t) >= 4]
                if len(tokens) >= 2:
                    found = all(t in norm_text for t in tokens)

            if found:
                seen_canonical.add(canonical)
                matches.append({
                    "canonical_name": canonical,
                    "entity_type": entity.get("entity_type", ""),
                })

        return matches

    def _build_known_hints(self, text: str, entity_lookup: Dict[str, Dict]) -> str:
        """Build a prompt hint section listing known entities fuzzy-matched to text.

        Injected after the main prompt template so the LLM knows which known
        entities to look for in the current chunk — without polluting the
        text reference used by the validate pass.
        Returns empty string if no entity_lookup or no matches.
        """
        if not entity_lookup:
            return ""
        matches = self.fuzzy_prefilter_entities(text, entity_lookup)
        if not matches:
            return ""
        lines = [
            f"- {m['canonical_name']} ({m['entity_type']})"
            for m in matches[:40]  # cap to avoid bloating prompt
        ]
        return (
            "\n\nEntites connues de cette civilisation susceptibles d'etre presentes"
            " dans le texte ci-dessus (inclus-les si tu les identifies) :\n"
            + "\n".join(lines)
        )

    def _pattern_extract_facts(
        self, text: str, entity_lookup: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Pattern-based extraction: known entity names from DB.

        Complements LLM extraction -- catches known entities the LLM missed.
        Uses fuzzy normalized matching so "sans-ciel" matches "sans-ciels" in text.
        Also returns entity mentions for known entities found in text.
        """
        technologies: List[str] = []
        resources: List[str] = []
        beliefs: List[str] = []
        geography: List[str] = []
        found_entities: List[ExtractedEntity] = []

        # Use fuzzy prefilter: normalizes both sides + handles plural stripping
        matched = self.fuzzy_prefilter_entities(text, entity_lookup)

        ENTITY_TYPE_TO_BUCKET: Dict[str, List[str]] = {
            "technology": technologies,
            "place": geography,
            "institution": beliefs,
            "caste": beliefs,
            "event": beliefs,
            "civilization": [],  # don't auto-add civs (too noisy)
        }
        for entity in matched:
            etype = entity.get("entity_type", "")
            canonical = entity["canonical_name"]

            bucket = ENTITY_TYPE_TO_BUCKET.get(etype, None)
            if bucket is not None:
                bucket.append(canonical)

            # Also emit as entity mention so it gets recorded in entity_entities
            found_entities.append(ExtractedEntity(
                text=canonical, label=etype, context="",
            ))

        return {
            "technologies": technologies,
            "resources": resources,
            "beliefs": beliefs,
            "geography": geography,
            "entities": found_entities,
        }

    def close(self):
        """Close the underlying provider's HTTP client."""
        if hasattr(self.provider, 'close'):
            self.provider.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
