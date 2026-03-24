"""Pipeline orchestrator --chains all processing stages end-to-end.

Usage:
    python -m pipeline.runner --data-dir ../civjdr/Background --civ "Civilisation de la Confluence" --db aurelm.db
    python -m pipeline.runner --data-dir ../civjdr/Background --civ "Civilisation de la Confluence" --db aurelm.db --no-llm
"""

from __future__ import annotations

import argparse
import atexit
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
    insert_turn_stats,
    update_run_usage,
)
from .loader import load_directory
from .ingestion import fetch_unprocessed_messages
from .chunker import detect_turn_boundaries
from .classifier import classify_segments
from .summarizer import summarize_turn, AuthorContent, TECH_ERAS, FANTASY_LEVELS
from .entity_profiler import build_entity_profiles
from .alias_resolver import resolve_aliases
from .fact_extractor import FactExtractor
from .extraction_versions import get_version, list_versions, ExtractionVersion
from .llm_provider import (
    LLMProvider, OllamaProvider, create_provider,
    LLMConfig, load_llm_config, llm_config_from_cli,
)
from .subject_extractor import SubjectExtractor, build_turn_pairs
from .subject_helpers import load_open_subjects, insert_subject, apply_resolutions
from . import llm_stats


# Known GM author names --messages from these authors are GM posts
GM_AUTHORS = {"Arthur Ignatus", "arthur ignatus"}

CHANNEL_ID = "file-import"


def run_pipeline(
    data_dir: str | None = None,
    db_path: str = "aurelm.db",
    civ_name: str = "",
    player_name: str | None = None,
    use_llm: bool = True,
    wiki_dir: str | None = None,
    track_progress: bool = False,
    extraction_version: str = "v22.2.2-pastlevel",
    model: str = "qwen3:14b",
    provider: LLMProvider | None = None,
    llm_config: LLMConfig | None = None,
    # Bot mode: pass pre-fetched messages + civ_id to skip steps 1-4
    messages: list | None = None,
    civ_id: int | None = None,
    channel_id: str | None = None,
) -> dict:
    """Run the full pipeline: load -> chunk -> classify -> NER -> summarize -> persist.

    Two modes:
    - CLI mode: pass data_dir + civ_name. Steps 1-4 load files and register civ.
    - Bot mode: pass messages + civ_id + channel_id. Steps 1-4 are skipped.

    Returns a stats dict with counts of processed items.
    """
    _entity_cache.clear()
    llm_stats.reset()

    # If llm_config provided, it drives model selection per stage
    if llm_config:
        model = llm_config.default_model
        provider = provider or create_provider(llm_config.provider_name)

    global _active_model
    _active_model = model

    # Create provider if not passed explicitly (default: Ollama local)
    llm_provider = provider or OllamaProvider()

    version = get_version(extraction_version)
    print(f"[*] Extraction version: {version.name} -- {version.description}")
    if llm_config and llm_config.stage_models:
        print(f"[*] LLM config: {llm_config.summary()}")
    else:
        print(f"[*] Model: {model} (provider: {llm_provider.name})")

    if use_llm and llm_provider.name == "ollama":
        _register_unload_atexit()

    stats = {
        "messages_loaded": 0,
        "turns_created": 0,
        "entities_extracted": 0,
        "segments_created": 0,
    }

    bot_mode = messages is not None
    _channel_id = channel_id or CHANNEL_ID

    if not bot_mode:
        # CLI mode: steps 1-4 load from files
        # Step 1: Init DB
        print("[1/10] Initializing database...")
        init_db(db_path)
        run_migrations(db_path)

        # Step 2: Register civilization
        print(f"[2/10] Registering civilization: {civ_name}")
        civ_id = register_civilization(db_path, civ_name, player_name=player_name)

        # Step 3: Load markdown files
        assert data_dir is not None, "data_dir required in CLI mode"
        print(f"[3/10] Loading markdown files from {data_dir}...")
        msg_count = load_directory(data_dir, db_path, channel_id=_channel_id)
        stats["messages_loaded"] = msg_count
        print(f"       -> {msg_count} messages in database")

        # Step 4: Fetch unprocessed messages
        print("[4/10] Fetching unprocessed messages...")
        messages = fetch_unprocessed_messages(db_path, _channel_id)
        print(f"       ->{len(messages)} unprocessed messages")
    else:
        # Bot mode: messages + civ_id already provided
        print(f"[1-4/10] Bot mode: {len(messages)} messages, civ_id={civ_id}")
        stats["messages_loaded"] = len(messages)

    if not messages:
        print("       No new messages to process.")
        return stats

    # Step 5: Detect turn boundaries
    print("[5/10] Detecting turn boundaries...")
    gm_author_id = _find_gm_author_id(messages)
    all_chunks = detect_turn_boundaries(messages, gm_author_id)
    # Only process GM turns — player-only chunks (PJ responses, synthetic placeholders)
    # are not lore sources and must not become turn records.
    chunks = [c for c in all_chunks if c.is_gm_post]
    print(f"       ->{len(chunks)} turns detected")

    # Step 6: Process each turn
    print("[6/10] Processing turns (classify -> extract facts -> summarize)...")
    # Per-stage models: each LLM call can use a different model.
    # Config priority: llm_config stage override > CLI --model fallback.
    extraction_model  = llm_config.get_model("extraction")  if llm_config else model
    focus_model       = llm_config.get_model("focus")       if llm_config else None
    validation_model  = llm_config.get_model("validation")  if llm_config else None
    summarization_model = llm_config.get_model("summarization") if llm_config else model
    profiling_model   = llm_config.get_model("profiling")   if llm_config else model
    aliases_model     = llm_config.get_model("aliases")     if llm_config else model
    subjects_model    = llm_config.get_model("subjects")    if llm_config else model
    fact_extractor = FactExtractor(
        model=extraction_model, version=version, provider=llm_provider,
        focus_model=focus_model, validate_model=validation_model,
    ) if use_llm else None

    conn = get_connection(db_path)
    run_id = _start_pipeline_run(
        conn,
        extraction_version=extraction_version,
        llm_model=model,
        llm_provider=llm_provider.name if hasattr(llm_provider, 'name') else str(llm_provider),
    )

    # Build entity lookup from DB before the loop — starts empty for a fresh run,
    # populated from previous turns on incremental runs.
    # Rebuilt every 5 turns after periodic dedup so hints stay fresh and canonical.
    entity_lookup = _build_civ_entity_lookup(conn, civ_id)

    # Register prompt logging callback on the LLM provider.
    # Every generate()/chat() call will persist its prompt+response to pipeline_llm_calls.
    def _prompt_log_callback(log_run_id, log_turn_id, stage, model, system, prompt, response):
        try:
            conn.execute(
                """INSERT INTO pipeline_llm_calls
                   (run_id, turn_id, stage, model, system_prompt, user_prompt, response)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (log_run_id, log_turn_id, stage, model, system, prompt, response),
            )
            conn.commit()
        except Exception:
            pass  # never let logging break the pipeline

    if use_llm:
        llm_provider.set_prompt_logger(_prompt_log_callback)
        llm_provider.set_call_context(run_id, None)  # turn_id updated per-turn below

    # Per-turn extraction stats for final logging (MJ turns only — PJ has no entity extraction).
    # Each entry: {turn_number, text_chars, sys_prompt_chars, chunks, raw, after_dedup, final,
    #              usage_before, usage_after}
    _mj_turn_logs: list[dict] = []

    try:
        turn_number = _get_next_turn_number(conn, civ_id)
        total_turns = len(chunks)

        # Maps 1-indexed sequential GM position -> DB turn_id.
        # Used after the loop to link PJ (player) segments to their GM turn.
        # Index matches build_turn_pairs() sequential numbering.
        gm_seq_to_turn_id: dict[int, int] = {}

        # Tech/fantasy context carried forward turn by turn.
        # Seeded from the last processed turn in DB (for incremental runs),
        # or defaults to neolithique/realiste for a fresh run.
        prev_tech_era, prev_fantasy_level = _get_last_turn_context(conn, civ_id)

        # LLM call counter for progress tracking.
        # Estimate: ~4 calls per GM chunk (extraction×3 + validation).
        # Actual count may differ (optional calls skipped), but close enough for progress bar.
        _llm_calls_done = 0
        _estimated_calls_per_turn = 4  # facts+entities, entities-only, focused, validate

        def _on_llm_call(stage_name: str):
            nonlocal _llm_calls_done
            _llm_calls_done += 1
            if track_progress:
                update_progress(
                    conn, run_id, "pipeline", civ_id, civ_name,
                    i + 1, total_turns, "turn", "running",
                    stage_name=stage_name,
                    llm_calls_done=_llm_calls_done,
                    llm_calls_total=total_turns * _estimated_calls_per_turn,
                    turn_number=turn_number,
                )

        for i, chunk in enumerate(chunks):
            turn_text = "\n\n".join(m.content for m in chunk.messages)
            raw_ids = json.dumps([m.id for m in chunk.messages])
            raw_content = "\n\n".join(m.content for m in chunk.messages)

            # Create turn record
            cursor = conn.execute(
                """INSERT INTO turn_turns (civ_id, turn_number, raw_message_ids, turn_type)
                   VALUES (?, ?, ?, ?)""",
                (civ_id, turn_number, raw_ids, chunk.turn_type),
            )
            turn_id = cursor.lastrowid
            # Update prompt logger context so all LLM calls for this turn are tagged correctly
            if use_llm:
                llm_provider.set_call_context(run_id, turn_id)
            gm_seq_to_turn_id[i + 1] = turn_id  # 1-indexed to match build_turn_pairs
            stats["turns_created"] += 1

            # Classify segments
            segments = classify_segments(turn_text)

            # Extract structured facts (snapshot usage before/after for per-turn cost delta)
            structured_facts = None
            if fact_extractor:
                segment_dicts = [
                    {"segment_type": seg.segment_type.value, "content": seg.text}
                    for seg in segments
                ]
                usage_before = llm_provider.get_usage_snapshot()
                structured_facts = fact_extractor.extract_facts(
                    segment_dicts, raw_content,
                    entity_lookup=entity_lookup,
                    validation_model=validation_model,
                    prev_tech_era=prev_tech_era,
                    prev_fantasy_level=prev_fantasy_level,
                    on_llm_call=_on_llm_call if track_progress else None,
                )
                usage_after = llm_provider.get_usage_snapshot()

            # Insert segments
            for seg_order, seg in enumerate(segments):
                conn.execute(
                    """INSERT INTO turn_segments (turn_id, segment_order, segment_type, content)
                       VALUES (?, ?, ?, ?)""",
                    (turn_id, seg_order, seg.segment_type.value, seg.text),
                )
                stats["segments_created"] += 1

            # Collect per-turn extraction stats for logging
            if fact_extractor:
                exs = fact_extractor.last_stats
                turn_cost = (
                    usage_after.get("total_cost", 0) - usage_before.get("total_cost", 0)
                )
                turn_tokens = (
                    usage_after.get("total_tokens", 0) - usage_before.get("total_tokens", 0)
                )
                _mj_turn_logs.append({
                    "turn_number": turn_number,
                    "text_chars": exs.get("text_chars", len(turn_text)),
                    "sys_prompt_chars": exs.get("sys_prompt_chars", 0),
                    "chunks": exs.get("chunks", 1),
                    "raw": exs.get("raw", 0),
                    "after_dedup": exs.get("after_dedup", 0),
                    "final": exs.get("final", 0),
                    "cost": turn_cost,
                    "tokens": turn_tokens,
                })
                # Persist GM turn stats to DB
                insert_turn_stats(
                    conn, run_id, turn_id, "gm",
                    text_chars=exs.get("text_chars", len(turn_text)),
                    sys_prompt_chars=exs.get("sys_prompt_chars", 0),
                    chunks=exs.get("chunks", 1),
                    raw_entities=exs.get("raw", 0),
                    after_dedup=exs.get("after_dedup", 0),
                    final_entities=exs.get("final", 0),
                    est_tokens=turn_tokens,
                    est_cost_usd=turn_cost,
                )
                # Per-turn line: turn# | text size | chunks | funnel | density | cost
                txt_k = exs.get("text_chars", len(turn_text)) / 1000
                final = exs.get("final", 0)
                density = (final / txt_k) if txt_k > 0 else 0
                cost_str = f"${turn_cost:.4f}" if turn_cost > 0 else f"~{turn_tokens}tok"
                print(
                    f"       T{turn_number:02d} [GM] "
                    f"{txt_k:.1f}K chr | {exs.get('chunks',1)} chks | "
                    f"raw:{exs.get('raw',0)} dd:{exs.get('after_dedup',0)} fin:{final} | "
                    f"{density:.1f}/K | {cost_str}"
                )

            # Extract entities from LLM results — tagged as GM source
            if structured_facts and structured_facts.entities:
                for ent in structured_facts.entities:
                    entity_id = _upsert_entity(conn, ent.text, ent.label, civ_id, turn_id)
                    conn.execute(
                        """INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context, source)
                           VALUES (?, ?, ?, ?, 'gm')""",
                        (entity_id, turn_id, ent.text, ent.context),
                    )
                    stats["entities_extracted"] += 1

            # Summarize -- multi-call: 1 LLM call per author
            author_contents = _split_by_author(chunk.messages, gm_author_id)
            # Summarize + tag in a single GM LLM call (merged prompt).
            # prev_tech_era/prev_fantasy_level are carried forward turn by turn
            # so the LLM can reason about progression from the previous turn.
            summary = summarize_turn(
                turn_text, model=summarization_model, use_llm=use_llm,
                civ_name=civ_name, player_name=player_name,
                author_contents=author_contents if use_llm else None,
                provider=llm_provider,
                prev_tech_era=prev_tech_era,
                prev_fantasy_level=prev_fantasy_level,
            )

            # Persist summary + structured facts + tags (all from summary object)
            update_fields = {
                "summary": summary.short_summary,
                "detailed_summary": summary.detailed_summary,
                "key_events": json.dumps(summary.key_events, ensure_ascii=False) if summary.key_events else None,
                "choices_made": json.dumps(summary.choices_made, ensure_ascii=False) if summary.choices_made else None,
                "processed_at": datetime.now().isoformat(),
                "thematic_tags": json.dumps(summary.thematic_tags, ensure_ascii=False),
                "tech_era": summary.tech_era,
                "tech_era_reasoning": summary.tech_era_reasoning,
                "fantasy_level": summary.fantasy_level,
                "fantasy_level_reasoning": summary.fantasy_level_reasoning,
            }

            if structured_facts:
                update_fields["media_links"] = json.dumps(structured_facts.media_links, ensure_ascii=False)
                update_fields["technologies"] = json.dumps(structured_facts.technologies, ensure_ascii=False)
                update_fields["resources"] = json.dumps(structured_facts.resources, ensure_ascii=False)
                update_fields["beliefs"] = json.dumps(structured_facts.beliefs, ensure_ascii=False)
                update_fields["geography"] = json.dumps(structured_facts.geography, ensure_ascii=False)
                update_fields["choices_proposed"] = json.dumps(structured_facts.choices_proposed, ensure_ascii=False)

            # Read GM-locked fields — skip them so GM edits are preserved
            gm_row = conn.execute(
                "SELECT gm_fields FROM turn_turns WHERE id = ?", (turn_id,)
            ).fetchone()
            gm_fields: set = set()
            if gm_row and gm_row[0]:
                try:
                    gm_fields = set(json.loads(gm_row[0]))
                except (json.JSONDecodeError, TypeError):
                    pass

            # Remove pipeline fields that the GM has locked
            for locked in gm_fields & {"summary", "thematic_tags"}:
                update_fields.pop(locked, None)

            # Build dynamic SET clause — only update non-locked fields
            set_clauses = []
            values = []
            # Always-updated fields (not user-editable, never locked)
            always_update = [
                "detailed_summary", "key_events", "choices_made", "processed_at",
                "tech_era", "tech_era_reasoning", "fantasy_level", "fantasy_level_reasoning",
            ]
            for col in always_update:
                set_clauses.append(f"{col} = ?")
                values.append(update_fields.get(col))
            # Conditionally-updated fields (skipped if locked)
            for col in ["summary", "thematic_tags"]:
                if col in update_fields:
                    set_clauses.append(f"{col} = ?")
                    values.append(update_fields[col])
            # Structured facts (only present when available)
            for col in ["media_links", "technologies", "resources", "beliefs", "geography", "choices_proposed"]:
                if col in update_fields:
                    set_clauses.append(f"{col} = ?")
                    values.append(update_fields[col])
            values.append(turn_id)
            conn.execute(
                f"UPDATE turn_turns SET {', '.join(set_clauses)} WHERE id = ?",
                values,
            )

            # Carry forward context for the next turn
            prev_tech_era = summary.tech_era
            prev_fantasy_level = summary.fantasy_level

            # Detect foreign-civ mentions — scan entity_mentions for civilization-type
            # entities that don't belong to the current civ, fuzzy-match to civ_civilizations,
            # and record a civ_mention for the relation profiler to synthesize later.
            _detect_civ_mentions(conn, civ_id, turn_id, summary.short_summary or "")

            # Mark turn as processed
            mark_turn_processed(conn, turn_id, run_id)

            # Update progress tracking
            if track_progress:
                update_progress(
                    conn, run_id, "pipeline", civ_id, civ_name,
                    i + 1, total_turns, "turn", "running"
                )

            turn_number += 1

            # Every 5 turns: dedup entities by normalized name, then rebuild lookup.
            # Keeps entity_lookup clean and canonical so subsequent turns get accurate
            # hints injection (no stale duplicates like "sans-ciel" vs "sans-ciels").
            if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                merged = _periodic_entity_dedup(conn, civ_id)
                entity_lookup = _build_civ_entity_lookup(conn, civ_id)
                merge_note = f", {merged} merged" if merged else ""
                print(
                    f"       -> Processed {i + 1}/{len(chunks)} GM turns"
                    f" | lookup: {len(entity_lookup)} entries{merge_note}"
                )

        # Mark pipeline phase as completed
        if track_progress and total_turns > 0:
            update_progress(
                conn, run_id, "pipeline", civ_id, civ_name,
                total_turns, total_turns, "turn", "completed"
            )

        # Insert PJ (player) segments + collect PJ text stats for logging
        pj_turn_logs: list[dict] = []
        if gm_seq_to_turn_id:
            pj_count, pj_turn_logs = _insert_pj_segments(
                conn, all_chunks, gm_seq_to_turn_id, run_id,
                fact_extractor=fact_extractor,
                entity_lookup=entity_lookup,
                civ_id=civ_id,
                on_llm_call=_on_llm_call if track_progress else None,
            )
            if pj_count:
                total_pj_ents = sum(p.get("pj_entities", 0) for p in pj_turn_logs)
                print(
                    f"       -> {pj_count} PJ segments inserted"
                    + (f" | {total_pj_ents} PJ entities extracted" if total_pj_ents else "")
                )
                for pj in pj_turn_logs:
                    ent_note = f" | {pj['pj_entities']} ents" if pj.get("pj_entities") else ""
                    print(
                        f"       T{pj['turn_number']:02d} [PJ] "
                        f"{pj['text_chars']/1000:.1f}K chr | {pj['segments']} segs{ent_note}"
                    )

        # Print extraction summary: MJ vs PJ side-by-side
        if _mj_turn_logs:
            _print_extraction_summary(_mj_turn_logs, pj_turn_logs)

        conn.commit()
        _complete_pipeline_run(conn, run_id, stats)

    except Exception as e:
        conn.rollback()
        _fail_pipeline_run(conn, run_id, str(e))
        raise
    finally:
        conn.close()

    # Step 6.5: Turn preanalysis (novelty detection + player strategy)
    print("[6.5/10] Turn preanalysis (novelty + player strategy)...")
    from .turn_preanalysis import run_preanalysis
    preanalysis_stats = run_preanalysis(
        db_path,
        model=llm_config.get_model("preanalysis") if llm_config else model,
        provider=llm_provider if use_llm else None,
        civ_id=civ_id,
        run_id=run_id,
        use_llm=use_llm,
    )
    if preanalysis_stats["new_entities_found"]:
        print(f"       -> {preanalysis_stats['new_entities_found']} new entities across {preanalysis_stats['turns_analyzed']} turns")
    if preanalysis_stats["strategies_analyzed"]:
        print(f"       -> {preanalysis_stats['strategies_analyzed']} player strategies analyzed")

    # Step 7: Subject extraction (MJ choices + PJ initiatives)
    if use_llm:
        print("[7/10] Extracting subjects (MJ choices + PJ initiatives)...")
        _run_subject_extraction(
            db_path, civ_id, all_chunks, gm_author_id,
            subjects_model, llm_provider,
        )

    # Step 8: Entity profiling (LLM-based)
    if use_llm:
        print("[8/10] Building entity profiles (1 LLM call per entity)...")
        profiles = build_entity_profiles(
            db_path,
            model=profiling_model,
            use_llm=True,
            incremental=True,
            run_id=run_id,
            track_progress=track_progress,
            provider=llm_provider,
        )
        stats["entities_profiled"] = len([p for p in profiles if p.description])

        # Step 8.5: Civ relation profiling — synthesize inter-civ opinions from civ_mentions
        print("[8.5/10] Profiling inter-civ relations...")
        from .civ_relation_profiler import build_civ_relations
        rel_stats = build_civ_relations(
            db_path,
            source_civ_id=civ_id,
            model=profiling_model,
            provider=llm_provider,
            use_llm=use_llm,
        )
        if rel_stats["pairs_found"]:
            print(
                f"       -> {rel_stats['relations_built']} relations profiled"
                f" ({rel_stats['pairs_found']} pairs found)"
            )
        else:
            print("       -> No foreign-civ mentions detected")

        # Step 9: Alias resolution
        # Prompt version + score threshold can be set per-stage in llm_config:
        # "aliases": {"prompt_version": "v5-score-pct", "score_threshold": 0.7}
        aliases_confirm_version = (
            llm_config.get_prompt_version("aliases") if llm_config else None
        )
        aliases_score_threshold = (
            llm_config.get_score_threshold("aliases") if llm_config else 0.7
        )
        print("[9/10] Resolving entity aliases...")
        alias_stats = resolve_aliases(
            db_path, profiles, model=aliases_model, use_llm=True,
            provider=llm_provider,
            confirm_version=aliases_confirm_version or "v2-qwen3",
            score_threshold=aliases_score_threshold,
        )
        stats["alias_candidates"] = alias_stats.get("candidates_found", 0)
        stats["aliases_confirmed"] = alias_stats.get("aliases_confirmed", 0)
    else:
        print("[7/10] Skipping subject extraction (--no-llm)")
        print("[8/10] Skipping entity profiling (--no-llm)")
        # Still register pairs with unknown opinion so the GUI shows known contacts
        print("[8.5/10] Registering civ contacts (--no-llm, opinion=unknown)...")
        from .civ_relation_profiler import build_civ_relations
        build_civ_relations(db_path, source_civ_id=civ_id, use_llm=False)
        print("[9/10] Skipping alias resolution (--no-llm)")

    # Step 10: Wiki generation (optional)
    if wiki_dir:
        print("[10/10] Generating wiki...")

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
        print("[10/10] Skipping wiki generation (use --wiki-dir to enable)")

    # Unload models to free VRAM (no-op for cloud providers)
    if use_llm:
        # Unload all distinct models that were used across stages
        used_models = {extraction_model, summarization_model, profiling_model, aliases_model, subjects_model}
        if validation_model:
            used_models.add(validation_model)
        for m in used_models:
            llm_provider.unload(m)

    # Capture provider usage (tokens + cost) for final summary + persist to DB
    usage = llm_provider.get_usage_snapshot()
    stats["provider_usage"] = usage
    if usage.get("total_tokens", 0) > 0 or usage.get("total_cost", 0) > 0:
        conn2 = get_connection(db_path)
        try:
            update_run_usage(conn2, run_id,
                             usage.get("total_tokens", 0),
                             usage.get("total_cost", 0.0))
            conn2.commit()
        finally:
            conn2.close()

    # Final summary
    print("[DONE] Pipeline complete!")
    _print_stats(stats)
    return stats


def _insert_pj_segments(
    conn,
    all_chunks: list,
    gm_seq_to_turn_id: dict[int, int],
    run_id: int | None = None,
    fact_extractor=None,
    entity_lookup: dict | None = None,
    civ_id: int | None = None,
    on_llm_call=None,
) -> tuple[int, list[dict]]:
    """Insert player (PJ) segments into the corresponding GM turn, and optionally
    extract named entities from PJ text.

    Iterates all_chunks in order, counting GM chunks to stay in sync with the
    1-indexed gm_seq_to_turn_id mapping built during the GM loop.
    Skips synthetic placeholders (content < 50 chars) and turns where
    PJ segments already exist (idempotent).

    When fact_extractor + civ_id are provided, also runs entity extraction on
    PJ text — entity_only + focused, no validate (PJ lore is trusted canon).
    Entities introduced by the player (Morsure-des-Ancêtres, Paniers immergés...)
    are inserted with mentions linked to the corresponding GM turn.

    Returns (total_segments_inserted, per_turn_stats_list).
    per_turn_stats_list entries: {turn_number, text_chars, segments, pj_entities}
    """
    gm_seq = 0
    total_inserted = 0
    turn_logs: list[dict] = []

    for chunk in all_chunks:
        if chunk.is_gm_post:
            gm_seq += 1
            continue

        # Non-GM chunk — attach to the preceding GM turn
        turn_id = gm_seq_to_turn_id.get(gm_seq)
        if turn_id is None:
            # No corresponding GM turn in this batch (e.g. orphan PJ chunk)
            continue

        # Skip synthetic __player__ placeholders (content is just "[Tour N]")
        pj_text = "\n\n".join(m.content for m in chunk.messages)
        if len(pj_text.strip()) < 50:
            continue

        # Idempotency: skip if PJ segments already exist for this turn
        existing = conn.execute(
            "SELECT COUNT(*) FROM turn_segments WHERE turn_id = ? AND source = 'pj'",
            (turn_id,),
        ).fetchone()[0]
        if existing > 0:
            # Already processed — skip segments AND entity extraction (idempotent)
            turn_logs.append({
                "turn_number": gm_seq,
                "text_chars": len(pj_text),
                "segments": 0,
                "pj_entities": 0,
            })
            continue

        # Find the current max segment_order so PJ segments come after GM ones
        max_order_row = conn.execute(
            "SELECT MAX(segment_order) FROM turn_segments WHERE turn_id = ?",
            (turn_id,),
        ).fetchone()
        base_order = (max_order_row[0] if max_order_row[0] is not None else -1) + 1

        pj_segments = classify_segments(pj_text)
        for seg_idx, seg in enumerate(pj_segments):
            conn.execute(
                """INSERT OR IGNORE INTO turn_segments
                   (turn_id, segment_order, segment_type, content, source)
                   VALUES (?, ?, ?, ?, 'pj')""",
                (turn_id, base_order + seg_idx, seg.segment_type.value, seg.text),
            )
            total_inserted += 1

        # PJ entity extraction: capture named entities introduced by the player.
        # Examples: Morsure-des-Ancêtres (T06 PJ), Paniers immergés (T05 PJ).
        # No validate — PJ text is trusted canon lore, genericity filter not needed.
        pj_entity_count = 0
        if fact_extractor is not None and civ_id is not None:
            pj_entities = fact_extractor.extract_pj_entities(
                pj_text, entity_lookup or {}, on_llm_call=on_llm_call)
            for ent in pj_entities:
                entity_id = _upsert_entity(conn, ent.text, ent.label, civ_id, turn_id)
                conn.execute(
                    """INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context, source)
                       VALUES (?, ?, ?, ?, 'pj')""",
                    (entity_id, turn_id, ent.text, ent.context),
                )
            pj_entity_count = len(pj_entities)

        seg_count = len(pj_segments)
        turn_logs.append({
            "turn_number": gm_seq,
            "text_chars": len(pj_text),
            "segments": seg_count,
            "pj_entities": pj_entity_count,
        })
        # Persist PJ stats to DB
        if run_id is not None:
            insert_turn_stats(
                conn, run_id, turn_id, "pj",
                text_chars=len(pj_text),
                sys_prompt_chars=0,
                chunks=0,
                raw_entities=0,
                after_dedup=0,
                final_entities=0,
                est_tokens=0,
                est_cost_usd=0.0,
            )

    return total_inserted, turn_logs


def _run_subject_extraction(
    db_path: str,
    civ_id: int,
    all_chunks: list,
    gm_author_id: str,
    model: str,
    provider: LLMProvider,
) -> dict:
    """Run subject extraction stage: MJ choices, PJ initiatives, resolutions.

    Processes turns in chronological order. For each turn:
    1. Extract MJ subjects (choices/questions requiring player response)
    2. Detect MJ consequences for open PJ initiatives
    3. Store new MJ subjects
    4. If PJ text exists: match resolutions + extract PJ initiatives
    5. Refresh open subjects for next turn

    Args:
        db_path: Path to SQLite database
        civ_id: Civilization ID
        all_chunks: All TurnChunk objects (GM + PJ)
        gm_author_id: Author ID of the GM
        model: LLM model for subject extraction
        provider: LLM provider instance

    Returns:
        Stats dict with subject/resolution counts
    """
    extractor = SubjectExtractor(provider=provider, model=model)
    turn_pairs = build_turn_pairs(all_chunks, gm_author_id)

    conn = get_connection(db_path)
    stats = {"subjects_extracted": 0, "resolutions_applied": 0, "initiatives_extracted": 0}

    try:
        # Get turn_id mapping: turn_number -> turn_id from DB
        turn_rows = conn.execute(
            """SELECT id, turn_number FROM turn_turns
               WHERE civ_id = ? ORDER BY turn_number""",
            (civ_id,),
        ).fetchall()
        turn_number_to_id = {row["turn_number"]: row["id"] for row in turn_rows}

        for turn_number in sorted(turn_pairs.keys()):
            pair = turn_pairs[turn_number]
            gm_text = pair["gm_text"]
            pj_text = pair["pj_text"]
            turn_id = turn_number_to_id.get(turn_number)

            if not turn_id:
                continue

            # Skip if already processed (idempotency check)
            existing = conn.execute(
                "SELECT COUNT(*) FROM subject_subjects WHERE source_turn_id = ?",
                (turn_id,),
            ).fetchone()[0]
            if existing > 0:
                continue

            # 1. Extract MJ subjects (choices/questions)
            mj_subjects = extractor.extract_mj_subjects(gm_text, turn_number)

            # 2. Detect MJ consequences for open PJ initiatives
            open_subjects = load_open_subjects(conn, civ_id)
            mj_consequences = extractor.detect_mj_consequences(
                gm_text, open_subjects, turn_number
            )

            # Apply MJ consequences (resolves PJ initiatives)
            if mj_consequences:
                resolved = apply_resolutions(
                    conn,
                    [
                        {
                            "subject_id": r.subject_id,
                            "resolution_text": r.resolution_text,
                            "confidence": r.confidence,
                            "source_quote": r.source_quote,
                        }
                        for r in mj_consequences
                    ],
                    turn_id,
                )
                stats["resolutions_applied"] += resolved

            # 3. Store new MJ subjects
            for subj in mj_subjects:
                subj_dict = {
                    "direction": subj.direction,
                    "title": subj.title,
                    "description": subj.description,
                    "category": subj.category,
                    "source_quote": subj.source_quote,
                    "tags": subj.tags,
                    "options": [
                        {
                            "number": opt.number,
                            "label": opt.label,
                            "description": opt.description,
                            "is_libre": opt.is_libre,
                        }
                        for opt in subj.options
                    ],
                }
                insert_subject(conn, subj_dict, civ_id, turn_id)
                stats["subjects_extracted"] += 1

            # 4. If PJ text exists: match resolutions + extract initiatives
            if pj_text.strip():
                # Refresh open subjects (includes newly inserted MJ subjects)
                open_subjects = load_open_subjects(conn, civ_id)

                # Match PJ responses to open MJ subjects
                resolutions = extractor.match_resolutions(
                    pj_text, open_subjects, turn_number
                )
                if resolutions:
                    resolved = apply_resolutions(
                        conn,
                        [
                            {
                                "subject_id": r.subject_id,
                                "resolution_text": r.resolution_text,
                                "chosen_option_label": r.chosen_option_label,
                                "is_libre": r.is_libre,
                                "confidence": r.confidence,
                                "source_quote": r.source_quote,
                            }
                            for r in resolutions
                        ],
                        turn_id,
                    )
                    stats["resolutions_applied"] += resolved

                # Extract PJ initiatives
                pj_initiatives = extractor.extract_pj_subjects(pj_text, turn_number)
                for subj in pj_initiatives:
                    subj_dict = {
                        "direction": subj.direction,
                        "title": subj.title,
                        "description": subj.description,
                        "category": subj.category,
                        "source_quote": subj.source_quote,
                        "tags": subj.tags,
                        "options": [],
                    }
                    insert_subject(conn, subj_dict, civ_id, turn_id)
                    stats["initiatives_extracted"] += 1

            conn.commit()

            if turn_number % 5 == 0 or turn_number == max(turn_pairs.keys()):
                print(
                    f"       -> T{turn_number}: "
                    f"{stats['subjects_extracted']} subjects, "
                    f"{stats['resolutions_applied']} resolutions, "
                    f"{stats['initiatives_extracted']} initiatives"
                )

    except Exception as e:
        conn.rollback()
        print(f"Error in subject extraction: {e}")
        raise
    finally:
        conn.close()

    print(
        f"       -> Total: {stats['subjects_extracted']} subjects, "
        f"{stats['resolutions_applied']} resolutions, "
        f"{stats['initiatives_extracted']} initiatives"
    )
    return stats


_active_model: str = "llama3.1:8b"


def _unload_ollama_model() -> None:
    """Unload Ollama model to free VRAM and Windows pagefile reservation."""
    try:
        import ollama
        ollama.generate(model=_active_model, prompt="", keep_alive=0)
        print("  Ollama model unloaded from VRAM.")
    except Exception:
        pass  # Non-critical — Ollama may already be unloaded or not running


_atexit_registered = False


def _register_unload_atexit() -> None:
    """Register atexit handler at most once (guards against double module import)."""
    global _atexit_registered
    if not _atexit_registered:
        atexit.register(_unload_ollama_model)
        _atexit_registered = True


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
    """Find the GM's author_id from known GM author names.

    Uses prefix matching so "Arthur Ignatus (03/09/2024)" matches "Arthur Ignatus".
    Skips synthetic __player__ placeholders which have a fixed ID and no real content.
    """
    for msg in messages:
        name_lower = msg.author_name.lower()
        if any(name_lower.startswith(gm.lower()) for gm in GM_AUTHORS):
            return msg.author_id
    # Fallback: first non-synthetic message
    for msg in messages:
        if msg.author_name != "__player__":
            return msg.author_id
    return messages[0].author_id if messages else ""


def _get_next_turn_number(conn, civ_id: int) -> int:
    """Get the next available turn number for a civilization."""
    row = conn.execute(
        "SELECT COALESCE(MAX(turn_number), 0) + 1 FROM turn_turns WHERE civ_id = ?",
        (civ_id,),
    ).fetchone()
    return row[0]


def _get_last_turn_context(conn, civ_id: int) -> tuple[str, str]:
    """Retrieve tech_era and fantasy_level from the most recent processed turn.

    Used to seed the carry-forward context at the start of a run.
    Falls back to defaults (neolithique / realiste) if no prior turns exist.
    """
    row = conn.execute(
        """SELECT tech_era, fantasy_level FROM turn_turns
           WHERE civ_id = ? AND tech_era IS NOT NULL
           ORDER BY turn_number DESC LIMIT 1""",
        (civ_id,),
    ).fetchone()
    if row:
        return row[0] or "neolithique", row[1] or "realiste"
    return "neolithique", "realiste"


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

    # Expand ligatures (not decomposed by NFKD)
    text = name.replace("\u0153", "oe").replace("\u0152", "OE")  # œ/Œ
    text = text.replace("\u00e6", "ae").replace("\u00c6", "AE")  # æ/Æ

    # Strip accents
    nfkd = _ud.normalize("NFKD", text)
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
            """UPDATE entity_entities
               SET last_seen_turn = MAX(last_seen_turn, ?),
                   first_seen_turn = MIN(first_seen_turn, ?),
                   updated_at = ?
               WHERE id = ?""",
            (turn_id, turn_id, datetime.now().isoformat(), entity_id),
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
            now = datetime.now().isoformat()
            if _is_better_display_name(name, stored_name):
                conn.execute(
                    """UPDATE entity_entities
                       SET canonical_name = ?, last_seen_turn = MAX(last_seen_turn, ?),
                           first_seen_turn = MIN(first_seen_turn, ?), updated_at = ?
                       WHERE id = ?""",
                    (name, turn_id, turn_id, now, entity_id),
                )
                _entity_cache[cache_key] = (entity_id, name)
            else:
                conn.execute(
                    """UPDATE entity_entities
                       SET last_seen_turn = MAX(last_seen_turn, ?),
                           first_seen_turn = MIN(first_seen_turn, ?), updated_at = ?
                       WHERE id = ?""",
                    (turn_id, turn_id, now, entity_id),
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


def _start_pipeline_run(
    conn,
    extraction_version: str | None = None,
    llm_model: str | None = None,
    llm_provider: str | None = None,
) -> int:
    """Record the start of a pipeline run with metadata."""
    cursor = conn.execute(
        """INSERT INTO pipeline_runs (status, extraction_version, llm_model, llm_provider)
           VALUES ('running', ?, ?, ?)""",
        (extraction_version, llm_model, llm_provider),
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


def _print_extraction_summary(mj_logs: list[dict], pj_logs: list[dict]) -> None:
    """Print a per-source extraction summary table after stage [6/10].

    Shows: turns | total text | total entities | funnel (raw/dedup/final) |
           entity density (ent/1000 chars) | estimated cost.
    MJ rows have entity stats; PJ rows show text size only (no entity extraction).
    """
    def _sum(logs, key):
        return sum(r.get(key, 0) for r in logs)

    mj_chars = _sum(mj_logs, "text_chars")
    mj_raw   = _sum(mj_logs, "raw")
    mj_dd    = _sum(mj_logs, "after_dedup")
    mj_final = _sum(mj_logs, "final")
    mj_cost  = _sum(mj_logs, "cost")
    mj_tok   = _sum(mj_logs, "tokens")
    mj_k     = mj_chars / 1000 if mj_chars else 1
    mj_dens  = mj_final / mj_k

    pj_chars = _sum(pj_logs, "text_chars")
    pj_k     = pj_chars / 1000 if pj_chars else 1

    total_chars = mj_chars + pj_chars
    total_cost  = mj_cost  # PJ not extracted by LLM (subjects tracked separately)
    total_tok   = mj_tok

    cost_fmt = (lambda c, t: f"${c:.4f}" if c > 0 else f"~{t}tok")

    print()
    print("  Extraction Summary (stage 6)")
    print(f"  {'':4} {'turns':>5}  {'text':>7}  {'raw':>4} {'dd':>4} {'fin':>4}  {'dens':>6}  {'cost/tokens':>12}")
    print(f"  {'----':4} {'-----':>5}  {'-------':>7}  {'----':>4} {'----':>4} {'----':>4}  {'------':>6}  {'------------':>12}")
    print(
        f"  {'MJ':4} {len(mj_logs):>5}  {mj_chars/1000:>6.1f}K  "
        f"{mj_raw:>4} {mj_dd:>4} {mj_final:>4}  {mj_dens:>5.1f}/K  "
        f"{cost_fmt(mj_cost, mj_tok):>12}"
    )
    if pj_logs:
        print(
            f"  {'PJ':4} {len(pj_logs):>5}  {pj_chars/1000:>6.1f}K  "
            f"{'n/a':>4} {'n/a':>4} {'n/a':>4}  {'n/a':>6}  {'(subjects)':>12}"
        )
    print(
        f"  {'TOT':4} {len(mj_logs)+len(pj_logs):>5}  {total_chars/1000:>6.1f}K  "
        f"{mj_raw:>4} {mj_dd:>4} {mj_final:>4}  {mj_dens:>5.1f}/K  "
        f"{cost_fmt(total_cost, total_tok):>12}"
    )
    print()

    # Flag low-density turns (< 1.0 ent/K) for review
    low = [r for r in mj_logs if r["text_chars"] > 500 and
           (r["final"] / (r["text_chars"] / 1000)) < 1.0]
    if low:
        print(f"  [!] Low-density turns (<1.0/K): "
              + ", ".join(f"T{r['turn_number']:02d}({r['final']}ent/{r['text_chars']//100*100}c)"
                          for r in low))
        print()


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
        print(f"    entity extraction: {counts['entity_extraction']}")
        print(f"    focus extraction:  {counts['focused_extraction']}")
        print(f"    validation:        {counts['entity_validation']}")
        print(f"    subject extr.:     {counts['subject_extraction']}")
        print(f"    subject resolv.:   {counts['subject_resolution']}")
        print(f"    summarization:     {counts['summarization']}")
        print(f"    entity profiling:  {counts['entity_profiling']}")
        if counts['preanalysis']:
            print(f"    preanalysis:       {counts['preanalysis']}")
    # Show total cost if available (OpenRouter provider)
    if "provider_usage" in stats:
        usage = stats["provider_usage"]
        if usage.get("total_cost", 0) > 0:
            print(f"  Total cost:          ${usage['total_cost']:.4f}")
            print(f"  Total tokens:        {usage['total_tokens']:,}")
    print("=" * 40)


def _detect_civ_mentions(conn, source_civ_id: int, turn_id: int, context: str) -> None:
    """Detect foreign-civilization mentions in a turn and record them in civ_mentions.

    Scans entity_mentions for this turn, finds entities of type 'civilization'
    that don't belong to source_civ, then fuzzy-matches canonical_name →
    civ_civilizations to resolve the target civ ID.  Inserts OR IGNOREs into
    civ_mentions so re-runs are idempotent.

    Context stored per (turn, target_civ) pair is built from entity_mentions.context
    — the surrounding text at extraction time — rather than the full turn summary.
    This makes the profiler LLM work from specific passages rather than a generic
    summary that may not even mention the target civ by name.
    """
    # Fetch source civ name for self-exclusion below
    source_civ_row = conn.execute(
        "SELECT name FROM civ_civilizations WHERE id = ?", (source_civ_id,)
    ).fetchone()
    source_civ_name_lower = source_civ_row["name"].lower() if source_civ_row else ""

    # Find all civilization-type entities mentioned in this turn, with their
    # per-mention context snippets (surrounding text from the source segment).
    # Note: ALL entities extracted from a civ's turns carry that civ's civ_id,
    # even foreign civs — so we CANNOT filter by civ_id here. Self-exclusion
    # is done by comparing target_civ_id == source_civ_id after DB lookup.
    rows = conn.execute(
        """SELECT e.canonical_name, em.mention_text, em.context AS mention_ctx
           FROM entity_mentions em
           JOIN entity_entities e ON e.id = em.entity_id
           WHERE em.turn_id = ?
             AND e.entity_type = 'civilization'
             AND e.disabled = 0""",
        (turn_id,),
    ).fetchall()

    # Also fetch known aliases for all civs so we can validate mention_text below.
    alias_rows = conn.execute(
        "SELECT alias_name, civ_id FROM civ_aliases"
    ).fetchall()
    civ_alias_names: dict[str, int] = {
        r["alias_name"].lower(): r["civ_id"] for r in alias_rows
    }

    # Group mention snippets by canonical_name so we can build a rich context
    # per (turn, target_civ) even when the civ is mentioned multiple times.
    # Filter: only include a snippet when mention_text roughly matches the entity's
    # canonical name or a known alias — this excludes alias-merged entities whose
    # mention_text refers to a completely different concept (e.g. "Mériadoques"
    # merged into "Nanzagouet" would pollute the Nanzagouets relation context).
    from collections import defaultdict
    snippets_by_name: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        canonical = row["canonical_name"]
        mention = (row["mention_text"] or "").strip().lower()
        canonical_lower = canonical.lower()

        # Accept if mention_text contains part of canonical name or vice versa,
        # OR if mention_text matches a known civ alias.
        mention_matches = (
            canonical_lower in mention
            or mention in canonical_lower
            or mention in civ_alias_names
        )
        if not mention_matches:
            continue  # skip — different concept merged under this entity

        ctx_snippet = (row["mention_ctx"] or "").strip()
        if ctx_snippet:
            snippets_by_name[canonical].append(ctx_snippet)
        elif canonical not in snippets_by_name:
            snippets_by_name[canonical] = []  # ensure key exists

    for entity_name, snippets in snippets_by_name.items():
        # Try canonical name match first (exact, then partial)
        target = conn.execute(
            "SELECT id FROM civ_civilizations WHERE LOWER(name) = LOWER(?)",
            (entity_name,),
        ).fetchone()
        if target is None:
            target = conn.execute(
                """SELECT id FROM civ_civilizations
                   WHERE LOWER(name) LIKE '%' || LOWER(?) || '%'
                      OR LOWER(?) LIKE '%' || LOWER(name) || '%'
                   LIMIT 1""",
                (entity_name, entity_name),
            ).fetchone()

        # Fall back to GM-defined aliases (e.g. "Nanzagouet" → Nanzagouets)
        if target is None:
            target = conn.execute(
                """SELECT civ_id AS id FROM civ_aliases
                   WHERE LOWER(alias_name) = LOWER(?)""",
                (entity_name,),
            ).fetchone()

        if target is None:
            # No match in known civs or aliases → skip silently.
            # We never auto-create stubs: the LLM tags false positives as "civilization".
            # Use the UI resolver to map unrecognized names.
            continue

        target_civ_id = target["id"]
        if target_civ_id == source_civ_id:
            continue

        # Build specific context from mention snippets; fall back to turn summary
        # only if no snippets are available (older DB rows without em.context).
        if snippets:
            # Deduplicate and join snippets, cap at 500 chars
            seen: set[str] = set()
            unique = [s for s in snippets if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]
            specific_context: str | None = " | ".join(unique)[:500]
        else:
            specific_context = context[:500] if context else None

        conn.execute(
            """INSERT OR IGNORE INTO civ_mentions
                   (source_civ_id, target_civ_id, turn_id, context)
               VALUES (?, ?, ?, ?)""",
            (source_civ_id, target_civ_id, turn_id, specific_context),
        )


def _periodic_entity_dedup(conn, civ_id: int) -> int:
    """Merge duplicate entities with the same normalized name for a civ.

    Runs after every N turns during stage [6] to keep the entity table clean
    before it's used as context for the next batch of turns.

    Strategy: group active entities by _normalize_for_dedup(canonical_name).
    Keep the entity with the most mentions as primary; redirect all mentions,
    relations, aliases and subject references from secondary to primary.
    Returns the number of merges performed.
    """
    rows = conn.execute(
        "SELECT id, canonical_name FROM entity_entities WHERE civ_id = ? AND is_active = 1",
        (civ_id,),
    ).fetchall()

    # Group by normalized key
    groups: dict[str, list] = {}
    for row in rows:
        eid = row[0] if not hasattr(row, "keys") else row["id"]
        name = row[1] if not hasattr(row, "keys") else row["canonical_name"]
        key = _normalize_for_dedup(name)
        groups.setdefault(key, []).append((eid, name))

    merged = 0
    for key, entities in groups.items():
        if len(entities) < 2:
            continue

        # Pick primary: entity with most mentions, or lowest id as tiebreak
        mention_counts = {}
        for eid, _ in entities:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?", (eid,)
            ).fetchone()[0]
            mention_counts[eid] = cnt

        primary_id = max(entities, key=lambda e: (mention_counts[e[0]], -e[0]))[0]

        for eid, name in entities:
            if eid == primary_id:
                continue
            # Redirect mentions, relations, aliases, subjects to primary
            conn.execute(
                "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?",
                (primary_id, eid),
            )
            conn.execute(
                "UPDATE entity_relations SET source_entity_id = ? WHERE source_entity_id = ?",
                (primary_id, eid),
            )
            conn.execute(
                "UPDATE entity_relations SET target_entity_id = ? WHERE target_entity_id = ?",
                (primary_id, eid),
            )
            conn.execute(
                "UPDATE entity_aliases SET entity_id = ? WHERE entity_id = ?",
                (primary_id, eid),
            )
            # Deactivate secondary (soft delete to preserve history)
            conn.execute(
                "UPDATE entity_entities SET is_active = 0 WHERE id = ?", (eid,)
            )
            merged += 1

    if merged:
        conn.commit()

    return merged


def _build_civ_entity_lookup(conn, civ_id: int) -> dict:
    """Build {name_lower: {canonical_name, entity_type}} for known entities of a civ.

    Used by the pattern pass in FactExtractor to detect entity names in turn text.
    Includes both canonical names and aliases.
    """
    lookup: dict = {}
    rows = conn.execute(
        "SELECT canonical_name, entity_type FROM entity_entities WHERE civ_id = ? AND is_active = 1 AND disabled = 0",
        (civ_id,),
    ).fetchall()
    for r in rows:
        name = r["canonical_name"] if hasattr(r, "keys") else r[0]
        etype = r["entity_type"] if hasattr(r, "keys") else r[1]
        lookup[name.lower()] = {"canonical_name": name, "entity_type": etype}

    aliases = conn.execute(
        """SELECT a.alias, e.canonical_name, e.entity_type
           FROM entity_aliases a
           JOIN entity_entities e ON a.entity_id = e.id
           WHERE e.civ_id = ? AND e.is_active = 1""",
        (civ_id,),
    ).fetchall()
    for a in aliases:
        alias = a["alias"] if hasattr(a, "keys") else a[0]
        canonical = a["canonical_name"] if hasattr(a, "keys") else a[1]
        etype = a["entity_type"] if hasattr(a, "keys") else a[2]
        lookup[alias.lower()] = {"canonical_name": canonical, "entity_type": etype}

    return lookup


def reextract_facts_for_civ(db_path: str, civ_id: int, use_llm: bool = True, extraction_version: str = "v7-v4t0") -> int:
    """Re-run fact extraction on all existing turns for a civilization.

    Uses the hybrid LLM + pattern approach with the civ's entity lookup.
    Updates turn_turns in place (merges new facts with existing ones).

    Args:
        db_path: Path to SQLite database
        civ_id: Civilization ID to reprocess
        use_llm: Whether to call Ollama for LLM extraction (default True)

    Returns:
        Number of turns updated
    """
    conn = get_connection(db_path)
    conn.row_factory = __import__("sqlite3").Row

    # Build entity lookup for this civ (uses entities already in DB)
    entity_lookup = _build_civ_entity_lookup(conn, civ_id)
    print(f"  Entity lookup: {len(entity_lookup)} entries")

    version = get_version(extraction_version)
    fact_extractor = FactExtractor(version=version) if use_llm else FactExtractor.__new__(FactExtractor)
    if not use_llm:
        # Init a no-LLM extractor that only runs the pattern pass
        fact_extractor.ollama_base_url = ""
        fact_extractor.model = ""
        fact_extractor.client = None

    turns = conn.execute(
        "SELECT id, turn_number FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
        (civ_id,),
    ).fetchall()

    updated = 0
    for turn in turns:
        turn_id = turn["id"]
        turn_num = turn["turn_number"]

        # Rebuild segment dicts from DB
        segs = conn.execute(
            "SELECT segment_type, content FROM turn_segments WHERE turn_id = ? ORDER BY segment_order",
            (turn_id,),
        ).fetchall()
        if not segs:
            continue

        segment_dicts = [
            {"segment_type": s["segment_type"], "content": s["content"]}
            for s in segs
        ]

        # Run hybrid extraction
        if use_llm:
            facts = fact_extractor.extract_facts(segment_dicts, "", entity_lookup)
        else:
            # Pattern-only: bypass LLM
            relevant_text = "\n\n".join(
                s["content"] for s in segs
                if s["segment_type"] in ("narrative", "consequence", "description")
            )
            pattern_facts = fact_extractor._pattern_extract_facts(relevant_text, entity_lookup)
            # Merge with existing DB values
            existing = conn.execute(
                "SELECT technologies, resources, beliefs, geography FROM turn_turns WHERE id = ?",
                (turn_id,),
            ).fetchone()

            def _load(col):
                val = existing[col]
                try:
                    return json.loads(val) if val else []
                except Exception:
                    return []

            def _merge(existing_list, new_list):
                seen = set()
                result = []
                for item in existing_list + new_list:
                    key = item.strip().lower()
                    if key and key not in seen:
                        seen.add(key)
                        result.append(item.strip())
                return result

            facts_dict = {
                "technologies": _merge(_load("technologies"), pattern_facts.get("technologies", [])),
                "resources":    _merge(_load("resources"),    pattern_facts.get("resources", [])),
                "beliefs":      _merge(_load("beliefs"),      pattern_facts.get("beliefs", [])),
                "geography":    _merge(_load("geography"),    pattern_facts.get("geography", [])),
            }
            conn.execute(
                """UPDATE turn_turns SET technologies=?, resources=?, beliefs=?, geography=?
                   WHERE id=?""",
                (
                    json.dumps(facts_dict["technologies"], ensure_ascii=False),
                    json.dumps(facts_dict["resources"],    ensure_ascii=False),
                    json.dumps(facts_dict["beliefs"],      ensure_ascii=False),
                    json.dumps(facts_dict["geography"],    ensure_ascii=False),
                    turn_id,
                ),
            )
            conn.commit()
            updated += 1
            print(f"  Turn {turn_num}: +{len(pattern_facts.get('beliefs', []))} beliefs, "
                  f"+{len(pattern_facts.get('technologies', []))} techs")
            continue

        # LLM path: full update
        conn.execute(
            """UPDATE turn_turns SET technologies=?, resources=?, beliefs=?, geography=?
               WHERE id=?""",
            (
                json.dumps(facts.technologies, ensure_ascii=False),
                json.dumps(facts.resources,    ensure_ascii=False),
                json.dumps(facts.beliefs,      ensure_ascii=False),
                json.dumps(facts.geography,    ensure_ascii=False),
                turn_id,
            ),
        )
        conn.commit()
        updated += 1
        print(f"  Turn {turn_num}: {len(facts.beliefs)} beliefs, {len(facts.technologies)} techs")

    if use_llm:
        fact_extractor.close()

    print(f"  Updated {updated} turns.")
    return updated


def run_pipeline_for_channels(
    db_path: str,
    use_llm: bool = True,
    wiki_dir: str | None = None,
    gm_authors: set[str] | None = None,
    track_progress: bool = True,
    extraction_version: str = "v22.2.2-pastlevel",
    model: str = "qwen3:14b",
    provider: LLMProvider | None = None,
    llm_config: LLMConfig | None = None,
) -> dict:
    """Run pipeline for all civs with a discord_channel_id set in DB.

    Thin wrapper: fetches unprocessed messages per civ, then delegates to
    run_pipeline() in bot mode so the SAME pipeline code runs for CLI and bot.

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

    for civ_id, civ_name, player_name, channel_id in civs:
        print(f"\n--- Processing {civ_name} (channel {channel_id}) ---")

        messages = fetch_unprocessed_messages(db_path, channel_id)
        if not messages:
            print(f"  No new messages for {civ_name}")
            aggregated["per_civ"][civ_name] = {"turns_created": 0, "entities_extracted": 0}
            continue

        # Delegate to run_pipeline in bot mode — same code path as CLI
        civ_stats = run_pipeline(
            db_path=db_path,
            civ_name=civ_name,
            player_name=player_name,
            use_llm=use_llm,
            wiki_dir=None,  # wiki generated once after all civs
            track_progress=track_progress,
            extraction_version=extraction_version,
            model=model,
            provider=provider,
            llm_config=llm_config,
            # Bot mode params — skip steps 1-4
            messages=messages,
            civ_id=civ_id,
            channel_id=channel_id,
        )

        aggregated["civs_processed"] += 1
        aggregated["total_turns_created"] += civ_stats.get("turns_created", 0)
        aggregated["total_entities_extracted"] += civ_stats.get("entities_extracted", 0)
        aggregated["per_civ"][civ_name] = civ_stats

    # Wiki generation (once after all civs)
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
    parser.add_argument("--data-dir", help="Path to markdown files directory")
    parser.add_argument("--civ", help="Civilization name")
    parser.add_argument("--db", default="aurelm.db", help="Database file path")
    parser.add_argument("--player", default=None, help="Player name")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM summarization (use extractive fallback)")
    parser.add_argument("--wiki-dir", default=None, help="Wiki directory (enables wiki generation)")
    parser.add_argument("--track-progress", action="store_true", help="Enable progress tracking for UI")
    parser.add_argument(
        "--extraction-version", required=True,
        help=f"Extraction version to use. Available: {', '.join(list_versions())}",
    )
    parser.add_argument(
        "--model", default="llama3.1:8b",
        help="Model to use for LLM extraction (default: llama3.1:8b)",
    )
    parser.add_argument(
        "--llm-provider", choices=["ollama", "openrouter"],
        help="LLM provider: 'ollama' (local) or 'openrouter' (cloud). Required unless --llm-config is used.",
    )
    parser.add_argument(
        "--llm-config", default=None,
        help="Path to LLM config JSON for per-stage model selection. "
             "Overrides --model and --llm-provider when set.",
    )
    parser.add_argument(
        "--reextract-facts", action="store_true",
        help="Re-run hybrid fact extraction (LLM + patterns) on all existing turns and update DB"
    )
    parser.add_argument(
        "--pattern-only", action="store_true",
        help="With --reextract-facts: skip LLM, run only the keyword/entity pattern pass (fast)"
    )
    args = parser.parse_args()

    if args.reextract_facts:
        if not args.civ:
            parser.error("--reextract-facts requires --civ")
        conn = get_connection(args.db)
        conn.row_factory = __import__("sqlite3").Row
        row = conn.execute(
            "SELECT id, name FROM civ_civilizations WHERE name = ?", (args.civ,)
        ).fetchone()
        if not row:
            parser.error(f"Civilization '{args.civ}' not found in {args.db}")
        civ_id = row["id"]
        conn.close()
        print(f"Re-extracting facts for '{args.civ}' (civ_id={civ_id})...")
        use_llm = not (args.no_llm or args.pattern_only)
        reextract_facts_for_civ(args.db, civ_id, use_llm=use_llm)
        return

    if not args.data_dir or not args.civ:
        parser.error("--data-dir and --civ are required unless using --reextract-facts")

    # Build LLM config: either from JSON file or from CLI args
    config: LLMConfig | None = None
    llm_provider: LLMProvider | None = None

    if args.llm_config:
        # Per-stage config from JSON file — overrides --model and --llm-provider
        config = load_llm_config(args.llm_config)
        llm_provider = create_provider(config.provider_name) if not args.no_llm else None
    elif not args.no_llm:
        # Classic CLI args — require --llm-provider
        if not args.llm_provider:
            parser.error("--llm-provider is required unless --llm-config or --no-llm is used")
        config = llm_config_from_cli(args.model, args.llm_provider)
        llm_provider = create_provider(args.llm_provider)

    run_pipeline(
        data_dir=args.data_dir,
        db_path=args.db,
        civ_name=args.civ,
        player_name=args.player,
        use_llm=not args.no_llm,
        wiki_dir=args.wiki_dir,
        track_progress=args.track_progress,
        extraction_version=args.extraction_version,
        model=config.default_model if config else args.model,
        provider=llm_provider,
        llm_config=config,
    )


if __name__ == "__main__":
    main()
