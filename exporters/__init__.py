"""Aurelm headless exporters.

WHAT: A standalone, read-only package that turns any Aurelm SQLite DB into
portable artefacts — a mindmap image (PNG/SVG), a glossary (md/json), and a
per-entity history (md/json).

WHY: Aurelm's data model (entity_entities / entity_aliases / entity_mentions /
entity_relations) is domain-neutral. These exporters read ONLY those neutral
tables (+ turn_turns for turn numbers), so they work on any "customer" DB —
the existing civ games as well as future non-civ corpora (a novel, etc.) —
with zero knowledge of Discord, castes, or the MJ/PJ turn structure.

DESIGN: Mirrors the wiki/ package pattern (stdlib sqlite3, argparse CLI,
generator functions), but with NO hardcoded French/game vocabulary in the
output — every colour, font and label is driven by exporters.style.ExportStyle
so a customer profile can restyle without touching code.

Entry point: ``python -m exporters <graph|glossary|history> --db PATH ...``
"""

from __future__ import annotations

__all__ = ["style", "models", "db"]
