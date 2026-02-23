"""
Structured fact and entity extractor for game turns.

Extracts from turn segments via a single LLM call:
- Technologies/tools discovered
- Resources mentioned
- Beliefs/rituals/social systems
- Geography/environment
- Named entities (persons, places, technologies, institutions, etc.)
- Media links (YouTube, images) — regex-based
- Choices proposed by the GM — pattern-based
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import httpx

from . import llm_stats
from .entity_filter import ExtractedEntity, is_noise_entity, VALID_ENTITY_TYPES


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
        Extract structured facts and entities from turn segments.

        Single LLM call extracts facts + entities together.
        Entity-based pattern pass adds known entities from DB.

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
                choices_proposed=choices_proposed,
                entities=[],
            )

        # LLM call 1: facts + entities together
        llm_result = self._llm_extract_facts_and_entities(relevant_text)

        # LLM call 2: dedicated entity extraction (catches what call 1 missed)
        dedicated_entities = self._llm_extract_entities_only(relevant_text)

        # Pattern pass: known entity names from DB
        pattern_facts = self._pattern_extract_facts(relevant_text, entity_lookup or {})

        # Merge facts: LLM + patterns, case-insensitive dedup
        def merge(a: List[str], b: List[str]) -> List[str]:
            seen: set = set()
            result: List[str] = []
            for item in a + b:
                key = item.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    result.append(item.strip())
            return result

        # Merge entities: LLM call 1 + call 2 + pattern pass, dedup by name|type
        llm_entities = llm_result.get("entities", [])
        pattern_entities = pattern_facts.get("entities", [])
        seen_entities: set = set()
        merged_entities: List[ExtractedEntity] = []
        for ent in llm_entities + dedicated_entities + pattern_entities:
            key = f"{ent.text.lower()}|{ent.label}"
            if key not in seen_entities:
                seen_entities.add(key)
                merged_entities.append(ent)

        return StructuredFacts(
            media_links=media_links,
            technologies=merge(llm_result.get("technologies", []), pattern_facts.get("technologies", [])),
            resources=merge(llm_result.get("resources", []), pattern_facts.get("resources", [])),
            beliefs=merge(llm_result.get("beliefs", []), pattern_facts.get("beliefs", [])),
            geography=merge(llm_result.get("geography", []), pattern_facts.get("geography", [])),
            choices_proposed=choices_proposed,
            entities=merged_entities,
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

            # Dedup by name|type
            dedup_key = f"{name.lower()}|{etype}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entities.append(ExtractedEntity(
                text=name,
                label=etype,
                context=context[:200] if context else "",
            ))

        return entities

    def _llm_extract_facts_and_entities(self, text: str) -> Dict[str, Any]:
        """Use LLM to extract facts and entities in a single call."""

        prompt = f"""Tu es un assistant qui extrait des faits structures et des entites nommees d'un tour de jeu de civilisation.

Texte du tour :
{text}

Retourne UNIQUEMENT un objet JSON valide (pas de texte avant ou apres) :

{{
  "technologies": ["outils, techniques ou savoirs ACTIVEMENT developpes ou adoptes"],
  "resources": ["ressources naturelles ACTIVEMENT exploitees ou utilisees"],
  "beliefs": ["croyances, rituels, systemes sociaux mentionnes"],
  "geography": ["lieux specifiques ou caracteristiques geographiques nommees"],
  "entities": [
    {{"name": "Nom exact", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte du texte"}}
  ]
}}

Regles pour les faits :
- Sois specifique (ex: "gourdins", "pieux", pas "outils")
- technologies : UNIQUEMENT ce qui a ete cree, fabrique ou adopte. PAS les materiaux juste observes.
- resources : UNIQUEMENT ce qui est recolte ou exploite. PAS les elements naturels juste mentionnes.

Regles STRICTES pour les entites :
- Extraire les noms propres, termes specifiques au jeu, et concepts nommes importants.
- Inclure les noms composes meme si les mots individuels sont courants (ex: "Argile Vivante" = technologie du jeu).
- Inclure les castes, institutions, lieux nommes, peuples, technologies meme s'ils utilisent des mots francais courants.

Guide de typage :
- civilization = un PEUPLE entier (ex: "Nanzagouets", "Confluents", "Cheveux de Sang")
- caste = un sous-groupe social au sein d'un peuple (ex: "Faucons Chasseurs", "Caste de l'Air")
- institution = une organisation, assemblee, tribunal (ex: "Cercle des Sages", "Tribunal des Moeurs")
- belief = une loi, un rite, une croyance, un systeme social (ex: "Loi du Sang et de la Bete")
- technology = un savoir-faire, une invention (ex: "Argile Vivante")
- place = un lieu nomme (ex: "Gouffre Humide")
- person = un individu nomme
- creature = un animal ou etre specifique
- resource = une ressource nommee (ex: "Larmes du Ciel")
- event = un evenement historique nomme

MAUVAIS exemples (NE PAS extraire) :
  "le ciel", "la terre", "les oiseaux", "la tribu", "le village", "les anciens",
  "les chasseurs", "la femme", "l'homme", "peuple", "les rites", "l'eau",
  "les saisons", "equipe 1", "l'equipe 4", "la vallee", "le peuple des eaux",
  "observation", "amelioration"

NE PAS extraire les descriptions ou phrases generiques : "ceux qui vivent pres de la riviere", "le peuple des eaux".
NE PAS extraire les metadonnees de musique/soundtrack (noms anglais de morceaux ou artistes).
Principe : si ca designe quelque chose de NOMME et SPECIFIQUE dans le jeu (lieu, groupe, technologie, personne, caste), c'est une entite. Si c'est un mot generique, une description, ou une phrase, ce n'est PAS une entite.

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
                        "temperature": 0.1,
                        "num_predict": 1500,
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
        prompt = f"""Liste TOUTES les entites nommees dans ce texte de jeu de civilisation.

Texte :
{text}

Retourne UNIQUEMENT un JSON : {{"entities": [{{"name": "Nom exact", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]}}

Quoi extraire :
- Noms propres de groupes, castes, institutions, civilisations, lieux, technologies, personnes, lois, croyances.
- Noms composes specifiques au jeu : "Argile Vivante" (technology), "Cheveux de Sang" (civilization), "Caste de l'Air" (caste), "Loi du Sang et de la Bete" (belief).

Guide de typage :
- civilization = un PEUPLE entier (ex: "Nanzagouets", "Confluents")
- caste = un sous-groupe social (ex: "Faucons Chasseurs", "Caste de l'Air")
- institution = une organisation, assemblee (ex: "Cercle des Sages")
- belief = une loi, un rite, une croyance (ex: "Loi du Sang et de la Bete")
- technology = un savoir-faire, une invention (ex: "Argile Vivante")

NE PAS extraire :
- Mots generiques : "l'eau", "le village", "la vallee", "les anciens", "le peuple".
- Metadonnees de musique/soundtrack.
- Si tu hesites entre un nom propre et une description generique, NE PAS l'extraire.

Retourne UNIQUEMENT le JSON."""

        try:
            llm_stats.increment("entity_extraction")
            response = self.client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1500,
                    }
                }
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "").strip()

            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group(0))
                return self._coerce_entity_list(data.get("entities"))
            else:
                return []

        except Exception as e:
            print(f"Error during dedicated entity extraction: {e}")
            return []

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
        """Close HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
