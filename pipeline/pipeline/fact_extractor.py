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
from typing import Dict, List, Any, Optional
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
    ):
        """
        Initialize the fact extractor.

        Args:
            ollama_base_url: Base URL for Ollama API (ignored if provider is set)
            model: Model to use for extraction
            version: Extraction version config (defaults to v1-baseline)
            provider: LLM provider instance (defaults to OllamaProvider)
        """
        self.model = model
        self.version = version or V1_BASELINE
        # Use provided provider, or fall back to OllamaProvider for backwards compat
        self.provider = provider or OllamaProvider(base_url=ollama_base_url)

    def extract_facts(
        self,
        segments: List[Dict[str, Any]],
        raw_content: str = "",
        entity_lookup: Optional[Dict[str, Dict]] = None,
        validation_model: Optional[str] = None,
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

        Returns:
            StructuredFacts object with all extracted information
        """
        # Extract media links from raw content (regex-based, no LLM needed)
        media_links = self._extract_media_links(raw_content)

        # Concatenate ONLY narrative/consequence/description for LLM analysis
        # EXCLUDE "choice" segments to avoid extracting proposed options as facts
        relevant_text = "\n\n".join(
            seg["content"] for seg in segments
            if seg["segment_type"] in ["narrative", "consequence", "description"]
        )

        # Extract choices proposed (pattern-based, works on choice segments)
        choices_proposed = self._extract_choices_proposed(segments)

        if not relevant_text.strip():
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
            # LLM call 1: facts + entities together
            llm_result = self._llm_extract_facts_and_entities(chunk)

            # LLM call 2: dedicated entity extraction
            dedicated_entities = self._llm_extract_entities_only(chunk)

            # LLM call 3 (optional): GPT-NER style marking
            marked_entities = self._llm_mark_entities(chunk)

            all_technologies = merge(all_technologies, llm_result.get("technologies", []))
            all_resources = merge(all_resources, llm_result.get("resources", []))
            all_beliefs = merge(all_beliefs, llm_result.get("beliefs", []))
            all_geography = merge(all_geography, llm_result.get("geography", []))
            all_entities.extend(llm_result.get("entities", []))
            all_entities.extend(dedicated_entities)
            all_entities.extend(marked_entities)

        # Pattern pass: known entity names from DB (runs on full text)
        pattern_facts = self._pattern_extract_facts(relevant_text, entity_lookup or {})
        all_technologies = merge(all_technologies, pattern_facts.get("technologies", []))
        all_resources = merge(all_resources, pattern_facts.get("resources", []))
        all_beliefs = merge(all_beliefs, pattern_facts.get("beliefs", []))
        all_geography = merge(all_geography, pattern_facts.get("geography", []))
        all_entities.extend(pattern_facts.get("entities", []))

        # Dedup entities by name (first occurrence wins for type)
        seen_entities: set = set()
        merged_entities: List[ExtractedEntity] = []
        for ent in all_entities:
            key = ent.text.lower().strip()
            if key not in seen_entities:
                seen_entities.add(key)
                merged_entities.append(ent)

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
        elif self.version.validate_prompt:
            text_for_validation = relevant_text[:3000]
            merged_entities = self._llm_validate_entities(
                merged_entities, text_for_validation,
                model_override=validation_model,
            )

        return StructuredFacts(
            media_links=media_links,
            technologies=all_technologies,
            resources=all_resources,
            beliefs=all_beliefs,
            geography=all_geography,
            choices_proposed=choices_proposed,
            entities=merged_entities,
        )

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

    def _llm_extract_facts_and_entities(self, text: str) -> Dict[str, Any]:
        """Use LLM to extract facts and entities in a single call."""
        v = self.version
        prompt = v.get_facts_prompt(self.model).format(text=text)
        sys_prompt = v.get_system_prompt(self.model)

        try:
            llm_stats.increment("fact_extraction")
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

    def _llm_extract_entities_only(self, text: str) -> List[ExtractedEntity]:
        """Dedicated LLM call for entity extraction only.

        Simpler prompt focused solely on finding named entities,
        catches what the combined facts+entities call tends to miss.
        """
        v = self.version
        prompt = v.get_entity_prompt(self.model).format(text=text)
        sys_prompt = v.get_system_prompt(self.model)

        try:
            llm_stats.increment("entity_extraction")
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
            response_text = self.provider.generate(
                model=validation_model,
                prompt=prompt,
                system=validate_sys,
                temperature=v.temperature,
                max_tokens=v.num_predict,
                num_ctx=v.num_ctx,
                seed=v.seed,
                json_mode=True,
            )

            data = self._robust_json_parse(response_text)
            if data:
                # Support both formats: {"keep": ["name1",...]} and {"entities": [...]}
                if "keep" in data:
                    keep_names = {n.lower().strip() for n in data["keep"] if isinstance(n, str)}
                    validated = [e for e in entities if e.text.lower().strip() in keep_names]
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

    def _pattern_extract_facts(
        self, text: str, entity_lookup: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Pattern-based extraction: known entity names from DB.

        Complements LLM extraction -- catches known entities the LLM missed.
        Also returns entity mentions for known entities found in text.
        """
        technologies: List[str] = []
        resources: List[str] = []
        beliefs: List[str] = []
        geography: List[str] = []
        found_entities: List[ExtractedEntity] = []

        text_lower = text.lower()

        # If a known entity name appears in the text, add it to the right bucket
        ENTITY_TYPE_TO_BUCKET: Dict[str, List[str]] = {
            "technology": technologies,
            "place": geography,
            "institution": beliefs,
            "caste": beliefs,
            "event": beliefs,
            "civilization": [],  # don't auto-add civs
        }
        for name_lower, entity in entity_lookup.items():
            if len(name_lower) < 4:
                continue  # skip very short names (noise risk)
            if name_lower not in text_lower:
                continue

            etype = entity.get("entity_type", "")
            canonical = entity["canonical_name"]

            bucket = ENTITY_TYPE_TO_BUCKET.get(etype, None)
            if bucket is not None:
                bucket.append(canonical)

            # Also emit as entity mention so it gets recorded
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
