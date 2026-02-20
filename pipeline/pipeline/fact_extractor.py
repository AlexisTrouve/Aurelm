"""
Structured fact extractor for game turns.

Extracts specific categories of information from turn segments:
- Technologies/tools discovered
- Resources mentioned
- Beliefs/rituals/social systems
- Geography/environment
- Media links (YouTube, images)
- Choices proposed by the GM
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx

from . import llm_stats


@dataclass
class StructuredFacts:
    """Container for extracted structured facts from a turn."""
    media_links: List[Dict[str, str]]  # [{type: 'youtube', url: str, title?: str}]
    technologies: List[str]
    resources: List[str]
    beliefs: List[str]
    geography: List[str]
    choices_proposed: List[str]


class FactExtractor:
    """Extracts structured facts from turn segments using LLM and patterns."""

    def __init__(self, ollama_base_url: str = "http://localhost:11434", model: str = "llama3.1:8b"):
        """
        Initialize the fact extractor.

        Args:
            ollama_base_url: Base URL for Ollama API
            model: Model to use for extraction
        """
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.client = httpx.Client(timeout=120.0)

    def extract_facts(
        self,
        segments: List[Dict[str, Any]],
        raw_content: str = "",
        entity_lookup: Optional[Dict[str, Dict]] = None,
    ) -> StructuredFacts:
        """
        Extract structured facts from turn segments.

        Uses two passes:
        1. LLM pass  — semantic understanding
        2. Pattern pass — keyword lists + known entity names (catches what LLM misses)
        Results are merged and deduplicated.

        Args:
            segments: List of segment dicts with 'segment_type' and 'content'
            raw_content: Optional raw Discord message content for media link extraction
            entity_lookup: Optional {name_lower: {canonical_name, entity_type, ...}}
                           built from DB entities for the current civ.

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
                choices_proposed=choices_proposed
            )

        # Pass 1: LLM extraction
        llm_facts = self._llm_extract_facts(relevant_text)

        # Pass 2: pattern + entity-based extraction
        pattern_facts = self._pattern_extract_facts(relevant_text, entity_lookup or {})

        # Merge: LLM ∪ patterns, case-insensitive dedup
        def merge(a: List[str], b: List[str]) -> List[str]:
            seen: set = set()
            result: List[str] = []
            for item in a + b:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(item.strip())
            return result

        return StructuredFacts(
            media_links=media_links,
            technologies=merge(llm_facts.get("technologies", []), pattern_facts.get("technologies", [])),
            resources=merge(llm_facts.get("resources", []), pattern_facts.get("resources", [])),
            beliefs=merge(llm_facts.get("beliefs", []), pattern_facts.get("beliefs", [])),
            geography=merge(llm_facts.get("geography", []), pattern_facts.get("geography", [])),
            choices_proposed=choices_proposed,
        )

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

    def _llm_extract_facts(self, text: str) -> Dict[str, List[str]]:
        """Use LLM to extract technologies, resources, beliefs, and geography."""

        prompt = f"""Tu es un assistant qui extrait des faits structurés d'un tour de jeu de civilisation.

Texte du tour :
{text}

Extrais les informations suivantes et retourne UNIQUEMENT un objet JSON valide (pas de texte avant ou après) :

{{
  "technologies": ["outils, techniques ou savoirs ACTIVEMENT developpes, fabriques ou adoptes par la civilisation"],
  "resources": ["ressources naturelles ACTIVEMENT exploitees ou utilisees (nourriture recoltee, materiaux travailles, etc.)"],
  "beliefs": ["croyances, rituels, systemes sociaux, ou institutions mentionnes"],
  "geography": ["lieux, caracteristiques geographiques, ou environnements decrits"]
}}

Regles :
- Sois specifique et concret (ex: "gourdins", "pieux", pas juste "outils")
- technologies : UNIQUEMENT ce que la civilisation a cree, fabrique, appris a faire ou adopte comme pratique. PAS les substances/materiaux juste observes ou mentionnes en passant.
- resources : UNIQUEMENT ce qui est recolte, exploite ou utilise. PAS les elements naturels juste observes sans exploitation.
- Utilise les termes exacts du texte quand possible
- Si une categorie est vide, retourne une liste vide []
- Retourne UNIQUEMENT le JSON, rien d'autre"""

        try:
            llm_stats.increment("fact_extraction")
            response = self.client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for factual extraction
                        "num_predict": 1024
                    }
                }
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "").strip()

            # Try to extract JSON from response (in case LLM added extra text)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                facts = json.loads(json_match.group(0))

                # Validate and coerce all fields to List[str]
                return {
                    "technologies": self._coerce_list(facts.get("technologies")),
                    "resources": self._coerce_list(facts.get("resources")),
                    "beliefs": self._coerce_list(facts.get("beliefs")),
                    "geography": self._coerce_list(facts.get("geography")),
                }
            else:
                print(f"Warning: LLM response not valid JSON: {response_text[:200]}")
                return {"technologies": [], "resources": [], "beliefs": [], "geography": []}

        except Exception as e:
            print(f"Error during LLM fact extraction: {e}")
            return {"technologies": [], "resources": [], "beliefs": [], "geography": []}

    # --- keyword lists for pattern pass ---

    _BELIEF_KEYWORDS = [
        "esprit", "âme", "ame", "ancêtre", "ancetre", "sacré", "sacre",
        "rituel", "cérémonie", "ceremonie", "offrande", "sacrifice",
        "oracle", "bénédiction", "benediction", "piété", "piete",
        "sacralité", "sacralite", "foi", "vénérer", "venerer", "prier",
        "divin", "cosmologie", "cosmologique", "céleste", "celeste",
        "au-delà", "au-dela", "ciel", "mort", "défunt", "defunt",
        "croyance", "croire", "tradition", "coutume", "tabou",
        "totem", "chamane", "shaman", "prophétie", "prophetie",
        "réincarnation", "reincarnation", "âmes", "esprits",
        "loi du sang", "lois du sang",
    ]

    _RESOURCE_KEYWORDS = [
        "récolte", "recolte", "pêche", "peche", "chasse", "cueillette",
        "culture", "cultive", "extrait", "exploite", "stocke",
        "nourriture", "viande", "poisson", "baie", "graine", "tubercule",
        "herbe", "plante", "bois", "pierre", "argile", "silex",
        "gingembre", "fleur", "champignon", "résine", "resine",
        "fourrure", "peau", "cuir", "os", "griffe", "corne",
        "cuivre", "bronze", "fer", "minerai", "sel",
    ]

    def _pattern_extract_facts(
        self, text: str, entity_lookup: Dict[str, Dict]
    ) -> Dict[str, List[str]]:
        """Pattern-based extraction: keyword lists + known entity names.

        Complements LLM extraction — catches entities the LLM ignored and
        beliefs signalled by spiritual/social keywords.
        """
        technologies: List[str] = []
        resources: List[str] = []
        beliefs: List[str] = []
        geography: List[str] = []

        text_lower = text.lower()

        # --- Entity-based pass ---
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
            bucket = ENTITY_TYPE_TO_BUCKET.get(entity.get("entity_type", ""), None)
            if bucket is None:
                continue
            if name_lower in text_lower:
                bucket.append(entity["canonical_name"])

        # --- Keyword pass for beliefs ---
        sentences = re.split(r'[.!?\n]', text)
        for sentence in sentences:
            s_lower = sentence.lower().strip()
            if not s_lower:
                continue
            if any(kw in s_lower for kw in self._BELIEF_KEYWORDS):
                clean = sentence.strip()
                if clean and len(clean) > 10:
                    beliefs.append(clean)

        # Resource keyword pass: intentionally disabled.
        # Sentence-level keyword matching produces too much noise (narrative sentences
        # containing "pêche" or "rivière" are not resource entries).
        # The LLM pass already handles resources well enough.

        return {
            "technologies": technologies,
            "resources": resources,
            "beliefs": beliefs,
            "geography": geography,
        }

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
