"""Score pipeline extraction against reference T01-T08 ground truth.

Computes Precision, Recall, F1 per turn and globally.
Matching is alias-aware and fuzzy (strips accents, articles, lowercase).

Usage (from pipeline/ dir):
    py -3.12 score_t1_t8.py [--db PATH] [--ref PATH] [--verbose]

    --db    Path to DB from test_t1_t8.py (default: AppData Temp t1_t8_test.db)
    --ref   Path to reference JSON (default: pipeline/data/reference_turns_t1_t8.json)
    --verbose  Show per-entity TP/FP/FN details
"""

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

# Allow importing pipeline modules when run from pipeline/ dir
sys.path.insert(0, str(Path(__file__).parent))

REF_PATH = Path(__file__).parent / "data" / "reference_turns_t1_t8.json"
DB_PATH = r"C:\Users\alexi\AppData\Local\Temp\t1_t8_test.db"


# ---------------------------------------------------------------------------
# Normalization (same as _normalize_for_fuzzy in fact_extractor.py)
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


# ---------------------------------------------------------------------------
# Load reference
# ---------------------------------------------------------------------------

def load_reference(ref_path: Path) -> dict:
    """Load reference JSON and build per-turn normalized lookup sets.

    Returns:
        {
          "T02": {norm_name: canonical_name, ...},
          ...
          "_aliases": {norm_alias: norm_canonical, ...}   # global alias map
        }
    """
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)

    # Build alias map: normalized alias -> normalized canonical name
    alias_map: dict[str, str] = {}
    for ent in ref.get("entities", []):
        canon_norm = normalize(ent["name"])
        alias_map[canon_norm] = canon_norm  # canonical maps to itself
        for alias in ent.get("aliases", []):
            alias_map[normalize(alias)] = canon_norm

    # Per-turn: norm_name -> canonical display name
    by_turn: dict[str, dict[str, str]] = {}
    for turn_key, entities in ref.get("by_turn", {}).items():
        mapping: dict[str, str] = {}
        for ent in entities:
            norm = normalize(ent["name"])
            # Resolve to canonical via alias map
            canon = alias_map.get(norm, norm)
            mapping[canon] = ent["name"]
        by_turn[turn_key] = mapping

    by_turn["_aliases"] = alias_map  # type: ignore
    return by_turn


# ---------------------------------------------------------------------------
# Load extracted entities from DB
# ---------------------------------------------------------------------------

def load_extracted(db_path: str) -> dict[str, list[str]]:
    """Load extracted entities grouped by first_seen_turn.

    Returns: {"T02": ["Oracle", "Sans-Ciels", ...], ...}
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT canonical_name, entity_type, first_seen_turn "
        "FROM entity_entities WHERE is_active=1 "
        "ORDER BY first_seen_turn, entity_type, canonical_name"
    ).fetchall()
    conn.close()

    by_turn: dict[str, list[str]] = {}
    for r in rows:
        key = f"T{r['first_seen_turn']:02d}"
        by_turn.setdefault(key, []).append(r["canonical_name"])
    return by_turn


# ---------------------------------------------------------------------------
# Score one turn
# ---------------------------------------------------------------------------

def score_turn(
    turn_key: str,
    extracted: list[str],
    reference: dict[str, str],  # norm_canonical -> display
    alias_map: dict[str, str],  # norm_any -> norm_canonical
    verbose: bool = False,
) -> dict:
    """Compute TP/FP/FN for one turn.

    An extracted entity is a TP if its normalized form (or any alias of it)
    maps to a canonical name that's in the reference set for this turn.
    """
    ref_set = set(reference.keys())  # normalized canonical names

    tp_names = []
    fp_names = []
    matched_ref = set()

    for name in extracted:
        norm = normalize(name)
        # Check direct match, then alias resolution
        canon = alias_map.get(norm, norm)
        if canon in ref_set:
            tp_names.append(name)
            matched_ref.add(canon)
        else:
            fp_names.append(name)

    fn_names = [reference[c] for c in ref_set if c not in matched_ref]

    tp = len(tp_names)
    fp = len(fp_names)
    fn = len(fn_names)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    if verbose and (tp + fp + fn) > 0:
        print(f"\n  {turn_key} details:")
        for n in sorted(tp_names):
            print(f"    TP  {n}")
        for n in sorted(fp_names):
            print(f"    FP  {n}")
        for n in sorted(fn_names):
            print(f"    FN  {n}")

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "tp_names": tp_names, "fp_names": fp_names, "fn_names": fn_names,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_all_extracted_global(db_path: str, alias_map: dict[str, str]) -> set[str]:
    """Load ALL extracted entities as a global normalized canonical set.

    Used for turn-agnostic scoring: an entity is a TP for a reference turn if
    it appears *anywhere* in the DB, regardless of which turn first saw it.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT canonical_name FROM entity_entities WHERE is_active=1"
    ).fetchall()
    conn.close()

    global_set: set[str] = set()
    for (name,) in rows:
        norm = normalize(name)
        canon = alias_map.get(norm, norm)
        global_set.add(canon)
    return global_set


def main(args):
    """Per-turn recall table (turn-agnostic: checks global DB, not first_seen_turn).

    FP has no meaning per-turn — an entity extracted from T06 that belongs to
    T08 in the reference is still a TP (we found it). FP is reported globally.
    Columns: Turn | Ref | TP | FN | R%
    """
    ref_data = load_reference(Path(args.ref))
    alias_map: dict[str, str] = ref_data.pop("_aliases")  # type: ignore

    # Global set: every entity anywhere in DB (normalized canonical)
    global_extracted = load_all_extracted_global(args.db, alias_map)

    turns = sorted(ref_data.keys())

    print(f"\n  Per-turn Recall (entity found anywhere in DB — FP shown globally)")
    print(f"\n{'Turn':>4}  {'Ref':>3}  {'TP':>3}  {'FN':>3}  {'R%':>5}")
    print(f"{'----':>4}  {'---':>3}  {'--':>3}  {'--':>3}  {'---':>5}")

    total_tp = total_fn = 0

    for turn_key in turns:
        reference = ref_data[turn_key]
        if not reference:
            continue  # T01 has 0 entities

        ref_set = reference  # norm_canonical -> display

        tp_names, fn_names = [], []
        for ref_norm, ref_display in ref_set.items():
            if ref_norm in global_extracted:
                tp_names.append(ref_display)
            else:
                fn_names.append(ref_display)

        tp = len(tp_names)
        fn = len(fn_names)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        total_tp += tp
        total_fn += fn

        print(f"  {turn_key}  {len(reference):>3}  {tp:>3}  {fn:>3}  {recall*100:>5.1f}")

        if args.verbose:
            for n in sorted(tp_names):
                print(f"    TP  {n}")
            for n in sorted(fn_names):
                print(f"    FN  {n}")

    ref_total = sum(len(v) for v in ref_data.values())
    g_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    print(f"{'----':>4}  {'---':>3}  {'--':>3}  {'--':>3}  {'---':>5}")
    print(f"  TOT  {ref_total:>3}  {total_tp:>3}  {total_fn:>3}  {g_r*100:>5.1f}")
    print(f"\n  Overall Recall (per-turn, global DB) = {g_r*100:.1f}%")
    print(f"  ({total_fn} reference entities truly absent from DB)\n")


def fuzzy_match(a: str, b: str) -> bool:
    """Pass 2 matching: substring or high token overlap.

    Catches:
    - "Serpes grossières" vs "Serpes grossières taillées dans des os" (substring)
    - "Rhombes en pierres" vs "Rhombes en pierre" (token overlap)
    - "Sans Ciel" vs "Sans-ciels" (already caught by normalize, but token fallback too)
    """
    # Substring in either direction
    if a in b or b in a:
        return True
    # Token Jaccard similarity > 0.6 (strict), with French stopwords removed
    # to avoid false matches like "Tailleurs de pierre" ~= "Lait de Pierre"
    STOPWORDS = {"de", "du", "des", "le", "la", "les", "l", "d", "et", "en", "un", "une"}
    ta = set(a.split()) - STOPWORDS
    tb = set(b.split()) - STOPWORDS
    if not ta or not tb:
        return False
    jaccard = len(ta & tb) / len(ta | tb)
    return jaccard > 0.6


def global_score(ref_path: Path, db_path: str, verbose: bool = False, simulate_filter: bool = False):
    """Compare the full extracted entity set against full reference, ignoring which turn.

    This is the fair measure: does the entity exist anywhere in the DB?
    Per-turn scoring artificially deflates recall when first_seen_turn differs from reference.

    simulate_filter: if True, apply is_noise_entity() to simulate updated entity_filter
                     on existing DB results without re-running the pipeline.
    """
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)

    # Build alias map and flat reference set
    alias_map: dict[str, str] = {}
    for ent in ref.get("entities", []):
        cn = normalize(ent["name"])
        alias_map[cn] = cn
        for a in ent.get("aliases", []):
            alias_map[normalize(a)] = cn
    ref_set = set(alias_map.values())

    # All extracted entities (ignore turn)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT canonical_name, entity_type FROM entity_entities WHERE is_active=1"
    ).fetchall()
    conn.close()

    if simulate_filter:
        # Import updated entity_filter and apply it to simulate effect of noise filtering
        # without re-running the pipeline.
        try:
            from pipeline.entity_filter import is_noise_entity
        except ImportError:
            from entity_filter import is_noise_entity  # type: ignore
        before = len(rows)
        rows = [(name, etype) for name, etype in rows if not is_noise_entity(name)]
        print(f"  [simulate-filter] Removed {before - len(rows)} noisy entities ({len(rows)} remain)")

    # --- Pass 1: exact normalized match (alias-aware) ---
    tp1, fp1_names, matched1 = [], [], set()
    for name, _ in rows:
        norm = normalize(name)
        canon = alias_map.get(norm, norm)
        if canon in ref_set:
            tp1.append(name)
            matched1.add(canon)
        else:
            fp1_names.append(name)

    fn1 = [k for k in ref_set if k not in matched1]  # normalized canonical names

    # --- Pass 2: fuzzy match on remainders ---
    # Try to match each unmatched extracted entity against each unmatched ref entity.
    # Greedy: first fuzzy match wins; both are removed from the unmatched pools.
    tp2, fp2_names, fn2 = [], [], list(fn1)
    still_unmatched_ref = list(fn1)

    for ext_name in fp1_names:
        ext_norm = normalize(ext_name)
        matched = False
        for ref_norm in still_unmatched_ref:
            if fuzzy_match(ext_norm, ref_norm):
                tp2.append((ext_name, ref_norm))
                still_unmatched_ref.remove(ref_norm)
                matched = True
                break
        if not matched:
            fp2_names.append(ext_name)

    fn2 = still_unmatched_ref  # what remains after pass 2

    tp = len(tp1) + len(tp2)
    fp = len(fp2_names)
    fn = len(fn2)
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    print(f"\n=== SCORE GLOBAL 2-passes (ignore first_seen_turn) ===")
    print(f"  Ref={len(ref_set)}  Ext={len(rows)}")
    print(f"  Pass1 (exact+alias): TP={len(tp1)}  residual FP={len(fp1_names)}  FN={len(fn1)}")
    print(f"  Pass2 (fuzzy):       TP={len(tp2)}  residual FP={len(fp2_names)}  FN={len(fn2)}")
    print(f"  TOTAL: TP={tp}  FP={fp}  FN={fn}")
    print(f"  P={p*100:.1f}%  R={r*100:.1f}%  F1={f1*100:.1f}%")

    if verbose:
        print(f"\n  TP Pass1 ({len(tp1)}):")
        for n in sorted(tp1): print(f"    {n}")
        print(f"\n  TP Pass2 ({len(tp2)}) — fuzzy matches:")
        for ext, ref in sorted(tp2): print(f"    '{ext}'  ~=  '{ref}'")
        print(f"\n  FP ({fp}) — vrais faux positifs apres 2 passes:")
        for n in sorted(fp2_names): print(f"    {n}")
        print(f"\n  FN ({fn}) — vraiment absents du DB:")
        for n in sorted(fn2): print(f"    {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score T1-T8 extraction vs reference")
    parser.add_argument("--db", default=DB_PATH, help="Path to pipeline DB")
    parser.add_argument("--ref", default=str(REF_PATH), help="Path to reference JSON")
    parser.add_argument("--verbose", action="store_true", help="Show TP/FP/FN per entity")
    parser.add_argument("--global-only", action="store_true", help="Only show global set score (skip per-turn table)")
    parser.add_argument("--simulate-filter", action="store_true",
                        help="Apply entity_filter to existing DB results (simulates updated filter without re-run)")
    args = parser.parse_args()

    if not args.global_only:
        main(args)  # per-turn recall table (turn-agnostic)
    global_score(Path(args.ref), args.db, verbose=args.verbose, simulate_filter=args.simulate_filter)
