"""Subject extractor — detects MJ choices and PJ initiatives, tracks resolutions.

Two directions:
  - MJ -> PJ: GM proposes choices/questions. Each option = 1 subject. Closed when PJ responds.
  - PJ -> MJ: Player declares initiatives ("je fonde X"). Closed when GM addresses them.

Uses LLM calls (2-4 per turn) with JSON output. Follows fact_extractor.py patterns.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .llm_provider import LLMProvider
from . import llm_stats


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExtractedOption:
    """A single option within a subject (typically a GM-proposed choice)."""
    number: int
    label: str
    description: str = ""
    is_libre: bool = False


@dataclass
class ExtractedSubject:
    """A subject extracted from turn text (MJ choice, PJ initiative, etc.)."""
    title: str
    description: str
    direction: str  # 'mj_to_pj' or 'pj_to_mj'
    category: str   # 'choice', 'question', 'initiative', 'request'
    options: list[ExtractedOption] = field(default_factory=list)
    # Verbatim phrase from the source text — used for turn detail auto-highlight.
    source_quote: str = ""
    # Domain tags auto-assigned by _assign_subject_tags() — same vocab as entity tags.
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Subject auto-tagging
# ---------------------------------------------------------------------------

# Keywords (French, accent-tolerant) per domain tag from ENTITY_TAG_VOCAB.
# Each subject's title+description is lowercased and scanned against these lists.
_SUBJECT_TAG_KEYWORDS: dict[str, list[str]] = {
    "militaire": [
        "guerre", "armee", "armée", "combat", "bataille", "soldat", "attaque",
        "défense", "defense", "troupe", "guerrier", "conflit", "raid", "siège",
        "siege", "fortif", "garnison", "arme", "milice",
    ],
    "religieux": [
        "dieu", "déesse", "deesse", "culte", "temple", "prêtre", "pretre",
        "rituel", "croyance", "sacrifice", "foi", "divin", "sacré", "sacre",
        "prophète", "prophete", "cérémonie", "ceremonie", "offrande",
    ],
    "politique": [
        "loi", "décret", "decret", "gouvernement", "caste", "oligarchie",
        "pouvoir", "dirigeant", "conseil", "vote", "élection", "election",
        "règle", "regle", "autorité", "autorite", "succession", "statut", "rang",
        "assemblée", "assemblee",
    ],
    "economique": [
        "commerce", "échange", "echange", "ressource", "production", "récolte",
        "recolte", "marché", "marche", "richesse", "tribut", "taxe", "agriculture",
        "artisan", "mine", "forge", "irrigation", "stock", "nourriture",
    ],
    "culturel": [
        "art", "musique", "fête", "fete", "célébration", "celebration",
        "tradition", "coutume", "festival", "danse", "culture", "monument",
        "architecture", "sculpture",
    ],
    "diplomatique": [
        "alliance", "traité", "traite", "paix", "ambassadeur", "négociation",
        "negociation", "contact", "relation", "accord", "envoyé", "envoye",
        "étranger", "etranger", "diplomatie",
    ],
    "technologique": [
        "technologie", "invention", "découverte", "decouverte", "argile",
        "construction", "technique", "outil", "navire", "bateau", "voile",
        "innovation", "forge", "irrigation", "machine",
    ],
    "mythologique": [
        "mythe", "légende", "legende", "ancien", "origine", "cosmogonie",
        "ancêtre", "ancetre", "héros", "heros", "créature", "creature",
        "divinité", "divinite",
    ],
}


def _assign_subject_tags(title: str, description: str, category: str) -> list[str]:
    """Auto-assign domain tags to a subject by scanning title + description.

    Uses keyword matching against _SUBJECT_TAG_KEYWORDS. Returns a list of
    matching domain tags from ENTITY_TAG_VOCAB. Never returns status tags
    (actif/disparu/…) — those are entity-specific.

    The category ('choice', 'question', 'initiative') is NOT added as a tag
    since it's already stored in its own column.
    """
    text = (title + " " + description).lower()
    # Strip accents for more robust matching (handles é/e, â/a variants)
    import unicodedata
    text_normalized = unicodedata.normalize("NFD", text)
    text_normalized = "".join(c for c in text_normalized if unicodedata.category(c) != "Mn")

    tags: list[str] = []
    for domain, keywords in _SUBJECT_TAG_KEYWORDS.items():
        for kw in keywords:
            kw_norm = unicodedata.normalize("NFD", kw)
            kw_norm = "".join(c for c in kw_norm if unicodedata.category(c) != "Mn")
            if kw_norm in text_normalized:
                tags.append(domain)
                break  # One match per domain is enough

    return tags


@dataclass
class ExtractedResolution:
    """A resolution matching an open subject to a response in text."""
    subject_title: str
    subject_id: int  # DB ID of the matched open subject
    resolution_text: str
    chosen_option_label: str = ""
    is_libre: bool = False
    confidence: float = 0.0
    # Verbatim phrase from the player/GM text — used for turn detail auto-highlight.
    source_quote: str = ""


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_MJ_SUBJECTS_PROMPT = """Tu es un assistant d'analyse de jeu de rôle civilisationnel.

Voici le texte d'un tour du MJ (Maitre du Jeu), tour numero {turn_number}.

TEXTE DU MJ:
{text}

TACHE: Extrais TOUS les sujets qui necessitent une reponse ou une decision du joueur.

Cherche en priorite:
- Les sections "### Choix" ou "## Choix" avec des options numerotees ou a puces
- Les questions directes posees au joueur
- Les decisions a prendre (diplomatiques, militaires, economiques, sociales)

Cherche AUSSI les choix implicites dans la narration:
- Plusieurs observations ou pensees presentees en sequence qui suggerent des directions differentes
- Des alternatives decrites narrativement sans etre numerotees explicitement
- Des situations ouvertes ou le MJ decrit plusieurs possibilites sans trancher
- Des evenements qui appellent clairement une reaction/decision sans la formuler comme question

EXEMPLE de choix implicite a detecter:
  Texte: "Pourquoi se fatiguer a ramer quand on pourrait utiliser le vent. Les elements sont dechaines au large, pourquoi ne pas couvrir le pont. Les tiens voient grand, monumental meme."
  -> C'est un choix implicite sur la direction de l'innovation navale avec 3 pistes (voiles / protection / taille monumentale). Extrais-le comme sujet avec ces 3 options.

Pour chaque sujet, identifie:
- "title": titre court et descriptif du sujet
- "description": contexte du sujet (1-2 phrases)
- "source_quote": COPIE EXACTE mot-pour-mot d'un passage du texte du MJ qui declenche ce sujet.
  REGLES ABSOLUES pour source_quote:
  * Copie les mots EXACTEMENT tels qu'ils apparaissent dans le texte — meme ponctuation, meme accents, meme majuscules
  * 5 a 20 mots, suffisamment unique pour localiser le passage
  * JAMAIS paraphraser, resumer, ni reformuler
  * Si le sujet vient d'une section "## Choix", copie le debut de cette section
  * MAUVAIS: "Tu dois choisir comment explorer la riviere" (paraphrase)
  * BON: "Quel chemin empruntes-tu pour longer la riviere ?" (copie exacte)
- "category": "choice" (choix avec options), "question" (question ouverte)
- "options": liste des options proposees (vide si question ouverte)

Chaque option a:
- "number": numero de l'option (1, 2, 3...)
- "label": texte court de l'option
- "description": detail de l'option si present
- "is_libre": true si c'est une option libre/custom (souvent la derniere)

Reponds UNIQUEMENT en JSON:
{{"subjects": [
  {{
    "title": "...",
    "description": "...",
    "source_quote": "...",
    "category": "choice",
    "options": [
      {{"number": 1, "label": "...", "description": "...", "is_libre": false}},
      {{"number": 2, "label": "...", "description": "...", "is_libre": false}},
      {{"number": 3, "label": "Option libre", "description": "...", "is_libre": true}}
    ]
  }}
]}}

Si aucun sujet ne necessite de reponse, retourne {{"subjects": []}}.
"""

_PJ_INITIATIVES_PROMPT = """Tu es un assistant d'analyse de jeu de rôle civilisationnel.

Voici le texte de la reponse d'un joueur, tour numero {turn_number}.

TEXTE DU JOUEUR:
{text}

TACHE: Extrais les INITIATIVES PROPRES du joueur — les actions, projets ou declarations
que le joueur annonce de sa propre initiative (pas les reponses aux choix du MJ).

Exemples d'initiatives:
- "Je fonde un nouveau village"
- "On etablit des routes commerciales"
- "Les artisans commencent a travailler le bronze"
- "Je declare la guerre a X"
- "On envoie des explorateurs vers le nord"

N'EXTRAIS PAS:
- Les reponses directes aux choix du MJ (ex: "Je choisis l'option 2")
- Les reformulations des choix du MJ
- Les descriptions de ce qui se passe deja

Pour chaque initiative:
- "title": titre court et descriptif
- "description": ce que le joueur veut faire (1-2 phrases)
- "source_quote": COPIE EXACTE mot-pour-mot de la phrase du joueur qui declare cette initiative.
  REGLES ABSOLUES pour source_quote:
  * Copie les mots EXACTEMENT tels qu'ils apparaissent — meme ponctuation, meme accents, meme majuscules
  * 5 a 20 mots, suffisamment unique pour localiser le passage
  * JAMAIS paraphraser ou reformuler
  * MAUVAIS: "Le joueur veut enseigner la chasse" (paraphrase)
  * BON: "Je leur montre des techniques afin de perfectionner l'art de la chasse" (copie exacte)
- "category": "initiative" (action proactive) ou "request" (demande au MJ)

Reponds UNIQUEMENT en JSON:
{{"subjects": [
  {{"title": "...", "description": "...", "source_quote": "...", "category": "initiative"}}
]}}

Si aucune initiative propre, retourne {{"subjects": []}}.
"""

_MATCH_RESOLUTIONS_PROMPT = """Tu es un assistant d'analyse de jeu de rôle civilisationnel.

Voici des sujets ouverts (choix/questions du MJ en attente de reponse du joueur):

SUJETS OUVERTS:
{open_subjects}

Et voici le texte de la reponse du joueur, tour numero {turn_number}:

TEXTE DU JOUEUR:
{text}

TACHE: Pour chaque sujet ouvert, determine si le joueur y repond dans ce texte.

Pour chaque match trouve:
- "subject_id": l'ID du sujet matche
- "subject_title": le titre du sujet (pour verification)
- "resolution_text": resume de la reponse du joueur (1-2 phrases)
- "source_quote": COPIE EXACTE mot-pour-mot de la phrase du joueur qui constitue sa reponse.
  REGLES ABSOLUES pour source_quote:
  * Copie les mots EXACTEMENT tels qu'ils apparaissent dans le texte — meme ponctuation, meme accents, meme majuscules
  * 5 a 20 mots, suffisamment unique pour localiser le passage
  * JAMAIS paraphraser, resumer, ni reformuler
  * MAUVAIS: "Le joueur choisit de longer la riviere" (paraphrase)
  * BON: "Je leur montre comment suivre la riviere mene a des lieux de vie" (copie exacte)
- "chosen_option_label": label de l'option choisie si applicable (vide sinon)
- "is_libre": true si le joueur a fait un choix libre (hors options proposees)
- "confidence": score de confiance de 0.0 a 1.0
  - 1.0 = match explicite ("je choisis l'option X")
  - 0.7-0.9 = match clair par le contenu
  - 0.4-0.6 = match implicite ou partiel
  - < 0.4 = pas de match clair

Reponds UNIQUEMENT en JSON:
{{"resolutions": [
  {{
    "subject_id": 1,
    "subject_title": "...",
    "resolution_text": "...",
    "source_quote": "...",
    "chosen_option_label": "...",
    "is_libre": false,
    "confidence": 0.85
  }}
]}}

Si aucun sujet n'est resolu, retourne {{"resolutions": []}}.
"""

_DETECT_MJ_CONSEQUENCES_PROMPT = """Tu es un assistant d'analyse de jeu de rôle civilisationnel.

Voici des initiatives PJ (actions/projets du joueur) en attente de traitement par le MJ:

INITIATIVES OUVERTES:
{open_initiatives}

Et voici le texte du MJ (Maitre du Jeu), tour numero {turn_number}:

TEXTE DU MJ:
{text}

TACHE: Pour chaque initiative PJ, determine si le MJ y repond ou la traite dans ce texte.
Le MJ peut y repondre:
- Directement (mentionne explicitement l'initiative)
- Indirectement (decrit les consequences de l'action du joueur)
- Par des evenements lies (quelque chose arrive en rapport avec l'initiative)

Pour chaque match trouve:
- "subject_id": l'ID de l'initiative matchee
- "subject_title": le titre de l'initiative (pour verification)
- "resolution_text": resume de comment le MJ a traite l'initiative (1-2 phrases)
- "source_quote": COPIE EXACTE mot-pour-mot de la phrase du MJ qui traite cette initiative.
  REGLES ABSOLUES pour source_quote:
  * Copie les mots EXACTEMENT tels qu'ils apparaissent dans le texte — meme ponctuation, meme accents, meme majuscules
  * 5 a 20 mots, suffisamment unique pour localiser le passage
  * JAMAIS paraphraser, resumer, ni reformuler
  * MAUVAIS: "Le MJ decrit la decouverte de la riviere" (paraphrase)
  * BON: "La confluence de deux rivieres cristallines, encaisse dans une large vallee." (copie exacte)
- "confidence": score de confiance de 0.0 a 1.0
  - 1.0 = mention explicite de l'initiative
  - 0.7-0.9 = consequences claires de l'initiative
  - 0.4-0.6 = lien implicite
  - < 0.4 = pas de lien clair

Reponds UNIQUEMENT en JSON:
{{"resolutions": [
  {{
    "subject_id": 1,
    "subject_title": "...",
    "resolution_text": "...",
    "source_quote": "...",
    "confidence": 0.8
  }}
]}}

Si aucune initiative n'est traitee, retourne {{"resolutions": []}}.
"""


# ---------------------------------------------------------------------------
# SubjectExtractor
# ---------------------------------------------------------------------------

class SubjectExtractor:
    """Extracts MJ choices and PJ initiatives from turn text via LLM calls."""

    def __init__(self, provider: LLMProvider, model: str = "qwen3:14b"):
        self.provider = provider
        self.model = model

    def extract_mj_subjects(
        self, mj_text: str, turn_number: int
    ) -> list[ExtractedSubject]:
        """Extract choices/questions from GM text that require player response.

        Args:
            mj_text: Raw text of the GM's turn
            turn_number: Turn number for prompt context

        Returns:
            List of ExtractedSubject with direction='mj_to_pj'
        """
        if not mj_text.strip():
            return []

        prompt = _MJ_SUBJECTS_PROMPT.format(text=mj_text, turn_number=turn_number)

        try:
            llm_stats.increment("subject_extraction")
            response = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=None,
                temperature=0.1,
                max_tokens=4000,
                num_ctx=32768,
                json_mode=True,
            )

            data = _robust_json_parse(response)
            if not data:
                return []

            return _parse_subjects(data.get("subjects", []), direction="mj_to_pj")

        except Exception as e:
            print(f"Error extracting MJ subjects (T{turn_number}): {e}")
            return []

    def extract_pj_subjects(
        self, pj_text: str, turn_number: int
    ) -> list[ExtractedSubject]:
        """Extract player's own initiatives (not responses to MJ choices).

        Args:
            pj_text: Raw text of the player's response
            turn_number: Turn number for prompt context

        Returns:
            List of ExtractedSubject with direction='pj_to_mj'
        """
        if not pj_text.strip():
            return []

        prompt = _PJ_INITIATIVES_PROMPT.format(text=pj_text, turn_number=turn_number)

        try:
            llm_stats.increment("subject_extraction")
            response = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=None,
                temperature=0.1,
                max_tokens=4000,
                num_ctx=32768,
                json_mode=True,
            )

            data = _robust_json_parse(response)
            if not data:
                return []

            return _parse_subjects(data.get("subjects", []), direction="pj_to_mj")

        except Exception as e:
            print(f"Error extracting PJ initiatives (T{turn_number}): {e}")
            return []

    def match_resolutions(
        self,
        pj_text: str,
        open_subjects: list[dict],
        turn_number: int,
    ) -> list[ExtractedResolution]:
        """Match player text against open MJ subjects to find resolutions.

        Args:
            pj_text: Player's response text
            open_subjects: Open MJ->PJ subjects (from load_open_subjects)
            turn_number: Current turn number

        Returns:
            List of ExtractedResolution for matched subjects
        """
        # Only match MJ->PJ subjects (player resolves GM choices)
        mj_subjects = [s for s in open_subjects if s["direction"] == "mj_to_pj"]
        if not pj_text.strip() or not mj_subjects:
            return []

        # Format subjects for the prompt
        subjects_text = _format_subjects_for_prompt(mj_subjects)

        prompt = _MATCH_RESOLUTIONS_PROMPT.format(
            open_subjects=subjects_text,
            text=pj_text,
            turn_number=turn_number,
        )

        try:
            llm_stats.increment("subject_resolution")
            response = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=None,
                temperature=0.1,
                max_tokens=4000,
                num_ctx=32768,
                json_mode=True,
            )

            data = _robust_json_parse(response)
            if not data:
                return []

            return _parse_resolutions(data.get("resolutions", []), mj_subjects)

        except Exception as e:
            print(f"Error matching resolutions (T{turn_number}): {e}")
            return []

    def detect_mj_consequences(
        self,
        mj_text: str,
        open_initiatives: list[dict],
        turn_number: int,
    ) -> list[ExtractedResolution]:
        """Detect when GM text addresses open PJ initiatives.

        Args:
            mj_text: GM's turn text
            open_initiatives: Open PJ->MJ subjects (player initiatives)
            turn_number: Current turn number

        Returns:
            List of ExtractedResolution for addressed initiatives
        """
        # Only match PJ->MJ subjects (GM resolves player initiatives)
        pj_initiatives = [s for s in open_initiatives if s["direction"] == "pj_to_mj"]
        if not mj_text.strip() or not pj_initiatives:
            return []

        # Format initiatives for the prompt
        initiatives_text = _format_subjects_for_prompt(pj_initiatives)

        prompt = _DETECT_MJ_CONSEQUENCES_PROMPT.format(
            open_initiatives=initiatives_text,
            text=mj_text,
            turn_number=turn_number,
        )

        try:
            llm_stats.increment("subject_resolution")
            response = self.provider.generate(
                model=self.model,
                prompt=prompt,
                system=None,
                temperature=0.1,
                max_tokens=4000,
                num_ctx=32768,
                json_mode=True,
            )

            data = _robust_json_parse(response)
            if not data:
                return []

            return _parse_resolutions(data.get("resolutions", []), pj_initiatives)

        except Exception as e:
            print(f"Error detecting MJ consequences (T{turn_number}): {e}")
            return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _robust_json_parse(text: str) -> dict | None:
    """Parse JSON from LLM output with recovery for common malformations.

    Same strategy as FactExtractor._robust_json_parse — try direct parse,
    then extract {...}, then attempt bracket repair.
    """
    if not text or not text.strip():
        return None

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract outermost { ... }
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 3: repair truncated JSON
    start = text.find('{')
    if start == -1:
        return None

    fragment = text[start:]
    for suffix in [']}', '"}]}', '"]}]}', '}', '}}', '"}}']:
        try:
            return json.loads(fragment + suffix)
        except json.JSONDecodeError:
            continue

    return None


def _parse_subjects(
    raw_subjects: list, direction: str
) -> list[ExtractedSubject]:
    """Parse raw JSON subjects into ExtractedSubject dataclasses."""
    results = []

    for item in raw_subjects:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        if not title:
            continue

        category = str(item.get("category", "")).strip().lower()
        # Validate category
        if category not in ("choice", "question", "initiative", "request"):
            category = "choice" if direction == "mj_to_pj" else "initiative"

        options = []
        for opt in item.get("options", []):
            if not isinstance(opt, dict):
                continue
            label = str(opt.get("label", "")).strip()
            if not label:
                continue
            options.append(ExtractedOption(
                number=int(opt.get("number", len(options) + 1)),
                label=label,
                description=str(opt.get("description", "")).strip(),
                is_libre=bool(opt.get("is_libre", False)),
            ))

        description = str(item.get("description", "")).strip()
        results.append(ExtractedSubject(
            title=title,
            description=description,
            direction=direction,
            category=category,
            options=options,
            source_quote=str(item.get("source_quote", "")).strip(),
            tags=_assign_subject_tags(title, description, category),
        ))

    return results


def _parse_resolutions(
    raw_resolutions: list, open_subjects: list[dict]
) -> list[ExtractedResolution]:
    """Parse raw JSON resolutions, validating subject_id against open subjects."""
    # Build lookup: subject_id -> subject dict
    valid_ids = {s["id"] for s in open_subjects}
    # Also build title -> id fallback (LLM may return title instead of id)
    title_to_id = {s["title"].lower().strip(): s["id"] for s in open_subjects}

    results = []
    for item in raw_resolutions:
        if not isinstance(item, dict):
            continue

        # Resolve subject_id — try numeric ID first, fall back to title match
        subject_id = item.get("subject_id")
        if subject_id is not None:
            try:
                subject_id = int(subject_id)
            except (TypeError, ValueError):
                subject_id = None

        # Fallback: match by title if ID is invalid
        if subject_id not in valid_ids:
            raw_title = str(item.get("subject_title", "")).lower().strip()
            subject_id = title_to_id.get(raw_title)

        if subject_id is None or subject_id not in valid_ids:
            continue

        resolution_text = str(item.get("resolution_text", "")).strip()
        if not resolution_text:
            continue

        confidence = 0.0
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            pass

        results.append(ExtractedResolution(
            subject_title=str(item.get("subject_title", "")).strip(),
            subject_id=subject_id,
            resolution_text=resolution_text,
            chosen_option_label=str(item.get("chosen_option_label", "")).strip(),
            is_libre=bool(item.get("is_libre", False)),
            confidence=confidence,
            source_quote=str(item.get("source_quote", "")).strip(),
        ))

    return results


def _format_subjects_for_prompt(subjects: list[dict]) -> str:
    """Format a list of subject dicts into readable text for LLM prompts."""
    lines = []
    for s in subjects:
        header = f"[ID={s['id']}] {s['title']} (tour {s['source_turn_number']}, {s['category']})"
        lines.append(header)
        if s.get("description"):
            lines.append(f"  Description: {s['description']}")
        for opt in s.get("options", []):
            libre_tag = " [LIBRE]" if opt.get("is_libre") else ""
            lines.append(f"  Option {opt['option_number']}: {opt['label']}{libre_tag}")
            if opt.get("description"):
                lines.append(f"    -> {opt['description']}")
        lines.append("")

    return "\n".join(lines)


def build_turn_pairs(
    all_chunks: list, gm_author_id: str
) -> dict[int, dict[str, str]]:
    """Build a mapping of turn_number -> {gm_text, pj_text} from all chunks.

    Pairs consecutive GM and PJ chunks. The turn_number comes from
    sequential GM chunks (1-indexed).

    Args:
        all_chunks: All TurnChunk objects (both GM and PJ)
        gm_author_id: Author ID of the GM

    Returns:
        Dict mapping turn_number -> {"gm_text": str, "pj_text": str}
    """
    pairs: dict[int, dict[str, str]] = {}
    gm_turn_number = 0

    for chunk in all_chunks:
        if chunk.is_gm_post:
            # New GM turn
            gm_turn_number += 1
            gm_text = "\n\n".join(m.content for m in chunk.messages)
            pairs[gm_turn_number] = {"gm_text": gm_text, "pj_text": ""}
        else:
            # PJ response — attach to the most recent GM turn
            if gm_turn_number > 0:
                pj_text = "\n\n".join(m.content for m in chunk.messages)
                # Append if there's already PJ text (multiple PJ chunks)
                if pairs[gm_turn_number]["pj_text"]:
                    pairs[gm_turn_number]["pj_text"] += "\n\n" + pj_text
                else:
                    pairs[gm_turn_number]["pj_text"] = pj_text

    return pairs
