"""Benchmark validate prompt versions against a pre-extracted entity pool.

Loads raw entities from pipeline_llm_calls (extraction responses before any
validate pass), then tests each VALIDATE_VERSIONS prompt and scores the result
against the reference ground truth.

Usage (from pipeline/ dir):
    py -3.12 benchmark_validate.py [--db PATH] [--ref PATH] [--versions v1,v2] [--model MODEL]

    --db        DB from test_t1_t8.py (default: AppData Temp t1_t8_test.db)
    --ref       Reference JSON (default: data/reference_turns_t1_t8.json)
    --versions  Comma-separated list of versions to test (default: all)
    --model     LLM model for validate call (default: qwen3:14b)
    --verbose   Show per-entity details for each version
"""

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.extraction_versions import VALIDATE_VERSIONS
from pipeline.llm_provider import OllamaProvider, create_provider
from pipeline.entity_filter import is_noise_entity

DB_PATH = r"C:\Users\alexi\AppData\Local\Temp\t1_t8_test.db"
REF_PATH = Path(__file__).parent / "data" / "reference_turns_t1_t8.json"


# ---------------------------------------------------------------------------
# Normalization (same as score_t1_t8.py)
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase, strip accents, remove French articles, collapse spaces."""
    text = text.lower().strip()
    text = text.replace("\u0153", "oe").replace("\u0152", "oe")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    for art in ["l'", "le ", "la ", "les "]:
        if text.startswith(art):
            text = text[len(art):]
    return text.strip()


def fuzzy_match(a: str, b: str) -> bool:
    """Substring or token Jaccard > 0.6 (French stopwords removed)."""
    if a in b or b in a:
        return True
    STOP = {"de", "du", "des", "le", "la", "les", "l", "d", "et", "en", "un", "une"}
    ta = set(a.split()) - STOP
    tb = set(b.split()) - STOP
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) > 0.6


# ---------------------------------------------------------------------------
# Load reference
# ---------------------------------------------------------------------------

def load_reference(ref_path: Path) -> tuple[set[str], dict[str, str]]:
    """Return (ref_set of normalized canonicals, alias_map norm->norm_canon)."""
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)
    alias_map: dict[str, str] = {}
    for ent in ref.get("entities", []):
        cn = normalize(ent["name"])
        alias_map[cn] = cn
        for a in ent.get("aliases", []):
            alias_map[normalize(a)] = cn
    ref_set = set(alias_map.values())
    return ref_set, alias_map


# ---------------------------------------------------------------------------
# Load raw entity pool from pipeline_llm_calls (pre-validate)
# ---------------------------------------------------------------------------

def load_raw_entities(db_path: str) -> tuple[list[tuple[str, str]], dict[int, str]]:
    """Parse extraction LLM responses to reconstruct the pre-validate entity pool.

    Reads entity_extraction, focus_extraction, fact_extraction responses,
    parses entity lists, applies noise filter and dedup.

    Returns:
        entities: [(text, label), ...] deduped globally
        turn_texts: {turn_id: combined segment text} for validate prompt context
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Raw extraction responses (entity pool before validate)
    calls = conn.execute(
        "SELECT turn_id, stage, response FROM pipeline_llm_calls "
        "WHERE stage IN ('entity_extraction', 'focus_extraction', 'fact_extraction') "
        "ORDER BY turn_id, id"
    ).fetchall()

    # Per-turn text from segments (non-choice GM segments only)
    segs = conn.execute(
        "SELECT turn_id, content FROM turn_segments "
        "WHERE source='gm' AND segment_type != 'choice' "
        "ORDER BY turn_id, segment_order"
    ).fetchall()
    conn.close()

    # Build turn texts
    turn_texts: dict[int, str] = {}
    for seg in segs:
        tid = seg["turn_id"]
        turn_texts[tid] = turn_texts.get(tid, "") + "\n" + seg["content"]

    # Parse entity pool — dedup by normalized text globally
    seen: dict[str, tuple[str, str]] = {}  # norm -> (text, label)
    for call in calls:
        try:
            data = json.loads(call["response"])
        except Exception:
            continue
        ents = data.get("entities", [])
        for ent in ents:
            if not isinstance(ent, dict):
                continue
            text = (ent.get("text") or ent.get("name") or "").strip()
            label = (ent.get("label") or ent.get("type") or "unknown").strip()
            if not text or len(text) < 2:
                continue
            if is_noise_entity(text):
                continue
            key = normalize(text)
            if key not in seen:
                seen[key] = (text, label)

    entities = list(seen.values())
    return entities, turn_texts


# ---------------------------------------------------------------------------
# Run one validate prompt version
# ---------------------------------------------------------------------------

def _parse_validate_response(response: str, all_names: list[str]) -> list[str] | None:
    """Parse a validate LLM response into a list of kept entity names.
    Returns None on parse failure.
    """
    try:
        data = json.loads(response)
        if isinstance(data, dict) and "keep" in data:
            return [n for n in data["keep"] if isinstance(n, str)]
        elif isinstance(data, dict) and "drops" in data and "keep" not in data:
            drops_raw = data.get("drops", "")
            drop_names: set[str] = set()
            if drops_raw and isinstance(drops_raw, str):
                for entry in drops_raw.split("|"):
                    entry = entry.strip()
                    if ":" in entry:
                        drop_names.add(entry.split(":", 1)[0].strip().lower())
            return [n for n in all_names if n.lower() not in drop_names]
        elif isinstance(data, dict) and "entities" in data:
            return [
                (e.get("text") or e.get("name") or "") if isinstance(e, dict) else str(e)
                for e in data["entities"]
            ]
        return all_names
    except Exception:
        return None


def run_validate(
    entities: list[tuple[str, str]],
    turn_texts: dict[int, str],
    prompt_template: str,
    model: str,
    provider,
    text_lock: bool = False,
    union_passes: int = 1,
) -> list[str]:
    """Apply a validate prompt per-turn (like the real pipeline).

    Args:
        text_lock: If True, auto-keep entities whose text appears verbatim in the
            turn text — they skip the LLM entirely (structural lock, zero cost).
        union_passes: Run the LLM N times per turn and keep an entity if ANY pass
            keeps it (union = maximum recall). 1 = standard single pass.

    Returns: list of kept entity names (canonical text, globally deduped).
    """
    kept_global: dict[str, str] = {}  # lower -> canonical text
    parse_fails = 0
    locked_count = 0

    for turn_id, turn_text in turn_texts.items():
        # Entities whose text appears (substring) in this turn
        turn_entities = [
            (text, label) for text, label in entities
            if text.lower() in turn_text.lower()
        ]
        if not turn_entities:
            continue

        # Text lock: auto-keep entities present verbatim in the turn text.
        # Anything literally in the text is canon — no need to ask the LLM.
        if text_lock:
            locked = [(t, l) for t, l in turn_entities if t.lower() in turn_text.lower()]
            for text, _ in locked:
                kept_global[text.lower()] = text
                locked_count += 1
            # Nothing left to validate — all present verbatim
            # (still run LLM for entities not present verbatim, but here all are)
            # Note: all turn_entities match by construction above, so nothing goes to LLM
            continue

        # Build entity lines for prompt
        entity_lines = "\n".join(f"- {text} [{label}]" for text, label in turn_entities)
        all_turn_names = [t for t, _ in turn_entities]

        try:
            prompt = prompt_template.format(text=turn_text[:2000], entities=entity_lines)
        except KeyError:
            prompt = prompt_template.format(entities=entity_lines)

        # Union voting: run N passes, keep entity if ANY pass keeps it
        union_kept: set[str] = set()
        for pass_i in range(union_passes):
            temp = 0.0 if union_passes == 1 else 0.4  # add variance for multi-pass
            response = provider.generate(
                model=model,
                prompt=prompt,
                temperature=temp,
                max_tokens=512,
                json_mode=True,
            )
            kept = _parse_validate_response(response, all_turn_names)
            if kept is None:
                parse_fails += 1
                kept = all_turn_names  # fallback keep all on parse fail
            union_kept.update(k.lower() for k in kept)

        # Merge into global: keep if in union across all passes
        for name in all_turn_names:
            if name.lower() in union_kept:
                kept_global[name.lower()] = name

    if locked_count:
        print(f"  [lock] {locked_count} entities auto-kept by text lock")
    if parse_fails:
        print(f"  [warn] {parse_fails} parse failures (kept all for those turns)")

    return list(kept_global.values())


# ---------------------------------------------------------------------------
# Score a list of entity names against reference
# ---------------------------------------------------------------------------

def score(entity_names: list[str], ref_set: set[str], alias_map: dict[str, str]) -> dict:
    """Compute TP/FP/FN using 2-pass matching (exact+alias, then fuzzy)."""
    # Pass 1: exact + alias
    tp1, fp1, matched = [], [], set()
    for name in entity_names:
        norm = normalize(name)
        canon = alias_map.get(norm, norm)
        if canon in ref_set:
            tp1.append(name)
            matched.add(canon)
        else:
            fp1.append(name)

    fn1 = [c for c in ref_set if c not in matched]

    # Pass 2: fuzzy on remainders
    tp2, fp2 = [], []
    unmatched_ref = list(fn1)
    for name in fp1:
        norm = normalize(name)
        matched_fuzzy = False
        for ref_norm in unmatched_ref:
            if fuzzy_match(norm, ref_norm):
                tp2.append((name, ref_norm))
                unmatched_ref.remove(ref_norm)
                matched_fuzzy = True
                break
        if not matched_fuzzy:
            fp2.append(name)

    fn2 = unmatched_ref
    tp = len(tp1) + len(tp2)
    fp = len(fp2)
    fn = len(fn2)
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "p": p, "r": r, "f1": f1,
        "tp1": tp1, "tp2": tp2, "fp2": fp2, "fn2": fn2,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark validate prompt versions")
    parser.add_argument("--db", default=DB_PATH, help="Pipeline DB path")
    parser.add_argument("--ref", default=str(REF_PATH), help="Reference JSON path")
    parser.add_argument("--versions", default="all",
                        help="Comma-separated version names or 'all'")
    parser.add_argument("--model", default="qwen/qwen3-14b",
                        help="LLM model for validate calls")
    parser.add_argument("--provider", default="openrouter",
                        help="LLM provider: openrouter or ollama")
    parser.add_argument("--verbose", action="store_true",
                        help="Show FP/FN breakdown per version")
    parser.add_argument("--text-lock", action="store_true",
                        help="Auto-keep entities present verbatim in turn text (skip LLM)")
    parser.add_argument("--union-passes", type=int, default=1,
                        help="Run validate N times per turn, keep if any pass keeps (default: 1)")
    args = parser.parse_args()

    # Select versions to test
    if args.versions == "all":
        versions_to_test = list(VALIDATE_VERSIONS.keys())
    else:
        versions_to_test = [v.strip() for v in args.versions.split(",")]
        unknown = [v for v in versions_to_test if v not in VALIDATE_VERSIONS]
        if unknown:
            print(f"Unknown validate versions: {unknown}")
            print(f"Available: {list(VALIDATE_VERSIONS.keys())}")
            sys.exit(1)

    print(f"\n=== Validate Prompt Benchmark ===")
    print(f"DB: {args.db}")
    print(f"Ref: {args.ref}")
    print(f"Model: {args.model}")
    print(f"Versions: {versions_to_test}\n")

    # Load data
    ref_set, alias_map = load_reference(Path(args.ref))
    print(f"Reference: {len(ref_set)} entities")

    entities, turn_texts = load_raw_entities(args.db)
    print(f"Raw entity pool: {len(entities)} entities (from extraction LLM calls)\n")

    # Score raw pool baseline (no validate)
    baseline = score([t for t, _ in entities], ref_set, alias_map)
    print(f"Baseline (no validate): TP={baseline['tp']}  FP={baseline['fp']}  FN={baseline['fn']}")
    print(f"  P={baseline['p']*100:.1f}%  R={baseline['r']*100:.1f}%  F1={baseline['f1']*100:.1f}%\n")

    # LLM provider for validate calls
    provider = create_provider(args.provider)

    # Run each version
    results = {}
    for vname in versions_to_test:
        prompt_template, description = VALIDATE_VERSIONS[vname]
        print(f"--- {vname} ---")
        print(f"  {description[:80]}...")

        kept_names = run_validate(
            entities, turn_texts, prompt_template, args.model, provider,
            text_lock=args.text_lock,
            union_passes=args.union_passes,
        )
        s = score(kept_names, ref_set, alias_map)
        results[vname] = s

        print(f"  Kept: {len(kept_names)} / {len(entities)}  "
              f"(dropped {len(entities) - len(kept_names)})")
        print(f"  TP={s['tp']}  FP={s['fp']}  FN={s['fn']}")
        print(f"  P={s['p']*100:.1f}%  R={s['r']*100:.1f}%  F1={s['f1']*100:.1f}%")

        if args.verbose:
            print(f"  FP ({s['fp']}):")
            for n in sorted(s['fp2']): print(f"    FP  {n}")
            print(f"  FN ({s['fn']}):")
            for n in sorted(s['fn2']): print(f"    FN  {n}")
        print()

    # Summary table
    print("=" * 65)
    print(f"{'Version':<25} {'Kept':>5} {'TP':>4} {'FP':>4} {'FN':>4} {'P%':>6} {'R%':>6} {'F1%':>6}")
    print("-" * 65)
    print(f"{'baseline (no validate)':<25} {len(entities):>5} "
          f"{baseline['tp']:>4} {baseline['fp']:>4} {baseline['fn']:>4} "
          f"{baseline['p']*100:>5.1f}% {baseline['r']*100:>5.1f}% {baseline['f1']*100:>5.1f}%")
    for vname, s in results.items():
        ents_kept = len([1 for _ in range(s["tp"] + s["fp"])])  # tp+fp = total kept
        print(f"  {vname:<23} {s['tp']+s['fp']:>5} "
              f"{s['tp']:>4} {s['fp']:>4} {s['fn']:>4} "
              f"{s['p']*100:>5.1f}% {s['r']*100:>5.1f}% {s['f1']*100:>5.1f}%")
    print("=" * 65)


if __name__ == "__main__":
    main()
