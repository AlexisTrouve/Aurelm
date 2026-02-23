"""Centralized LLM call counter for pipeline statistics."""

from __future__ import annotations

_counts: dict[str, int] = {
    "fact_extraction": 0,
    "entity_extraction": 0,
    "summarization": 0,
    "entity_profiling": 0,
}


def increment(category: str) -> None:
    """Increment the call counter for the given category."""
    if category in _counts:
        _counts[category] += 1


def get_counts() -> dict[str, int]:
    """Return a copy of current call counts."""
    return dict(_counts)


def total() -> int:
    """Return total LLM calls across all categories."""
    return sum(_counts.values())


def reset() -> None:
    """Reset all counters to zero (call at pipeline start)."""
    for k in _counts:
        _counts[k] = 0
