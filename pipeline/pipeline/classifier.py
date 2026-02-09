"""Message type classification — categorizes turn segments by content type."""

from __future__ import annotations

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
    """Split text into meaningful paragraphs."""
    paragraphs = []
    current = []
    for line in text.splitlines():
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current))
            current = []
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _classify_paragraph(text: str) -> tuple[SegmentType, float]:
    """Classify a single paragraph using heuristics."""
    lower = text.lower()

    # Choice markers
    if any(marker in lower for marker in ["choix", "option", "que fais-tu", "que faites-vous"]):
        return SegmentType.CHOICE, 0.8

    # OOC markers
    if text.startswith("(") or text.startswith("[") or "hors-jeu" in lower:
        return SegmentType.OOC, 0.9

    # Consequence markers
    if any(marker in lower for marker in ["en conséquence", "résultat", "suite à"]):
        return SegmentType.CONSEQUENCE, 0.7

    # Default to narrative
    return SegmentType.NARRATIVE, 0.5
