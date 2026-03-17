"""Backfill inter-civ relations on an existing database.

Runs two steps on all (or one) civilization(s):
  1. Detection: scan entity_mentions for type=civilization foreign entities
     → populate civ_mentions (idempotent, INSERT OR IGNORE)
  2. Profiling: LLM call per (source_civ, target_civ) pair
     → upsert civ_relations with opinion + description + treaties

Safe to re-run: detection is idempotent, profiling overwrites existing rows.

Usage:
    py -3.12 -m pipeline.scripts.backfill_civ_relations --db aurelm.db
    py -3.12 -m pipeline.scripts.backfill_civ_relations --db aurelm.db --no-llm
    py -3.12 -m pipeline.scripts.backfill_civ_relations --db aurelm.db --civ Confluence
    py -3.12 -m pipeline.scripts.backfill_civ_relations --db aurelm.db --model qwen3:8b

Or run as a script from the project root:
    py -3.12 pipeline/scripts/backfill_civ_relations.py --db aurelm.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a standalone script from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.pipeline.db import get_connection
from pipeline.pipeline.runner import _detect_civ_mentions
from pipeline.pipeline.civ_relation_profiler import build_civ_relations
from pipeline.pipeline.llm_provider import create_provider, load_llm_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill civ_mentions + civ_relations on an existing DB."
    )
    parser.add_argument("--db", required=True, help="Path to aurelm.db")
    parser.add_argument(
        "--civ",
        default=None,
        help="Restrict to one civilization (fuzzy match on name). Default: all civs.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM profiling — only populate civ_mentions (opinion stays 'unknown').",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override LLM model for profiling (default: from pipeline_llm_config.json or llama3.1:8b).",
    )
    parser.add_argument(
        "--llm-config",
        default="pipeline_llm_config.json",
        help="Path to LLM config JSON (default: pipeline_llm_config.json).",
    )
    args = parser.parse_args()

    db_path = args.db
    use_llm = not args.no_llm

    # Load LLM config + provider
    llm_config = load_llm_config(args.llm_config) if Path(args.llm_config).exists() else None
    provider = None
    model = args.model or (llm_config.get_model("profiling") if llm_config else "llama3.1:8b")

    if use_llm:
        try:
            provider = create_provider(llm_config)
            print(f"LLM provider: {type(provider).__name__} | model: {model}")
        except Exception as e:
            print(f"[warn] Could not create LLM provider: {e}. Falling back to --no-llm.")
            use_llm = False

    # --- Step 1: detection ---
    conn = get_connection(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Resolve civ filter
    if args.civ:
        civ_rows = conn.execute(
            "SELECT id, name FROM civ_civilizations WHERE name LIKE ?",
            (f"%{args.civ}%",),
        ).fetchall()
        if not civ_rows:
            print(f"Error: no civilization matching '{args.civ}'.")
            conn.close()
            sys.exit(1)
        civs = [(r["id"], r["name"]) for r in civ_rows]
    else:
        civs = [
            (r["id"], r["name"])
            for r in conn.execute(
                "SELECT id, name FROM civ_civilizations ORDER BY name"
            ).fetchall()
        ]

    print(f"\n{'='*60}")
    print(f"DB: {db_path}")
    print(f"Civs to process: {', '.join(n for _, n in civs)}")
    print(f"LLM profiling: {'yes' if use_llm else 'no (--no-llm)'}")
    print(f"{'='*60}\n")

    total_mentions_inserted = 0

    print("[1/2] Detecting foreign-civ mentions in entity_mentions...")
    for civ_id, civ_name in civs:
        # Fetch all turns for this civ with their summaries
        turns = conn.execute(
            "SELECT id, turn_number, summary FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
            (civ_id,),
        ).fetchall()

        civ_mentions_before = conn.execute(
            "SELECT COUNT(*) FROM civ_mentions WHERE source_civ_id = ?", (civ_id,)
        ).fetchone()[0]

        for turn in turns:
            context = (turn["summary"] or "")[:500]
            _detect_civ_mentions(conn, civ_id, turn["id"], context)

        civ_mentions_after = conn.execute(
            "SELECT COUNT(*) FROM civ_mentions WHERE source_civ_id = ?", (civ_id,)
        ).fetchone()[0]
        inserted = civ_mentions_after - civ_mentions_before
        total_mentions_inserted += inserted

        if civ_mentions_after > 0:
            print(
                f"  {civ_name}: {civ_mentions_after} pairs total"
                + (f" (+{inserted} new)" if inserted else " (no change)")
            )
        else:
            print(f"  {civ_name}: no foreign-civ mentions found")

    conn.commit()
    conn.close()

    print(f"\n  -> {total_mentions_inserted} new civ_mention rows inserted")

    # --- Step 2: profiling ---
    print(f"\n[2/2] Profiling inter-civ relations {'(LLM)' if use_llm else '(no-llm, opinion=unknown)'}...")

    total_relations = 0
    for civ_id, civ_name in civs:
        stats = build_civ_relations(
            db_path,
            source_civ_id=civ_id,
            model=model,
            provider=provider,
            use_llm=use_llm,
        )
        if stats["pairs_found"]:
            print(
                f"  {civ_name}: {stats['relations_built']} relation(s) profiled"
                f" ({stats['pairs_found']} pair(s))"
            )
            total_relations += stats["relations_built"]
        else:
            print(f"  {civ_name}: no pairs to profile")

    if use_llm and provider:
        usage = provider.get_usage()
        cost_str = f"${usage.get('total_cost', 0):.4f}" if usage.get("total_cost") else "n/a"
        print(f"\nCost: {cost_str}")

    print(f"\nDone. {total_relations} relation(s) upserted into civ_relations.")


if __name__ == "__main__":
    main()
