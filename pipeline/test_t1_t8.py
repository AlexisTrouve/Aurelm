"""Test T1-T8: runs the full pipeline on a range of turns and shows per-turn entity growth.

Usage (from pipeline/ dir):
    py -3.12 test_t1_t8.py [--version v20-clean] [--config pipeline_llm_config.json] [--turns 1-3]

What it shows:
    - Per-turn entity extraction funnel (raw/dedup/final)
    - Entity lookup growth (how many known entities injected as hints each turn)
    - Fuzzy matches found per turn
    - Final entity list with types
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import re

SRC = r"C:\Users\alexi\Documents\projects\civjdr\Background"
DB_PATH = r"C:\Users\alexi\AppData\Local\Temp\t1_t8_test.db"
CIV = "Civilisation de la Confluence"


def parse_turns(turns_arg: str) -> list[int]:
    """Parse a turns range string like '1-3' or '1,3,5' into a list of ints."""
    turns = []
    for part in turns_arg.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            turns.extend(range(int(start), int(end) + 1))
        else:
            turns.append(int(part))
    return sorted(set(turns))


def normalize(text):
    text = text.lower().strip()
    text = text.replace("\u0153", "oe").replace("\u0152", "oe")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    for art in ["l'", "le ", "la ", "les "]:
        if text.startswith(art):
            text = text[len(art):]
    return text


def copy_turn_files(src_dir: str, dest_dir: str, turns: list[int]) -> list[str]:
    """Copy MJ + PJ files for the given turn numbers to dest_dir."""
    copied = []
    for fname in sorted(os.listdir(src_dir)):
        # Match mj-T01 through T08 and corresponding pj files
        for t in turns:
            tag = f"-T{t:02d}-"
            if tag in fname:
                shutil.copy(os.path.join(src_dir, fname), dest_dir)
                copied.append(fname)
                break
    return copied


def inspect_db(db_path: str):
    """Print entity list + lookup stats from the DB."""
    from pipeline.db import get_connection
    conn = get_connection(db_path)
    conn.row_factory = __import__("sqlite3").Row

    # Per-turn extraction funnel from pipeline_turn_stats
    print("\n=== Per-turn extraction funnel ===")
    print(f"  {'Turn':>4}  {'Src':>3}  {'Chars':>6}  {'Raw':>4}  {'DD':>4}  {'Fin':>4}  {'Lookup':>6}")
    print(f"  {'----':>4}  {'---':>3}  {'------':>6}  {'----':>4}  {'----':>4}  {'----':>4}  {'------':>6}")
    rows = conn.execute(
        """SELECT ts.source, tt.turn_number, ts.text_chars,
                  ts.raw_entities, ts.after_dedup, ts.final_entities
           FROM pipeline_turn_stats ts
           JOIN turn_turns tt ON ts.turn_id = tt.id
           ORDER BY tt.turn_number, ts.source"""
    ).fetchall()
    for r in rows:
        print(
            f"  T{r['turn_number']:02d}   {r['source']:>3}  "
            f"{r['text_chars']:>6}  {r['raw_entities']:>4}  "
            f"{r['after_dedup']:>4}  {r['final_entities']:>4}  n/a"
        )

    # Entity list
    print("\n=== Entities extracted ===")
    entities = conn.execute(
        "SELECT canonical_name, entity_type FROM entity_entities "
        "WHERE is_active=1 ORDER BY entity_type, canonical_name"
    ).fetchall()
    by_type: dict = {}
    for e in entities:
        by_type.setdefault(e["entity_type"], []).append(e["canonical_name"])
    for etype, names in sorted(by_type.items()):
        print(f"  [{etype}] ({len(names)})")
        for n in names:
            print(f"    - {n}")

    # Prompt log sample — last 3 calls
    print("\n=== Last 3 LLM calls logged ===")
    calls = conn.execute(
        "SELECT turn_id, stage, model, length(user_prompt) as plen, "
        "length(response) as rlen FROM pipeline_llm_calls "
        "ORDER BY id DESC LIMIT 3"
    ).fetchall()
    for c in calls:
        print(
            f"  turn={c['turn_id']} stage={c['stage']} model={c['model']} "
            f"prompt={c['plen']}c response={c['rlen']}c"
        )

    conn.close()
    return len(entities)


def main():
    parser = argparse.ArgumentParser(description="Test pipeline on a range of turns")
    parser.add_argument("--version", default="v20-clean", help="Extraction version")
    parser.add_argument("--config", default="pipeline_llm_config.json", help="LLM config file")
    parser.add_argument("--turns", default="1-8", help="Turn range, e.g. '1-3' or '1,3,5'")
    parser.add_argument("--keep-db", action="store_true", help="Don't delete DB after run")
    args = parser.parse_args()

    turns = parse_turns(args.turns)
    turns_label = args.turns.replace(",", "_")

    # Prepare temp dir with requested turn files
    tmpdir = tempfile.mkdtemp(prefix="aurelm_t1t8_")
    try:
        copied = copy_turn_files(SRC, tmpdir, turns)
        print(f"Copied {len(copied)} files for turns {args.turns}:")
        for f in copied:
            print(f"  {f}")

        # Clean old DB
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        for ext in ["-shm", "-wal"]:
            p = DB_PATH + ext
            if os.path.exists(p):
                os.unlink(p)

        print(f"\nRunning pipeline (version={args.version}, turns={args.turns})...")
        print("=" * 60)

        from pipeline.runner import run_pipeline
        from pipeline.llm_provider import load_llm_config

        llm_cfg = load_llm_config(args.config) if os.path.exists(args.config) else None

        result = run_pipeline(
            data_dir=tmpdir,
            db_path=DB_PATH,
            civ_name=CIV,
            use_llm=True,
            extraction_version=args.version,
            llm_config=llm_cfg,
        )

        print("=" * 60)
        print(f"Pipeline done: {result}")

        n = inspect_db(DB_PATH)
        print(f"\nTotal active entities: {n}")

        if not args.keep_db:
            print(f"\nDB kept at: {DB_PATH}")
            print("(delete manually or rerun to overwrite)")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
