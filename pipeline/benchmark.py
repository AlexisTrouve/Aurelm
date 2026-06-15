"""Benchmark script for entity extraction quality.

Runs extraction on selected turns and scores against reference_entities.json.
Standalone dev tool -- uses a temp DB, does not touch the main database.

Usage (from pipeline/ directory):
    python -m benchmark \
        --data-dir ../../civjdr/Background \
        --civ "Civilisation de la Confluence" \
        --model qwen3:8b \
        --extraction-version v7-v4t0 \
        --turn last
"""

import argparse
import json
import os
import tempfile
import time
import unicodedata
from pathlib import Path

from pipeline.db import init_db, run_migrations, register_civilization
from pipeline.loader import load_directory
from pipeline.ingestion import fetch_unprocessed_messages
from pipeline.chunker import detect_turn_boundaries
from pipeline.classifier import classify_segments
from pipeline.extraction_versions import get_version, list_versions
from pipeline.fact_extractor import FactExtractor
from pipeline.llm_provider import create_provider, load_llm_config, LLMConfig

# Same constant as runner.py
GM_AUTHORS = {"Arthur Ignatus", "arthur ignatus"}

REFERENCE_PATH = Path(__file__).parent / "data" / "reference_entities.json"


def normalize(text: str) -> str:
    """Normalize for comparison: lowercase, strip accents, strip articles."""
    text = text.lower().strip()
    # Normalize curly apostrophes to straight
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    # Strip accents
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Strip leading French articles
    for article in ["l'", "le ", "la ", "les "]:
        if text.startswith(article):
            text = text[len(article):]
            break
    return text.strip()


def find_gm_author_id(messages: list) -> str:
    """Find the GM's author_id from messages.

    Uses prefix matching so "Arthur Ignatus (03/09/2024)" matches "Arthur Ignatus".
    Skips synthetic __player__ placeholders.
    """
    for msg in messages:
        name_lower = msg.author_name.lower()
        if any(name_lower.startswith(gm.lower()) for gm in GM_AUTHORS):
            return msg.author_id
    # Fallback: first non-synthetic message
    for msg in messages:
        if msg.author_name != "__player__":
            return msg.author_id
    return messages[0].author_id if messages else "unknown"


def load_reference_entities(civ_name: str, reference_path: Path | None = None) -> list[dict]:
    """Load reference entities. Supports both global and per-turn reference files."""
    path = reference_path or REFERENCE_PATH
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Per-turn format: {"entities": [...]}
    if "entities" in data and "civilizations" not in data:
        return data["entities"]
    # Global format: {"civilizations": {"Civ Name": {"entities": [...]}}}
    civs = data.get("civilizations", {})
    if civ_name not in civs:
        available = list(civs.keys())
        raise ValueError(f"Civ '{civ_name}' not in reference. Available: {available}")
    return civs[civ_name]["entities"]


def filter_reference_by_text(reference: list[dict], text: str) -> list[dict]:
    """Keep only reference entities whose name or alias appears in the turn text."""
    text_lower = text.lower()
    result = []
    for ent in reference:
        names_to_check = [ent["name"]] + ent.get("aliases", [])
        if any(n.lower() in text_lower for n in names_to_check):
            result.append(ent)
    return result


def score_extraction(
    extracted: list, reference: list[dict]
) -> dict:
    """Score extracted entities against reference.

    Returns dict with tp, fp, fn lists and precision/recall/f1.
    """
    # Build reference lookup: normalized name -> entity, plus aliases
    ref_lookup: dict[str, dict] = {}
    for ent in reference:
        ref_lookup[normalize(ent["name"])] = ent
        for alias in ent.get("aliases", []):
            ref_lookup[normalize(alias)] = ent

    # Match each extracted entity
    matched_ref = set()  # track which reference entities were matched
    tp = []
    fp = []

    for ext in extracted:
        ext_name = ext.text if hasattr(ext, "text") else ext.get("text", "")
        ext_type = ext.label if hasattr(ext, "label") else ext.get("label", "")
        norm = normalize(ext_name)

        if norm in ref_lookup:
            ref_ent = ref_lookup[norm]
            ref_key = ref_ent["name"]
            if ref_key not in matched_ref:
                matched_ref.add(ref_key)
                tp.append(f"{ext_name} [{ext_type}]")
            else:
                # Already matched this ref entity -- duplicate extraction
                fp.append(f"{ext_name} [{ext_type}]")
        else:
            fp.append(f"{ext_name} [{ext_type}]")

    # FN: reference entities not matched
    fn = []
    for ent in reference:
        if ent["name"] not in matched_ref:
            fn.append(f"{ent['name']} [{ent['type']}]")

    n_tp = len(tp)
    n_fp = len(fp)
    n_fn = len(fn)
    precision = n_tp / (n_tp + n_fp) if (n_tp + n_fp) > 0 else 0.0
    recall = n_tp / (n_tp + n_fn) if (n_tp + n_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "n_tp": n_tp, "n_fp": n_fp, "n_fn": n_fn,
    }


def parse_turn_arg(turn_arg: str, num_turns: int) -> list[int]:
    """Parse --turn argument into list of 0-based turn indices.

    Accepts:
      'last'  → last turn only
      'all'   → every turn (for full-corpus aggregate scoring)
      '14'    → turn 14 (1-based)
      '1,5,14' → multiple turns
    """
    if turn_arg == "last":
        return [num_turns - 1]
    if turn_arg == "all":
        return list(range(num_turns))
    indices = []
    for part in turn_arg.split(","):
        part = part.strip()
        idx = int(part)
        # Convert 1-based to 0-based
        if idx < 1 or idx > num_turns:
            raise ValueError(f"Turn {idx} out of range (1-{num_turns})")
        indices.append(idx - 1)
    return indices


def run_benchmark(
    data_dir: str,
    civ_name: str,
    model: str,
    extraction_version: str,
    turn_arg: str,
    reference_path: Path | None = None,
    max_chunks: int | None = None,
    llm_provider: str = "ollama",
    llm_config: LLMConfig | None = None,
) -> list[dict]:
    """Run benchmark on selected turns. Returns list of score dicts."""
    # Temp DB
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        # 1. Init DB + load messages
        init_db(db_path)
        run_migrations(db_path)
        register_civilization(db_path, civ_name)
        n_loaded = load_directory(data_dir, db_path)
        print(f"Loaded {n_loaded} messages from {data_dir}")

        # 2. Fetch + chunk
        messages = fetch_unprocessed_messages(db_path, "file-import")
        if not messages:
            print("No messages found.")
            return []

        gm_id = find_gm_author_id(messages)
        turns = detect_turn_boundaries(messages, gm_id)
        # Filter out synthetic player-only boundary markers inserted by new-layout loader.
        # New layout: loader inserts a fake "__player__" message before each mj file to trigger
        # GM-after-player detection. That creates a leading chunk[0] with is_gm_post=False
        # (content = "[Tour N]") which shifts all real turn indices by +1 without this filter.
        turns = [t for t in turns if t.is_gm_post]
        print(f"Detected {len(turns)} turns (GM author: {gm_id})")

        # 3. Select turns
        indices = parse_turn_arg(turn_arg, len(turns))
        print(f"Benchmarking turn(s): {[i+1 for i in indices]}")

        # 4. Load reference
        reference_all = load_reference_entities(civ_name, reference_path)
        ref_source = str(reference_path) if reference_path else "global"
        print(f"Reference: {len(reference_all)} entities ({ref_source})")

        # 5. Extract + score each turn
        version = get_version(extraction_version)
        # Use per-stage config if available, otherwise classic CLI args
        effective_provider_name = llm_config.provider_name if llm_config else llm_provider
        effective_model = llm_config.get_model("extraction") if llm_config else model
        validation_model = llm_config.get_model("validation") if llm_config else None
        provider = create_provider(effective_provider_name)
        results = []

        with FactExtractor(model=effective_model, version=version, provider=provider) as extractor:
            # Limit chunks if requested (wrap _chunk_text)
            if max_chunks is not None:
                original_chunk = extractor._chunk_text
                def limited_chunk(text):
                    chunks = original_chunk(text)
                    if len(chunks) > max_chunks:
                        print(f"  Limiting to {max_chunks}/{len(chunks)} chunks")
                    return chunks[:max_chunks]
                extractor._chunk_text = limited_chunk

            for idx in indices:
                turn = turns[idx]
                turn_text = "\n\n".join(m.content for m in turn.messages)
                word_count = len(turn_text.split())

                # Classify
                segments = classify_segments(turn_text)
                seg_dicts = [
                    {"segment_type": s.segment_type.value, "content": s.text}
                    for s in segments
                ]

                # Extract
                t0 = time.time()
                facts = extractor.extract_facts(
                    seg_dicts, raw_content=turn_text,
                    validation_model=validation_model,
                )
                elapsed = time.time() - t0

                # Filter reference to this turn's text
                ref_for_turn = filter_reference_by_text(reference_all, turn_text)

                # Score
                scores = score_extraction(facts.entities, ref_for_turn)
                scores["turn_number"] = idx + 1
                scores["word_count"] = word_count
                scores["elapsed"] = elapsed
                scores["n_extracted"] = len(facts.entities)
                scores["n_reference"] = len(ref_for_turn)
                results.append(scores)

                # Display
                print(f"\n=== Benchmark: Turn {idx+1} ({extraction_version}, {model}) ===")
                if max_chunks is not None:
                    print(f"  [limited to {max_chunks} chunks]")
                print(f"Text: {word_count:,} words | Entities extracted: {len(facts.entities)} | Time: {elapsed:.0f}s")
                print()
                print(f"Precision: {scores['precision']:.1%} ({scores['n_tp']}/{scores['n_tp']+scores['n_fp']})")
                print(f"Recall:    {scores['recall']:.1%} ({scores['n_tp']}/{scores['n_tp']+scores['n_fn']})")
                print(f"F1:        {scores['f1']:.1%}")
                print()
                if scores["tp"]:
                    print(f"TP ({scores['n_tp']}): {', '.join(scores['tp'])}")
                if scores["fp"]:
                    print(f"FP ({scores['n_fp']}): {', '.join(scores['fp'])}")
                if scores["fn"]:
                    print(f"FN ({scores['n_fn']}): {', '.join(scores['fn'])}")

                # Threshold sweep: when certainty_threshold=0, the version asked
                # for scores but didn't filter. We re-score at multiple thresholds
                # to find the optimal cutoff — one LLM run, many evaluations.
                has_certainty = any(
                    getattr(e, "certainty", 0) > 0 for e in facts.entities
                )
                if version.certainty_threshold == 0 and has_certainty:
                    lo, hi = version.certainty_scale
                    # Pick meaningful thresholds based on scale
                    if hi <= 10:
                        thresholds = list(range(lo, hi + 1))
                    else:
                        thresholds = list(range(10, hi + 1, 10))

                    print(f"\n--- Threshold sweep (scale {lo}-{hi}) ---")
                    print(f"{'Thresh':>6} | {'P':>6} | {'R':>6} | {'F1':>6} | {'TP':>3} | {'FP':>3} | {'Kept':>4}")
                    print("-" * 50)

                    best_f1, best_thresh = 0.0, 0
                    for thresh in thresholds:
                        filtered = [
                            e for e in facts.entities
                            if e.certainty >= thresh or e.certainty == 0
                        ]
                        s = score_extraction(filtered, ref_for_turn)
                        marker = ""
                        if s["f1"] > best_f1:
                            best_f1 = s["f1"]
                            best_thresh = thresh
                            marker = " <-- best"
                        print(
                            f"{thresh:>6} | {s['precision']:>5.1%} | {s['recall']:>5.1%} | "
                            f"{s['f1']:>5.1%} | {s['n_tp']:>3} | {s['n_fp']:>3} | "
                            f"{len(filtered):>4}{marker}"
                        )

                    print(f"\nBest F1: {best_f1:.1%} at threshold={best_thresh}")

        # Print OpenRouter usage/cost summary if available
        if hasattr(provider, 'get_usage'):
            usage = provider.get_usage()
            if usage["total_tokens"] > 0:
                print(f"\n--- OpenRouter usage ---")
                print(f"  Prompt tokens:     {usage['prompt_tokens']:,}")
                print(f"  Completion tokens: {usage['completion_tokens']:,}")
                print(f"  Total tokens:      {usage['total_tokens']:,}")
                if usage["total_cost"] > 0:
                    print(f"  Total cost:        ${usage['total_cost']:.6f}")

        return results

    finally:
        # Cleanup temp DB
        try:
            os.unlink(db_path)
        except OSError:
            pass
        for suffix in ("-shm", "-wal"):
            try:
                os.unlink(db_path + suffix)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark entity extraction against reference entities"
    )
    parser.add_argument("--data-dir", required=True, help="Path to markdown turn files")
    parser.add_argument("--civ", required=True, help="Civilization name")
    parser.add_argument("--model", default="qwen3:8b", help="Ollama model (default: qwen3:8b)")
    parser.add_argument(
        "--extraction-version", default="v13.2-validate",
        help=f"Extraction version (default: v7-v4t0, available: {list_versions()})"
    )
    parser.add_argument(
        "--turn", default="last",
        help="Turn selection: 'last', number (1-based), or comma-separated (e.g. 1,5,14)"
    )
    parser.add_argument(
        "--reference", default=None,
        help="Custom reference file (default: data/reference_entities.json)"
    )
    parser.add_argument(
        "--max-chunks", type=int, default=None,
        help="Limit LLM to N chunks (2 chunks ~ 3-4 min instead of 35 min for full turn)"
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
    args = parser.parse_args()

    # Build LLM config
    config: LLMConfig | None = None
    if args.llm_config:
        config = load_llm_config(args.llm_config)
    elif not args.llm_provider:
        parser.error("--llm-provider is required unless --llm-config is used")

    results = run_benchmark(
        data_dir=args.data_dir,
        civ_name=args.civ,
        model=config.default_model if config else args.model,
        extraction_version=args.extraction_version,
        turn_arg=args.turn,
        reference_path=Path(args.reference) if args.reference else None,
        max_chunks=args.max_chunks,
        llm_provider=args.llm_provider or (config.provider_name if config else "ollama"),
        llm_config=config,
    )

    # Aggregate across all turns when multiple turns are processed
    if results and len(results) > 1:
        total_tp = sum(r["n_tp"] for r in results)
        total_fp = sum(r["n_fp"] for r in results)
        total_fn = sum(r["n_fn"] for r in results)
        agg_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        agg_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        agg_f1 = 2 * agg_p * agg_r / (agg_p + agg_r) if (agg_p + agg_r) > 0 else 0
        total_words = sum(r.get("word_count", 0) for r in results)
        print(f"\n{'='*60}")
        print(f"AGGREGATE ({len(results)} turns, {total_words:,} words)")
        print(f"{'='*60}")
        print(f"Precision: {agg_p:.1%}  ({total_tp}/{total_tp+total_fp})")
        print(f"Recall:    {agg_r:.1%}  ({total_tp}/{total_tp+total_fn})")
        print(f"F1:        {agg_f1:.1%}")


if __name__ == "__main__":
    main()
