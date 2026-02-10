"""Message type classification — categorizes turn segments by content type."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SegmentType(Enum):
    NARRATIVE = "narrative"       # World description, story progression
    CHOICE = "choice"             # Options presented to the player
    CONSEQUENCE = "consequence"   # Results of previous choices
    OOC = "ooc"                   # Out-of-character GM commentary
    DESCRIPTION = "description"   # Entity/location descriptions


@dataclass
class ClassifiedSegment:
    text: str
    segment_type: SegmentType
    confidence: float


def classify_segments(text: str) -> list[ClassifiedSegment]:
    """Split text into segments and classify each one.

    Uses heuristics first, then optionally LLM for ambiguous segments.
    """
    segments: list[ClassifiedSegment] = []
    paragraphs = _split_paragraphs(text)

    for para in paragraphs:
        segment_type, confidence = _classify_paragraph(para)
        segments.append(
            ClassifiedSegment(
                text=para,
                segment_type=segment_type,
                confidence=confidence,
            )
        )

    return segments


def _split_paragraphs(text: str) -> list[str]:
    """Split text into meaningful paragraphs, respecting markdown headers."""
    paragraphs: list[str] = []
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()

        # Markdown headers start a new paragraph
        if stripped.startswith("##") and current:
            paragraphs.append("\n".join(current))
            current = [line]
            continue

        # Horizontal rules are separators
        if re.match(r"^-{3,}\s*$", stripped):
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue

        # Bold headers on their own line start a new section
        if re.match(r"^\*\*[^*]+\*\*\s*$", stripped) and current:
            paragraphs.append("\n".join(current))
            current = [line]
            continue

        if stripped:
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current))
            current = []

    if current:
        paragraphs.append("\n".join(current))

    return [p for p in paragraphs if p.strip()]


def _classify_paragraph(text: str) -> tuple[SegmentType, float]:
    """Classify a single paragraph using heuristics."""
    lower = text.lower()
    stripped = text.strip()

    # OOC markers — highest priority
    if stripped.startswith("(") or stripped.startswith("["):
        return SegmentType.OOC, 0.9
    if "hors-jeu" in lower or "hors jeu" in lower or "hrp" in lower.split():
        return SegmentType.OOC, 0.9
    if re.match(r"^\[.*\]$", stripped, re.DOTALL):
        return SegmentType.OOC, 0.9

    # Choice markers — explicit patterns from real data
    if re.search(r"\*\*choix\s*\d*\b", lower):
        return SegmentType.CHOICE, 0.95
    if re.match(r"^\*\*choix\*\*", stripped, re.IGNORECASE):
        return SegmentType.CHOICE, 0.95
    if re.match(r"^\*\*libre\*\*", stripped, re.IGNORECASE):
        return SegmentType.CHOICE, 0.9
    # Bullet list that looks like options
    if _looks_like_choice_list(text):
        return SegmentType.CHOICE, 0.85
    if any(marker in lower for marker in [
        "que fais-tu", "que faites-vous", "que décides-tu",
        "autres [ libre ]", "autres [libre]",
    ]):
        return SegmentType.CHOICE, 0.8

    # Consequence markers — player response patterns
    if re.search(r"__choix\s*:", lower):
        return SegmentType.CONSEQUENCE, 0.9
    if any(marker in lower for marker in [
        "résumé des décisions", "en conséquence", "résultat", "suite à",
        "suite aux", "les conséquences",
    ]):
        return SegmentType.CONSEQUENCE, 0.8
    if re.match(r"^\*\*posture\*\*", stripped, re.IGNORECASE):
        return SegmentType.CONSEQUENCE, 0.8

    # Description markers — detailed entity/location descriptions
    if _looks_like_description(text):
        return SegmentType.DESCRIPTION, 0.7

    # Default to narrative
    return SegmentType.NARRATIVE, 0.5


def _looks_like_choice_list(text: str) -> bool:
    """Detect bullet/numbered choice lists."""
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return False

    bullet_count = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^[-•]\s+", stripped):
            bullet_count += 1
        elif re.match(r"^\d+[.)]\s+", stripped):
            bullet_count += 1

    # If most lines are bullets and there are at least 2, it's likely choices
    return bullet_count >= 2 and bullet_count >= len(lines) * 0.5


def _looks_like_description(text: str) -> bool:
    """Detect entity/location description sections."""
    lower = text.lower()
    # Section explicitly about describing something
    desc_keywords = [
        "se caractérise par", "on y trouve", "il s'agit de",
        "cette ville", "ce lieu", "cet endroit", "cette région",
        "ses habitants", "sa population",
    ]
    return any(kw in lower for kw in desc_keywords)
