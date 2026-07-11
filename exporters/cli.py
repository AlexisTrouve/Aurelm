"""Command-line interface for the headless exporters.

WHAT: ``python -m exporters <graph|glossary|history> --db PATH ...`` — one
subcommand per exporter, all read-only, all working on any Aurelm DB.

WHY a single CLI: mirrors the wiki generator's argparse entrypoint so the
exporters are scriptable/pipeline-friendly without importing Python. Styling
overrides (font, background) are shared flags that build an ExportStyle.
"""

from __future__ import annotations

import argparse
import sys

from .style import ExportStyle


def _build_style(args: argparse.Namespace) -> ExportStyle:
    """Construct an ExportStyle from the shared styling flags."""
    style = ExportStyle()
    if getattr(args, "font", None):
        style.font_path = args.font
    if getattr(args, "background", None):
        style.background = args.background
    return style


def _parse_filter(expr: str | None) -> str | None:
    """Parse a ``--filter entity_type=VALUE`` expression to the type value.

    Only entity_type filtering is supported today; anything else is a hard error
    (no silent ignore that would produce a misleading graph).
    """
    if not expr:
        return None
    if "=" not in expr:
        raise SystemExit(f"--filter must be key=value, got: {expr!r}")
    key, _, value = expr.partition("=")
    key = key.strip()
    if key != "entity_type":
        raise SystemExit(f"--filter only supports 'entity_type', got: {key!r}")
    return value.strip() or None


def _cmd_graph(args: argparse.Namespace) -> dict:
    from .graph_exporter import export_graph
    center: str | int = args.center_id if args.center_id is not None else args.center
    if center is None:
        raise SystemExit("graph: provide --center NAME or --center-id N")
    formats = tuple(f.strip() for f in args.format.split(",") if f.strip())
    return export_graph(
        db_path=args.db, center=center, out_base=args.out, depth=args.depth,
        entity_type=_parse_filter(args.filter), formats=formats,
        title=args.title, style=_build_style(args),
    )


def _cmd_glossary(args: argparse.Namespace) -> dict:
    from .glossary_exporter import export_glossary
    return export_glossary(
        db_path=args.db, out_dir=args.out, entity_type=args.type,
        civ_id=args.civ_id, active_only=args.active_only,
        title=args.title, style=_build_style(args),
    )


def _cmd_history(args: argparse.Namespace) -> dict:
    from .history_exporter import export_history
    entity: str | int | None = args.entity_id if args.entity_id is not None else args.entity
    return export_history(
        db_path=args.db, out_dir=args.out, entity=entity,
        title=args.title, style=_build_style(args),
    )


def _add_style_flags(p: argparse.ArgumentParser) -> None:
    """Attach the styling flags shared by every subcommand."""
    p.add_argument("--font", help="Path to a TTF/TTC font (default: auto CJK-capable)")
    p.add_argument("--background", help="Background colour hex, e.g. #FFFFFF")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m exporters",
                                     description="Headless exporters for any Aurelm DB.")
    sub = parser.add_subparsers(dest="kind", required=True)

    # graph
    g = sub.add_parser("graph", help="Radial ego-graph -> PNG + SVG")
    g.add_argument("--db", required=True)
    g.add_argument("--center", help="Center entity name")
    g.add_argument("--center-id", type=int, help="Center entity id (overrides --center)")
    g.add_argument("--depth", type=int, default=1, help="BFS depth from center (default 1)")
    g.add_argument("--filter", help="Node filter, e.g. entity_type=person")
    g.add_argument("--out", default="graph", help="Output path base (no extension)")
    g.add_argument("--format", default="png,svg", help="Comma list: png,svg")
    g.add_argument("--title", help="Title (default: center name)")
    _add_style_flags(g)
    g.set_defaults(func=_cmd_graph)

    # glossary
    gl = sub.add_parser("glossary", help="Entities -> Markdown + JSON")
    gl.add_argument("--db", required=True)
    gl.add_argument("--type", help="Filter by entity_type")
    gl.add_argument("--civ-id", type=int, help="Filter by civ scope id")
    gl.add_argument("--active-only", action="store_true")
    gl.add_argument("--out", default="glossary_out", help="Output directory")
    gl.add_argument("--title", default="Glossary")
    _add_style_flags(gl)
    gl.set_defaults(func=_cmd_glossary)

    # history
    h = sub.add_parser("history", help="Per-entity history -> Markdown + JSON")
    h.add_argument("--db", required=True)
    h.add_argument("--entity", help="Entity name (omit for all entities)")
    h.add_argument("--entity-id", type=int, help="Entity id (overrides --entity)")
    h.add_argument("--out", default="history_out", help="Output directory")
    h.add_argument("--title", default="History")
    _add_style_flags(h)
    h.set_defaults(func=_cmd_history)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the chosen exporter, print the resulting paths."""
    args = build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except (LookupError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0
