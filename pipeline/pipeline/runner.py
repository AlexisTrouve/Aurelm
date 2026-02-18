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

from .db import (
    get_connection,
    init_db,
    register_civilization,
    run_migrations,
    mark_turn_processed,
    update_progress,
)
from .loader import load_directory
from .ingestion import fetch_unprocessed_messages
from .chunker import detect_turn_boundaries
from .classifier import classify_segments
from .ner import EntityExtractor
from .summarizer import summarize_turn, AuthorContent
from .entity_profiler import build_entity_profiles
from .alias_resolver import resolve_aliases
from .fact_extractor import FactExtractor
from . import llm_stats


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
    track_progress: bool = False,
) -> dict:
    """Run the full pipeline: load -> chunk -> classify -> NER -> summarize -> persist.

    Returns a stats dict with counts of processed items.
    """
    _entity_cache.clear()
    llm_stats.reset()

    stats = {
        "messages_loaded": 0,
        "turns_created": 0,
        "entities_extracted": 0,
        "segments_created": 0,
    }

    # Step 1: Init DB
    print("[1/9] Initializing database...")
    init_db(db_path)
    run_migrations(db_path)

    # Step 2: Register civilization
    print(f"[2/9] Registering civilization: {civ_name}")
    civ_id = register_civilization(db_path, civ_name, player_name=player_name)

    # Step 3: Load markdown files
    print(f"[3/9] Loading markdown files from {data_dir}...")
    msg_count = load_directory(data_dir, db_path, channel_id=CHANNEL_ID)
    stats["messages_loaded"] = msg_count
    print(f"       -> {msg_count} messages in database")

    # Step 4: Fetch unprocessed messages
    print("[4/9] Fetching unprocessed messages...")
    messages = fetch_unprocessed_messages(db_path, CHANNEL_ID)
    print(f"       ->{len(messages)} unprocessed messages")

    if not messages:
        print("       No new messages to process.")
        return stats

    # Step 5: Detect turn boundaries
    print("[5/9] Detecting turn boundaries...")
    gm_author_id = _find_gm_author_id(messages)
    chunks = detect_turn_boundaries(messages, gm_author_id)
    print(f"       ->{len(chunks)} turns detected")

    # Step 6: Process each turn
    print("[6/9] Processing turns (classify -> extract facts -> NER -> summarize)...")
    extractor = _init_ner()
    fact_extractor = FactExtractor() if use_llm else None

    conn = get_connection(db_path)
    run_id = _start_pipeline_run(conn)

    try:
        turn_number = _get_next_turn_number(conn, civ_id)
        total_turns = len(chunks)

        for i, chunk in enumerate(chunks):
            turn_text = "\n\n".join(m.content for m in chunk.messages)
            raw_ids = json.dumps([m.id for m in chunk.messages])
            raw_content = "\n\n".join(m.content for m in chunk.messages)  # For media extraction

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

            # Extract structured facts
            structured_facts = None
            if fact_extractor:
                segment_dicts = [
                    {"segment_type": seg.segment_type.value, "content": seg.text}
                    for seg in segments
                ]
                structured_facts = fact_extractor.extract_facts(segment_dicts, raw_content)

            # Insert segments
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

            # Summarize -- multi-call: 1 LLM call per author
            author_contents = _split_by_author(chunk.messages, gm_author_id)
            summary = summarize_turn(
                turn_text, use_llm=use_llm,
                civ_name=civ_name, player_name=player_name,
                author_contents=author_contents if use_llm else None,
            )

            # Persist summary + structured facts
            update_fields = {
                "summary": summary.short_summary,
                "detailed_summary": summary.detailed_summary,
                "key_events": json.dumps(summary.key_events, ensure_ascii=False) if summary.key_events else None,
                "choices_made": json.dumps(summary.choices_made, ensure_ascii=False) if summary.choices_made else None,
                "processed_at": datetime.now().isoformat(),
            }

            if structured_facts:
                update_fields["media_links"] = json.dumps(structured_facts.media_links, ensure_ascii=False)
                update_fields["technologies"] = json.dumps(structured_facts.technologies, ensure_ascii=False)
                update_fields["resources"] = json.dumps(structured_facts.resources, ensure_ascii=False)
                update_fields["beliefs"] = json.dumps(structured_facts.beliefs, ensure_ascii=False)
                update_fields["geography"] = json.dumps(structured_facts.geography, ensure_ascii=False)
                update_fields["choices_proposed"] = json.dumps(structured_facts.choices_proposed, ensure_ascii=False)

            conn.execute(
                """UPDATE turn_turns
                   SET summary = ?, detailed_summary = ?,
                       key_events = ?, choices_made = ?, processed_at = ?,
                       media_links = ?, technologies = ?, resources = ?,
                       beliefs = ?, geography = ?, choices_proposed = ?
                   WHERE id = ?""",
                (
                    update_fields["summary"],
                    update_fields["detailed_summary"],
                    update_fields["key_events"],
                    update_fields["choices_made"],
                    update_fields["processed_at"],
                    update_fields.get("media_links"),
                    update_fields.get("technologies"),
                    update_fields.get("resources"),
                    update_fields.get("beliefs"),
                    update_fields.get("geography"),
                    update_fields.get("choices_proposed"),
                    turn_id,
                ),
            )

            # Mark turn as processed
            mark_turn_processed(conn, turn_id, run_id)

            # Update progress tracking
            if track_progress:
                update_progress(
                    conn, run_id, "pipeline", civ_id, civ_name,
                    i + 1, total_turns, "turn", "running"
                )

            turn_number += 1

            if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                print(f"       ->Processed {i + 1}/{len(chunks)} turns")

        # Mark pipeline phase as completed
        if track_progress and total_turns > 0:
            update_progress(
                conn, run_id, "pipeline", civ_id, civ_name,
                total_turns, total_turns, "turn", "completed"
            )

        conn.commit()
        _complete_pipeline_run(conn, run_id, stats)

    except Exception as e:
        conn.rollback()
        _fail_pipeline_run(conn, run_id, str(e))
        raise
    finally:
        conn.close()

    # Step 7: Entity profiling (LLM-based)
    if use_llm:
        print("[7/9] Building entity profiles (1 LLM call per entity)...")
        profiles = build_entity_profiles(
            db_path,
            use_llm=True,
            incremental=True,
            run_id=run_id,
            track_progress=track_progress,
        )
        stats["entities_profiled"] = len([p for p in profiles if p.description])

        # Step 8: Alias resolution
        print("[8/9] Resolving entity aliases...")
        alias_stats = resolve_aliases(db_path, profiles, use_llm=True)
        stats["alias_candidates"] = alias_stats.get("candidates_found", 0)
        stats["aliases_confirmed"] = alias_stats.get("aliases_confirmed", 0)
    else:
        print("[7/9] Skipping entity profiling (--no-llm)")
        print("[8/9] Skipping alias resolution (--no-llm)")

    # Step 9: Wiki generation (optional)
    if wiki_dir:
        print("[9/9] Generating wiki...")

        # Progress callback for wiki generation
        def wiki_progress(current, total, unit_type):
            if track_progress:
                conn_progress = get_connection(db_path)
                try:
                    update_progress(
                        conn_progress, run_id, "wiki", None, None,
                        current, total, unit_type, "running"
                    )
                    conn_progress.commit()
                finally:
                    conn_progress.close()

        try:
            from wiki.generate import generate_wiki
            wiki_out = str(Path(wiki_dir) / "docs")
            wiki_stats = generate_wiki(
                db_path, wiki_out,
                progress_callback=wiki_progress if track_progress else None,
                run_id=run_id,
            )
            stats["wiki_pages"] = wiki_stats["pages_generated"]
            print(f"       -> {wiki_stats['pages_generated']} pages generated")

            # Mark wiki phase as completed
            if track_progress:
                conn_progress = get_connection(db_path)
                try:
                    total = stats["wiki_pages"]
                    update_progress(
                        conn_progress, run_id, "wiki", None, None,
                        total, total, "page", "completed"
                    )
                    conn_progress.commit()
                finally:
                    conn_progress.close()
        except ImportError:
            # wiki module may not be importable from pipeline context
            # try direct import by path
            import importlib.util
            wiki_gen_path = Path(wiki_dir) / "generate.py"
            if wiki_gen_path.exists():
                # Add wiki dir to sys.path so relative imports (turn_page_generator) work
                import sys
                wiki_abs = str(wiki_gen_path.parent.resolve())
                if wiki_abs not in sys.path:
                    sys.path.insert(0, wiki_abs)
                spec = importlib.util.spec_from_file_location("wiki_generate", wiki_gen_path)
                mod = importlib.util.module_from_spec(spec)  # type: ignore
                spec.loader.exec_module(mod)  # type: ignore
                wiki_out = str(Path(wiki_dir) / "docs")
                wiki_stats = mod.generate_wiki(
                    db_path, wiki_out,
                    progress_callback=wiki_progress if track_progress else None,
                    run_id=run_id,
                )
                stats["wiki_pages"] = wiki_stats["pages_generated"]
                print(f"       -> {wiki_stats['pages_generated']} pages generated")

                # Mark wiki phase as completed
                if track_progress:
                    conn_progress = get_connection(db_path)
                    try:
                        total = stats["wiki_pages"]
                        update_progress(
                            conn_progress, run_id, "wiki", None, None,
                            total, total, "page", "completed"
                        )
                        conn_progress.commit()
                    finally:
                        conn_progress.close()
            else:
                print("       WARNING: wiki/generate.py not found -- skipping wiki generation")
    else:
        print("[9/9] Skipping wiki generation (use --wiki-dir to enable)")

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


def _split_by_author(messages: list, gm_author_id: str) -> list[AuthorContent]:
    """Group consecutive messages by author role (GM vs player) for multi-call LLM."""
    groups: list[AuthorContent] = []
    for msg in messages:
        is_gm = msg.author_id == gm_author_id
        # Merge with previous group if same role
        if groups and groups[-1].is_gm == is_gm:
            groups[-1].content += "\n\n" + msg.content
        else:
            groups.append(AuthorContent(
                author=msg.author_name,
                is_gm=is_gm,
                content=msg.content,
            ))
    return groups


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


def _is_better_display_name(new_name: str, stored_name: str) -> bool:
    """Check if new_name is a better display form (e.g. Title Case vs lowercase)."""
    new_uppers = sum(1 for c in new_name if c.isupper())
    stored_uppers = sum(1 for c in stored_name if c.isupper())
    return new_uppers > stored_uppers


def _normalize_for_dedup(name: str) -> str:
    """Normalize entity name for dedup.

    Steps: strip accents, lowercase, remove leading articles,
    normalize des->de, strip French plural markers.

    'Les Cercles de Vigile' -> 'cercle de vigile'
    'Faucons Chasseurs'     -> 'faucon chasseur'
    'tribunal des mœurs'    -> 'tribunal de moeur'
    'La Vallée'             -> 'vallee'
    'l'Antre des Échos'     -> 'antre de echo'
    """
    import re as _re
    import unicodedata as _ud

    # Strip accents
    nfkd = _ud.normalize("NFKD", name)
    text = "".join(c for c in nfkd if not _ud.combining(c))

    # Lowercase + split on non-word chars
    words = _re.findall(r"[\w']+", text.lower())

    # Strip leading French articles
    articles = {"le", "la", "les", "l", "un", "une", "des", "du"}
    while words and words[0] in articles:
        words.pop(0)

    # Normalize: des -> de (so "tribunal des X" = "tribunal de X")
    normalized = []
    for w in words:
        if w == "des":
            w = "de"
        # Strip trailing 's' for words > 3 chars (not 'ss' like 'bras')
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        normalized.append(w)
    return " ".join(normalized)


# Cache: normalized_name -> (entity_id, canonical_name) per pipeline run
_entity_cache: dict[str, tuple[int, str]] = {}


def _upsert_entity(conn, name: str, entity_type: str, civ_id: int, turn_id: int) -> int:
    """Insert or update an entity, returning its id.

    Uses normalized name (lowercase + depluralized) for dedup.
    First-seen form is kept as canonical_name for display.
    """
    norm = _normalize_for_dedup(name)
    cache_key = f"{norm}|{civ_id}"

    # Check in-memory cache first (fast path)
    if cache_key in _entity_cache:
        entity_id = _entity_cache[cache_key][0]
        conn.execute(
            "UPDATE entity_entities SET last_seen_turn = ?, updated_at = ? WHERE id = ?",
            (turn_id, datetime.now().isoformat(), entity_id),
        )
        return entity_id

    # Check DB: scan existing entities for this civ, match by normalized form
    rows = conn.execute(
        "SELECT id, canonical_name FROM entity_entities WHERE civ_id = ?",
        (civ_id,),
    ).fetchall()

    for row in rows:
        if _normalize_for_dedup(row[1]) == norm:
            entity_id = row[0]
            stored_name = row[1]
            # Prefer Title Case: if new name has uppercase and stored doesn't, update display
            if _is_better_display_name(name, stored_name):
                conn.execute(
                    "UPDATE entity_entities SET canonical_name = ?, last_seen_turn = ?, updated_at = ? WHERE id = ?",
                    (name, turn_id, datetime.now().isoformat(), entity_id),
                )
                _entity_cache[cache_key] = (entity_id, name)
            else:
                conn.execute(
                    "UPDATE entity_entities SET last_seen_turn = ?, updated_at = ? WHERE id = ?",
                    (turn_id, datetime.now().isoformat(), entity_id),
                )
                _entity_cache[cache_key] = (entity_id, stored_name)
            return entity_id

    # No match -- insert new entity
    cursor = conn.execute(
        """INSERT INTO entity_entities (canonical_name, entity_type, civ_id, first_seen_turn, last_seen_turn)
           VALUES (?, ?, ?, ?, ?)""",
        (name, entity_type, civ_id, turn_id, turn_id),
    )
    entity_id = cursor.lastrowid  # type: ignore[return-value]
    _entity_cache[cache_key] = (entity_id, name)
    return entity_id


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
    if "entities_profiled" in stats:
        print(f"  Entities profiled:   {stats['entities_profiled']}")
    if "alias_candidates" in stats:
        print(f"  Alias candidates:    {stats['alias_candidates']}")
    if "aliases_confirmed" in stats:
        print(f"  Aliases confirmed:   {stats['aliases_confirmed']}")
    counts = llm_stats.get_counts()
    if llm_stats.total() > 0:
        print(f"  LLM calls total:     {llm_stats.total()}")
        print(f"    fact extraction:   {counts['fact_extraction']}")
        print(f"    summarization:     {counts['summarization']}")
        print(f"    entity profiling:  {counts['entity_profiling']}")
    print("=" * 40)


def run_pipeline_for_channels(
    db_path: str,
    use_llm: bool = False,
    wiki_dir: str | None = None,
    gm_authors: set[str] | None = None,
    track_progress: bool = True,
) -> dict:
    """Run pipeline for all civs with a discord_channel_id set in DB.

    Called by the bot's /sync endpoint. Processes unprocessed messages
    per channel/civ, then optionally rebuilds wiki.

    Returns aggregated stats across all civs.
    """
    if gm_authors:
        global GM_AUTHORS
        GM_AUTHORS = gm_authors

    init_db(db_path)
    run_migrations(db_path)

    conn = get_connection(db_path)
    civs = conn.execute(
        "SELECT id, name, player_name, discord_channel_id FROM civ_civilizations WHERE discord_channel_id IS NOT NULL"
    ).fetchall()
    conn.close()

    if not civs:
        print("No civilizations with discord_channel_id configured.")
        return {"civs_processed": 0}

    aggregated: dict = {
        "civs_processed": 0,
        "total_turns_created": 0,
        "total_entities_extracted": 0,
        "per_civ": {},
    }

    extractor = _init_ner()
    fact_extractor = FactExtractor() if use_llm else None

    for civ_id, civ_name, player_name, channel_id in civs:
        print(f"\n--- Processing {civ_name} (channel {channel_id}) ---")

        messages = fetch_unprocessed_messages(db_path, channel_id)
        if not messages:
            print(f"  No new messages for {civ_name}")
            aggregated["per_civ"][civ_name] = {"turns_created": 0, "entities_extracted": 0}
            continue

        gm_author_id = _find_gm_author_id(messages)
        chunks = detect_turn_boundaries(messages, gm_author_id)
        print(f"  {len(messages)} messages -> {len(chunks)} turns")

        civ_stats = {"turns_created": 0, "entities_extracted": 0, "segments_created": 0}
        conn = get_connection(db_path)
        run_id = _start_pipeline_run(conn)

        try:
            turn_number = _get_next_turn_number(conn, civ_id)
            total_turns = len(chunks)

            for i, chunk in enumerate(chunks):
                turn_text = "\n\n".join(m.content for m in chunk.messages)
                raw_ids = json.dumps([m.id for m in chunk.messages])
                raw_content = "\n\n".join(m.content for m in chunk.messages)

                cursor = conn.execute(
                    """INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type)
                       VALUES (?, ?, ?, ?)""",
                    (civ_id, turn_number, raw_ids, chunk.turn_type),
                )
                turn_id = cursor.lastrowid
                civ_stats["turns_created"] += 1

                segments = classify_segments(turn_text)

                # Extract structured facts
                structured_facts = None
                if fact_extractor:
                    segment_dicts = [
                        {"segment_type": seg.segment_type.value, "content": seg.text}
                        for seg in segments
                    ]
                    structured_facts = fact_extractor.extract_facts(segment_dicts, raw_content)

                for seg_order, seg in enumerate(segments):
                    conn.execute(
                        """INSERT INTO turn_segments (turn_id, segment_order, segment_type, content)
                           VALUES (?, ?, ?, ?)""",
                        (turn_id, seg_order, seg.segment_type.value, seg.text),
                    )
                    civ_stats["segments_created"] += 1

                if extractor:
                    entities = extractor.extract(turn_text)
                    for ent in entities:
                        entity_id = _upsert_entity(conn, ent.text, ent.label, civ_id, turn_id)
                        conn.execute(
                            """INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context)
                               VALUES (?, ?, ?, ?)""",
                            (entity_id, turn_id, ent.text, ent.context),
                        )
                        civ_stats["entities_extracted"] += 1

                author_contents = _split_by_author(chunk.messages, gm_author_id)
                summary = summarize_turn(
                    turn_text, use_llm=use_llm,
                    civ_name=civ_name, player_name=player_name,
                    author_contents=author_contents if use_llm else None,
                )

                # Persist summary + structured facts
                update_fields = {
                    "summary": summary.short_summary,
                    "detailed_summary": summary.detailed_summary,
                    "key_events": json.dumps(summary.key_events, ensure_ascii=False) if summary.key_events else None,
                    "choices_made": json.dumps(summary.choices_made, ensure_ascii=False) if summary.choices_made else None,
                    "processed_at": datetime.now().isoformat(),
                }

                if structured_facts:
                    update_fields["media_links"] = json.dumps(structured_facts.media_links, ensure_ascii=False)
                    update_fields["technologies"] = json.dumps(structured_facts.technologies, ensure_ascii=False)
                    update_fields["resources"] = json.dumps(structured_facts.resources, ensure_ascii=False)
                    update_fields["beliefs"] = json.dumps(structured_facts.beliefs, ensure_ascii=False)
                    update_fields["geography"] = json.dumps(structured_facts.geography, ensure_ascii=False)
                    update_fields["choices_proposed"] = json.dumps(structured_facts.choices_proposed, ensure_ascii=False)

                conn.execute(
                    """UPDATE turn_turns
                       SET summary = ?, detailed_summary = ?,
                           key_events = ?, choices_made = ?, processed_at = ?,
                           media_links = ?, technologies = ?, resources = ?,
                           beliefs = ?, geography = ?, choices_proposed = ?
                       WHERE id = ?""",
                    (
                        update_fields["summary"],
                        update_fields["detailed_summary"],
                        update_fields["key_events"],
                        update_fields["choices_made"],
                        update_fields["processed_at"],
                        update_fields.get("media_links"),
                        update_fields.get("technologies"),
                        update_fields.get("resources"),
                        update_fields.get("beliefs"),
                        update_fields.get("geography"),
                        update_fields.get("choices_proposed"),
                        turn_id,
                    ),
                )

                # Mark turn as processed
                mark_turn_processed(conn, turn_id, run_id)

                # Update progress tracking
                if track_progress:
                    update_progress(
                        conn, run_id, "pipeline", civ_id, civ_name,
                        i + 1, total_turns, "turn", "running"
                    )

                turn_number += 1

            # Mark pipeline phase as completed for this civ
            if track_progress and total_turns > 0:
                update_progress(
                    conn, run_id, "pipeline", civ_id, civ_name,
                    total_turns, total_turns, "turn", "completed"
                )

            conn.commit()
            _complete_pipeline_run(conn, run_id, {
                "messages_loaded": len(messages),
                "turns_created": civ_stats["turns_created"],
                "entities_extracted": civ_stats["entities_extracted"],
            })
        except Exception as e:
            conn.rollback()
            _fail_pipeline_run(conn, run_id, str(e))
            raise
        finally:
            conn.close()

        aggregated["civs_processed"] += 1
        aggregated["total_turns_created"] += civ_stats["turns_created"]
        aggregated["total_entities_extracted"] += civ_stats["entities_extracted"]
        aggregated["per_civ"][civ_name] = civ_stats

    # Wiki generation
    if wiki_dir and aggregated["total_turns_created"] > 0:
        print("\n--- Generating wiki ---")
        try:
            from wiki.generate import generate_wiki
            wiki_out = str(Path(wiki_dir) / "docs")
            wiki_stats = generate_wiki(db_path, wiki_out)
            aggregated["wiki_pages"] = wiki_stats["pages_generated"]
        except Exception as exc:
            print(f"  Wiki generation failed: {exc}")
            aggregated["wiki_error"] = str(exc)

    return aggregated


def main() -> None:
    parser = argparse.ArgumentParser(description="Aurelm ML Pipeline")
    parser.add_argument("--data-dir", required=True, help="Path to markdown files directory")
    parser.add_argument("--civ", required=True, help="Civilization name")
    parser.add_argument("--db", default="aurelm.db", help="Database file path")
    parser.add_argument("--player", default=None, help="Player name")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM summarization (use extractive fallback)")
    parser.add_argument("--wiki-dir", default=None, help="Wiki directory (enables wiki generation)")
    parser.add_argument("--track-progress", action="store_true", help="Enable progress tracking for UI")
    args = parser.parse_args()

    run_pipeline(
        data_dir=args.data_dir,
        db_path=args.db,
        civ_name=args.civ,
        player_name=args.player,
        use_llm=not args.no_llm,
        wiki_dir=args.wiki_dir,
        track_progress=args.track_progress,
    )


if __name__ == "__main__":
    main()
