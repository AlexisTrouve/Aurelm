"""History exporter — per-entity chronology to Markdown + JSON.

WHAT: For one entity (or all), emits history.md + history.json combining three
sources: the entity_entities.history event log, the entity_mentions per turn,
and the first/last_seen turn markers.

WHY: gives a "what happened to X, when" view that composes into a wiki/PDF.
Reuses the wiki's timeline idea (get_entity_timeline / context samples) but with
no civ coupling and machine-readable output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import db
from .models import Entity
from .style import ExportStyle

# QUOI: capture un numero d'ordre en tete d'un event ("Tour 1:", "Chapter 3 -").
# POURQUOI generique (pas le mot "Tour"): un corpus non-civ prefixe autrement
# (ex. "Chapitre N"); on veut juste l'entier de tete pour l'etiquette de tour.
# COMMENT: non-chiffres non-gourmands, puis le 1er entier, suivi de : ou -.
_TURN_PREFIX = re.compile(r"^\s*\D*?(\d+)\s*[:\-]\s*(.*)$", re.DOTALL)


def _split_event(event: str) -> tuple[int | None, str]:
    """Split a history event into (turn_number, text-without-prefix).

    Returns (None, event) when no leading "<label> N:" prefix is present, so the
    raw event is preserved verbatim.
    """
    m = _TURN_PREFIX.match(event)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, event.strip()


def _entity_history(conn, e: Entity) -> dict:
    """Assemble the full history record (events + mentions + markers) for one entity."""
    events = []
    for ev in e.history:
        turn, text = _split_event(ev)
        events.append({"turn": turn, "text": text})

    mentions = [
        {"turn_number": m.turn_number, "mention_text": m.mention_text, "context": m.context}
        for m in db.fetch_mentions(conn, e.id)
    ]
    return {
        "id": e.id,
        "canonical_name": e.canonical_name,
        "entity_type": e.entity_type,
        "first_seen_turn": e.first_seen_turn,
        "last_seen_turn": e.last_seen_turn,
        "is_active": e.is_active,
        "events": events,
        "mentions": mentions,
    }


def _render_markdown(records: list[dict], title: str) -> str:
    """Render one or more entity histories as Markdown."""
    lines: list[str] = [f"# {title}", ""]
    for r in records:
        status = "active" if r["is_active"] else "inactive"
        lines.append(f"## {r['canonical_name']} ({r['entity_type']})")
        span = []
        if r["first_seen_turn"] is not None:
            span.append(f"first seen T{r['first_seen_turn']}")
        if r["last_seen_turn"] is not None:
            span.append(f"last seen T{r['last_seen_turn']}")
        span.append(f"status: {status}")
        lines.append(f"_{', '.join(span)}_")
        lines.append("")

        if r["events"]:
            lines.append("### Events")
            for ev in r["events"]:
                tag = f"**T{ev['turn']}** — " if ev["turn"] is not None else ""
                lines.append(f"- {tag}{ev['text']}")
            lines.append("")

        if r["mentions"]:
            lines.append("### Mentions")
            for m in r["mentions"]:
                tag = f"**T{m['turn_number']}** — " if m["turn_number"] is not None else ""
                text = m["mention_text"] or ""
                ctx = f": {m['context']}" if m["context"] else ""
                lines.append(f"- {tag}{text}{ctx}")
            lines.append("")
    return "\n".join(lines)


def export_history(
    db_path: str,
    out_dir: str,
    entity: str | int | None = None,
    title: str = "History",
    style: ExportStyle | None = None,
) -> dict[str, str]:
    """Export history to <out_dir>/history.md and history.json.

    ``entity`` may be an entity id (int), a name (str, resolved via aliases), or
    None to export every entity's history. ``style`` is accepted for symmetry.
    """
    conn = db.get_connection(db_path)

    if entity is None:
        entities = db.fetch_all_entities(conn)
    else:
        eid = entity if isinstance(entity, int) else db.resolve_entity_id(conn, entity)
        one = db.fetch_entity(conn, eid)
        if one is None:
            raise LookupError(f"No entity with id {eid}")
        entities = [one]

    records = [_entity_history(conn, e) for e in entities]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "history.md"
    json_path = out / "history.json"

    md_path.write_text(_render_markdown(records, title), encoding="utf-8")
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"md": str(md_path), "json": str(json_path), "count": str(len(records))}
