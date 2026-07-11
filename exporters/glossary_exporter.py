"""Glossary exporter — entities to Markdown + JSON.

WHAT: Reads all (optionally filtered) entities and emits two artefacts in an
output directory: glossary.md (human, grouped by entity type) and glossary.json
(machine, flat list). Each entry carries canonical_name, description, aliases
and active/inactive status.

WHY double format: the wishlist wants machine + human outputs so they compose
(embed the json in a wiki build, hand the md to the GM). Generalises the wiki's
generate_civ_entities, but with no civ partitioning and no hardcoded French.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import db
from .models import Entity
from .style import ExportStyle


def _entity_record(conn, e: Entity) -> dict:
    """Build the machine (json) record for one entity, including its aliases."""
    return {
        "id": e.id,
        "canonical_name": e.canonical_name,
        "entity_type": e.entity_type,
        "description": e.description,
        "aliases": db.fetch_aliases(conn, e.id),
        "is_active": e.is_active,
        "civ_id": e.civ_id,
    }


def _render_markdown(records: list[dict], title: str) -> str:
    """Render the glossary as Markdown, grouped by entity_type then name.

    COMMENT: headings use the raw entity_type key (already an English ontology
    token like "person"), so nothing here is language-specific. Inactive
    entities are flagged inline so the reader sees lifecycle without extra tools.
    """
    lines: list[str] = [f"# {title}", ""]
    # group by type, stable alphabetical order of the type keys
    by_type: dict[str, list[dict]] = {}
    for r in records:
        by_type.setdefault(r["entity_type"], []).append(r)

    for etype in sorted(by_type):
        entries = sorted(by_type[etype], key=lambda r: r["canonical_name"].lower())
        lines.append(f"## {etype} ({len(entries)})")
        lines.append("")
        for r in entries:
            status = "" if r["is_active"] else " _(inactive)_"
            header = f"**{r['canonical_name']}**{status}"
            if r["aliases"]:
                header += f" — _aka {', '.join(r['aliases'])}_"
            lines.append(f"- {header}")
            if r["description"]:
                lines.append(f"  {r['description']}")
        lines.append("")
    return "\n".join(lines)


def export_glossary(
    db_path: str,
    out_dir: str,
    entity_type: str | None = None,
    civ_id: int | None = None,
    active_only: bool = False,
    title: str = "Glossary",
    style: ExportStyle | None = None,
) -> dict[str, str]:
    """Export the glossary to <out_dir>/glossary.md and glossary.json.

    Returns a dict of {format: path} for the caller/CLI. ``style`` is accepted
    for signature symmetry with the other exporters (glossary has no colours).
    """
    conn = db.get_connection(db_path)
    entities = db.fetch_all_entities(conn, entity_type=entity_type, civ_id=civ_id, active_only=active_only)
    records = [_entity_record(conn, e) for e in entities]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "glossary.md"
    json_path = out / "glossary.json"

    md_path.write_text(_render_markdown(records, title), encoding="utf-8")
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"md": str(md_path), "json": str(json_path), "count": str(len(records))}
