"""Batch benchmark: all extraction versions × selected models.

Runs each (version, model) combo on turn 14 via OpenRouter,
collects P/R/F1 and prints a summary table at the end.

Usage:
    cd pipeline
    python -m benchmark_matrix
"""

import sys
import time
import traceback
from pathlib import Path

from benchmark import run_benchmark, REFERENCE_PATH

# -- Config --
DATA_DIR = str(Path(__file__).parent.parent / ".." / "civjdr" / "Background")
CIV = "Civilisation de la Confluence"
TURN = "14"
MAX_CHUNKS = 3  # ~3 chunks, keeps each run fast
REFERENCE = Path(__file__).parent / "data" / "reference_turn14.json"

# Models to test (OpenRouter names, passed as Ollama-style)
MODELS = [
    "llama3.1:8b",
    "mistral-nemo",
]

# All extraction versions to test
VERSIONS = [
    "v1-baseline",
    "v2-fewshot",
    "v3-recall",
    "v4-strict-recall",
    "v5-schema",
    "v6-combo",
    "v7-v4t0",
    "v8-negshot",
    "v9-neginuser",
    "v10-mark",
    "v11-heavy",
    "v12-think",
    "v13-validate",
    "v13.1-validate",
    "v13.2-validate",
    "v14-certainty",
    "v14-certainty-5",
    "v14-certainty-pct",
    "v14-blind",
    "v14-blind-10",
    "v14-certainty-10",
    "v14-nemo-pct",
]


def main():
    """Run full benchmark matrix and print summary table."""
    total = len(VERSIONS) * len(MODELS)
    print(f"=== Benchmark Matrix: {len(VERSIONS)} versions x {len(MODELS)} models = {total} runs ===")
    print(f"Turn: {TURN} | Max chunks: {MAX_CHUNKS} | Provider: openrouter")
    print(f"Models: {', '.join(MODELS)}")
    print()

    # Collect results: list of (version, model, P, R, F1, TP, FP, FN, time)
    results = []
    errors = []

    for i, version in enumerate(VERSIONS):
        for j, model in enumerate(MODELS):
            run_num = i * len(MODELS) + j + 1
            label = f"[{run_num}/{total}] {version} + {model}"
            print(f"\n{'='*60}")
            print(f"  {label}")
            print(f"{'='*60}")

            try:
                t0 = time.time()
                scores_list = run_benchmark(
                    data_dir=DATA_DIR,
                    civ_name=CIV,
                    model=model,
                    extraction_version=version,
                    turn_arg=TURN,
                    reference_path=REFERENCE,
                    max_chunks=MAX_CHUNKS,
                    llm_provider="openrouter",
                )
                elapsed = time.time() - t0

                if scores_list:
                    s = scores_list[0]
                    results.append({
                        "version": version,
                        "model": model,
                        "P": s["precision"],
                        "R": s["recall"],
                        "F1": s["f1"],
                        "TP": s["n_tp"],
                        "FP": s["n_fp"],
                        "FN": s["n_fn"],
                        "time": elapsed,
                    })
                else:
                    errors.append((version, model, "No scores returned"))

            except Exception as e:
                elapsed = time.time() - t0
                errors.append((version, model, str(e)))
                traceback.print_exc()
                print(f"  FAILED after {elapsed:.0f}s: {e}")

    # -- Summary table --
    print("\n\n")
    print("=" * 100)
    print("  BENCHMARK MATRIX RESULTS")
    print("=" * 100)

    # Header
    print(f"{'Version':<22} | {'Model':<16} | {'P':>6} | {'R':>6} | {'F1':>6} | {'TP':>3} | {'FP':>3} | {'FN':>3} | {'Time':>5}")
    print("-" * 100)

    # Sort by F1 descending for readability
    results.sort(key=lambda r: r["F1"], reverse=True)

    for r in results:
        print(
            f"{r['version']:<22} | {r['model']:<16} | "
            f"{r['P']:>5.1%} | {r['R']:>5.1%} | {r['F1']:>5.1%} | "
            f"{r['TP']:>3} | {r['FP']:>3} | {r['FN']:>3} | "
            f"{r['time']:>4.0f}s"
        )

    if errors:
        print(f"\n--- ERRORS ({len(errors)}) ---")
        for v, m, err in errors:
            print(f"  {v} + {m}: {err[:80]}")

    # Per-model best
    print("\n--- Best F1 per model ---")
    for model in MODELS:
        model_results = [r for r in results if r["model"] == model]
        if model_results:
            best = model_results[0]  # already sorted by F1
            print(f"  {model}: {best['version']} -> F1={best['F1']:.1%} (P={best['P']:.1%}, R={best['R']:.1%})")

    # Per-version comparison (side by side)
    print("\n--- Side-by-side (Llama vs Nemo) ---")
    print(f"{'Version':<22} | {'Llama F1':>9} | {'Nemo F1':>9} | {'Winner':>8}")
    print("-" * 60)

    # Group by version
    by_version = {}
    for r in results:
        by_version.setdefault(r["version"], {})[r["model"]] = r

    for version in VERSIONS:
        if version not in by_version:
            continue
        vr = by_version[version]
        llama_f1 = vr.get("llama3.1:8b", {}).get("F1", 0)
        nemo_f1 = vr.get("mistral-nemo", {}).get("F1", 0)
        winner = "Llama" if llama_f1 > nemo_f1 else ("Nemo" if nemo_f1 > llama_f1 else "Tie")
        print(
            f"{version:<22} | {llama_f1:>8.1%} | {nemo_f1:>8.1%} | {winner:>8}"
        )

    print(f"\nTotal runs: {len(results)} OK, {len(errors)} errors")


if __name__ == "__main__":
    main()
