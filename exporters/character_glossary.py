"""Character glossary exporter — persons with a per-chapter history.

WHAT: For each person entity, emits a dossier: canonical name + aliases +
description, then a "per chapter" breakdown of what happens to them, chapter by
chapter. Output as Markdown (human) + JSON (machine).

WHY: a novel's readers/authors want "who is this character and what do they do
in each chapter". The per-chapter view is built from two sources, most-reliable
first: the profiling turn-summaries (rich narrative, keyed "Tour N: …") when
present, otherwise the raw mention contexts for that chapter. Mentions accumulate
reliably chapter-by-chapter, so a chapter is never silently dropped even if its
narrative summary is missing.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import db
from .history_exporter import _split_event
from .style import ExportStyle

# Placeholder contexts the LLM sometimes emits — not worth showing.
_EMPTY_CONTEXTS = {"", "non mentionné", "non mentionne"}


def _per_chapter(entity, mentions) -> list[dict]:
    """Build the per-chapter history for a person.

    Merges profiling turn-summaries (rich) with mention contexts (fallback),
    one entry per chapter the person appears in, in chapter order.
    """
    # rich narrative summaries from the entity history ("Tour N: ...")
    summaries: dict[int, str] = {}
    for event in entity.history:
        turn, text = _split_event(event)
        if turn is not None:
            summaries[turn] = text

    # mention contexts per chapter (reliable presence signal)
    contexts: dict[int, list[str]] = {}
    for m in mentions:
        if m.turn_number is None:
            continue
        ctx = (m.context or m.mention_text or "").strip()
        if ctx and ctx.lower() not in _EMPTY_CONTEXTS:
            contexts.setdefault(m.turn_number, []).append(ctx)

    chapters = sorted(set(summaries) | set(contexts))
    out = []
    for ch in chapters:
        if ch in summaries:
            out.append({"chapter": ch, "text": summaries[ch], "source": "summary"})
        else:
            joined = " ; ".join(dict.fromkeys(contexts.get(ch, [])))  # dedup, keep order
            out.append({"chapter": ch, "text": joined or "(apparaît)", "source": "mention"})
    return out


def _character_record(conn, e) -> dict:
    """Assemble the full character dossier for one person."""
    return {
        "id": e.id,
        "canonical_name": e.canonical_name,
        "description": e.description,
        "aliases": db.fetch_aliases(conn, e.id),
        "first_seen_turn": e.first_seen_turn,
        "last_seen_turn": e.last_seen_turn,
        "is_active": e.is_active,
        "per_chapter": _per_chapter(e, db.fetch_mentions(conn, e.id)),
    }


def _render_markdown(records: list[dict], title: str) -> str:
    """Render the character glossary as Markdown."""
    lines = [f"# {title}", ""]
    for r in sorted(records, key=lambda x: x["canonical_name"].lower()):
        header = f"## {r['canonical_name']}"
        if r["aliases"]:
            header += f"  _(aka {', '.join(r['aliases'])})_"
        lines.append(header)
        if r["description"]:
            lines.append(r["description"])
        lines.append("")
        if r["per_chapter"]:
            lines.append("**Par chapitre :**")
            for ch in r["per_chapter"]:
                lines.append(f"- **Chapitre {ch['chapter']}** — {ch['text']}")
            lines.append("")
    return "\n".join(lines)


def export_character_glossary(
    db_path: str,
    out_dir: str,
    civ_id: int | None = None,
    active_only: bool = False,
    title: str = "Personnages",
    style: ExportStyle | None = None,
) -> dict[str, str]:
    """Export a character glossary (persons + per-chapter history) as md + json.

    Only ``person`` entities are included. Returns {format: path}. ``style`` is
    accepted for signature symmetry (this exporter has no colours).
    """
    conn = db.get_connection(db_path)
    persons = db.fetch_all_entities(conn, entity_type="person", civ_id=civ_id, active_only=active_only)
    records = [_character_record(conn, e) for e in persons]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "characters.md"
    json_path = out / "characters.json"

    md_path.write_text(_render_markdown(records, title), encoding="utf-8")
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"md": str(md_path), "json": str(json_path), "count": str(len(records))}
