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

    def extract_facts(self, segments: List[Dict[str, Any]], raw_content: str = "") -> StructuredFacts:
        """
        Extract structured facts from turn segments.

        Args:
            segments: List of segment dicts with 'segment_type' and 'content'
            raw_content: Optional raw Discord message content for media link extraction

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

        if not relevant_text.strip():
            return StructuredFacts(
                media_links=media_links,
                technologies=[],
                resources=[],
                beliefs=[],
                geography=[],
                choices_proposed=[]
            )

        # Extract choices proposed (pattern-based + LLM confirmation)
        choices_proposed = self._extract_choices_proposed(segments)

        # Use LLM to extract other structured facts
        llm_facts = self._llm_extract_facts(relevant_text)

        return StructuredFacts(
            media_links=media_links,
            technologies=llm_facts.get("technologies", []),
            resources=llm_facts.get("resources", []),
            beliefs=llm_facts.get("beliefs", []),
            geography=llm_facts.get("geography", []),
            choices_proposed=choices_proposed
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
                list_items = re.findall(r'^[-*]\s+(.+)$', content, re.MULTILINE)
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

    def _llm_extract_facts(self, text: str) -> Dict[str, List[str]]:
        """Use LLM to extract technologies, resources, beliefs, and geography."""

        prompt = f"""Tu es un assistant qui extrait des faits structurés d'un tour de jeu de civilisation.

Texte du tour :
{text}

Extrais les informations suivantes et retourne UNIQUEMENT un objet JSON valide (pas de texte avant ou après) :

{{
  "technologies": ["liste des outils, techniques, savoirs découverts ou mentionnés"],
  "resources": ["liste des ressources naturelles mentionnées (nourriture, matériaux, etc.)"],
  "beliefs": ["liste des croyances, rituels, systèmes sociaux, ou institutions mentionnés"],
  "geography": ["liste des lieux, caractéristiques géographiques, ou environnements décrits"]
}}

Règles :
- Sois spécifique et concret (ex: "gourdins", "pieux", pas juste "outils")
- Inclus uniquement ce qui est explicitement mentionné dans le texte
- Utilise les termes exacts du texte quand possible
- Si une catégorie est vide, retourne une liste vide []
- Retourne UNIQUEMENT le JSON, rien d'autre"""

        try:
            response = self.client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for factual extraction
                        "num_predict": 500
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

                # Validate structure
                return {
                    "technologies": facts.get("technologies", []),
                    "resources": facts.get("resources", []),
                    "beliefs": facts.get("beliefs", []),
                    "geography": facts.get("geography", [])
                }
            else:
                print(f"Warning: LLM response not valid JSON: {response_text[:200]}")
                return {"technologies": [], "resources": [], "beliefs": [], "geography": []}

        except Exception as e:
            print(f"Error during LLM fact extraction: {e}")
            return {"technologies": [], "resources": [], "beliefs": [], "geography": []}

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
