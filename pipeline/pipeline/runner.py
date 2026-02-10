"""Pipeline orchestrator --chains all processing stages end-to-end.

Usage:
    python -m pipeline.runner --data-dir ../civjdr/Background --civ "Civilisation de la Confluence" --db aurelm.db
    python -m pipeline.runner --data-dir ../civjdr/Background --civ "Civilisation de la Confluence" --db aurelm.db --no-llm
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .db import get_connection, init_db, register_civilization
from .loader import load_directory
from .ingestion import fetch_unprocessed_messages
from .chunker import detect_turn_boundaries
from .classifier import classify_segments
from .ner import EntityExtractor
from .summarizer import summarize_turn


# Known GM author names --messages from these authors are GM posts
GM_AUTHORS = {"Arthur Ignatus", "arthur ignatus"}

CHANNEL_ID = "file-import"


def run_pipeline(
    data_dir: str,
    db_path: str,
    civ_name: str,
    player_name: str | None = None,
    use_llm: bool = True,
    wiki_dir: str | None = None,
) -> dict:
    """Run the full pipeline: load -> chunk -> classify -> NER -> summarize -> persist.

    Returns a stats dict with counts of processed items.
    """
    stats = {
        "messages_loaded": 0,
        "turns_created": 0,
        "entities_extracted": 0,
        "segments_created": 0,
    }

    # Step 1: Init DB
    print("[1/7] Initializing database...")
    init_db(db_path)

    # Step 2: Register civilization
    print(f"[2/7] Registering civilization: {civ_name}")
    civ_id = register_civilization(db_path, civ_name, player_name=player_name)

    # Step 3: Load markdown files
    print(f"[3/7] Loading markdown files from {data_dir}...")
    msg_count = load_directory(data_dir, db_path, channel_id=CHANNEL_ID)
    stats["messages_loaded"] = msg_count
    print(f"       -> {msg_count} messages in database")

    # Step 4: Fetch unprocessed messages
    print("[4/7] Fetching unprocessed messages...")
    messages = fetch_unprocessed_messages(db_path, CHANNEL_ID)
    print(f"       ->{len(messages)} unprocessed messages")

    if not messages:
        print("       No new messages to process.")
        return stats

    # Step 5: Detect turn boundaries
    print("[5/7] Detecting turn boundaries...")
    gm_author_id = _find_gm_author_id(messages)
    chunks = detect_turn_boundaries(messages, gm_author_id)
    print(f"       ->{len(chunks)} turns detected")

    # Step 6: Process each turn
    print("[6/7] Processing turns (classify -> NER -> summarize)...")
    extractor = _init_ner()

    conn = get_connection(db_path)
    run_id = _start_pipeline_run(conn)

    try:
        turn_number = _get_next_turn_number(conn, civ_id)

        for i, chunk in enumerate(chunks):
            turn_text = "\n\n".join(m.content for m in chunk.messages)
            raw_ids = json.dumps([m.id for m in chunk.messages])

            # Create turn record
            cursor = conn.execute(
                """INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type)
                   VALUES (?, ?, ?, ?)""",
                (civ_id, turn_number, raw_ids, chunk.turn_type),
            )
            turn_id = cursor.lastrowid
            stats["turns_created"] += 1

            # Classify segments
            segments = classify_segments(turn_text)
            for seg_order, seg in enumerate(segments):
                conn.execute(
                    """INSERT INTO turn_segments (turn_id, segment_order, segment_type, content)
                       VALUES (?, ?, ?, ?)""",
                    (turn_id, seg_order, seg.segment_type.value, seg.text),
                )
                stats["segments_created"] += 1

            # Extract entities
            if extractor:
                entities = extractor.extract(turn_text)
                for ent in entities:
                    entity_id = _upsert_entity(conn, ent.text, ent.label, civ_id, turn_id)
                    conn.execute(
                        """INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context)
                           VALUES (?, ?, ?, ?)""",
                        (entity_id, turn_id, ent.text, ent.context),
                    )
                    stats["entities_extracted"] += 1

            # Summarize
            summary = summarize_turn(turn_text, use_llm=use_llm)
            conn.execute(
                "UPDATE turn_turns SET summary = ?, processed_at = ? WHERE id = ?",
                (summary.short_summary, datetime.now().isoformat(), turn_id),
            )

            turn_number += 1

            if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                print(f"       ->Processed {i + 1}/{len(chunks)} turns")

        conn.commit()
        _complete_pipeline_run(conn, run_id, stats)

    except Exception as e:
        conn.rollback()
        _fail_pipeline_run(conn, run_id, str(e))
        raise
    finally:
        conn.close()

    # Step 7: Wiki generation (optional)
    if wiki_dir:
        print("[7/8] Generating wiki...")
        try:
            from wiki.generate import generate_wiki
            wiki_out = str(Path(wiki_dir) / "docs")
            wiki_stats = generate_wiki(db_path, wiki_out)
            stats["wiki_pages"] = wiki_stats["pages_generated"]
            print(f"       -> {wiki_stats['pages_generated']} pages generated")
        except ImportError:
            # wiki module may not be importable from pipeline context
            # try direct import by path
            import importlib.util
            wiki_gen_path = Path(wiki_dir) / "generate.py"
            if wiki_gen_path.exists():
                spec = importlib.util.spec_from_file_location("wiki_generate", wiki_gen_path)
                mod = importlib.util.module_from_spec(spec)  # type: ignore
                spec.loader.exec_module(mod)  # type: ignore
                wiki_out = str(Path(wiki_dir) / "docs")
                wiki_stats = mod.generate_wiki(db_path, wiki_out)
                stats["wiki_pages"] = wiki_stats["pages_generated"]
                print(f"       -> {wiki_stats['pages_generated']} pages generated")
            else:
                print("       WARNING: wiki/generate.py not found -- skipping wiki generation")
    else:
        print("[7/7] Skipping wiki generation (use --wiki-dir to enable)")

    # Final summary
    print("[DONE] Pipeline complete!")
    _print_stats(stats)
    return stats


def _init_ner() -> EntityExtractor | None:
    """Initialize the NER extractor, returning None if spaCy model not available."""
    try:
        return EntityExtractor()
    except OSError:
        print("       WARNING: spaCy model fr_core_news_lg not found -- skipping NER")
        return None


def _find_gm_author_id(messages: list) -> str:
    """Find the GM's author_id from known GM author names."""
    for msg in messages:
        if msg.author_name in GM_AUTHORS:
            return msg.author_id
    # Fallback: first message author is probably the GM
    return messages[0].author_id if messages else ""


def _get_next_turn_number(conn, civ_id: int) -> int:
    """Get the next available turn number for a civilization."""
    row = conn.execute(
        "SELECT COALESCE(MAX(turn_number), 0) + 1 FROM turn_turns WHERE civ_id = ?",
        (civ_id,),
    ).fetchone()
    return row[0]


def _upsert_entity(conn, name: str, entity_type: str, civ_id: int, turn_id: int) -> int:
    """Insert or update an entity, returning its id."""
    row = conn.execute(
        "SELECT id FROM entity_entities WHERE canonical_name = ? AND civ_id = ?",
        (name, civ_id),
    ).fetchone()

    if row:
        entity_id = row[0]
        conn.execute(
            "UPDATE entity_entities SET last_seen_turn = ?, updated_at = ? WHERE id = ?",
            (turn_id, datetime.now().isoformat(), entity_id),
        )
        return entity_id

    cursor = conn.execute(
        """INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn, last_seen_turn)
           VALUES (?, ?, ?, ?, ?)""",
        (name, entity_type, civ_id, turn_id, turn_id),
    )
    return cursor.lastrowid  # type: ignore[return-value]


def _start_pipeline_run(conn) -> int:
    """Record the start of a pipeline run."""
    cursor = conn.execute(
        "INSERT INTO pipeline_runs (status) VALUES ('running')"
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def _complete_pipeline_run(conn, run_id: int, stats: dict) -> None:
    """Mark a pipeline run as completed."""
    conn.execute(
        """UPDATE pipeline_runs
           SET status = 'completed', completed_at = ?,
               messages_processed = ?, turns_created = ?, entities_extracted = ?
           WHERE id = ?""",
        (datetime.now().isoformat(), stats["messages_loaded"],
         stats["turns_created"], stats["entities_extracted"], run_id),
    )
    conn.commit()


def _fail_pipeline_run(conn, run_id: int, error: str) -> None:
    """Mark a pipeline run as failed."""
    conn.execute(
        "UPDATE pipeline_runs SET status = 'failed', completed_at = ?, error_message = ? WHERE id = ?",
        (datetime.now().isoformat(), error, run_id),
    )
    conn.commit()


def _print_stats(stats: dict) -> None:
    """Print pipeline run statistics."""
    print()
    print("=" * 40)
    print("Pipeline Results")
    print("=" * 40)
    print(f"  Messages loaded:     {stats['messages_loaded']}")
    print(f"  Turns created:       {stats['turns_created']}")
    print(f"  Segments created:    {stats['segments_created']}")
    print(f"  Entity mentions:     {stats['entities_extracted']}")
    print("=" * 40)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurelm ML Pipeline")
    parser.add_argument("--data-dir", required=True, help="Path to markdown files directory")
    parser.add_argument("--civ", required=True, help="Civilization name")
    parser.add_argument("--db", default="aurelm.db", help="Database file path")
    parser.add_argument("--player", default=None, help="Player name")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM summarization (use extractive fallback)")
    parser.add_argument("--wiki-dir", default=None, help="Wiki directory (enables wiki generation)")
    args = parser.parse_args()

    run_pipeline(
        data_dir=args.data_dir,
        db_path=args.db,
        civ_name=args.civ,
        player_name=args.player,
        use_llm=not args.no_llm,
        wiki_dir=args.wiki_dir,
    )


if __name__ == "__main__":
    main()
