"""Quick benchmark for alias confirmation prompt versions.

Runs a given confirm_version on the 30-pair test set and reports P/R/F1.
Much faster than running on the full 113 candidates.

Usage:
    python benchmark_aliases.py --version v5-score-pct --model mistral-nemo
    python benchmark_aliases.py --version v5-score-pct --model mistral-nemo --threshold 0.5
    python benchmark_aliases.py --version v2-qwen3 --model qwen3:14b --provider openrouter
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.alias_resolver import get_confirm_version, _call_llm, _decide_by_score
from pipeline.entity_profiler import build_entity_profiles
from pipeline.llm_provider import OpenRouterProvider, OllamaProvider, create_provider

TEST_SET = Path(__file__).parent / "data" / "alias_test_set.json"
DB = Path(__file__).parent / "aurelm_qwen14b_full.db"


def run_benchmark(version_name: str, model: str, provider_name: str, threshold: float):
    test_pairs = json.loads(TEST_SET.read_text(encoding="utf-8"))["pairs"]

    provider = create_provider(provider_name)
    profiles = build_entity_profiles(str(DB), use_llm=False)
    by_name = {p.canonical_name: p for p in profiles}

    def find(name: str):
        if name in by_name:
            return by_name[name]
        # Accent-insensitive fallback
        name_l = name.lower()
        return next((p for p in profiles if p.canonical_name.lower() == name_l), None)

    version = get_confirm_version(version_name)
    score_mode = version.score_scale is not None

    results = []
    tp = fp = tn = fn = 0
    no_score = 0

    print(f"\nVersion: {version_name}  Model: {model}  Threshold: {threshold:.0%}  ({len(test_pairs)} pairs)\n")
    print(f"{'#':>2} {'Score':>6} {'Pred':>5} {'GT':>5} | {'Entité A':<30} <-> {'Entité B':<30} | Note")
    print("-" * 120)

    for i, pair in enumerate(test_pairs):
        a = find(pair["name_a"])
        b = find(pair["name_b"])
        expected = pair["expected"]

        if not a or not b:
            print(f"{i+1:>2} {'?':>6} {'?':>5} {'TP' if expected else 'TN':>5} | "
                  f"{'NOT FOUND: ' + pair['name_a'][:28]:<30} <-> {pair['name_b']:<30}")
            continue

        prompt = version.prompt.format(
            name_a=a.canonical_name, type_a=a.entity_type,
            desc_a=a.description or "(aucune)",
            name_b=b.canonical_name, type_b=b.entity_type,
            desc_b=b.description or "(aucune)",
            reason="Noms similaires (tokens communs)",
        )

        try:
            data = _call_llm(model, prompt, provider, json_mode=version.json_mode)
        except Exception as e:
            print(f"{i+1:>2} {'ERR':>6} | {str(e)[:60]}")
            continue

        # Decide confirmed or not
        if score_mode:
            confirmed, norm_score = _decide_by_score(
                data, version.score_scale, threshold,
                a.canonical_name, b.canonical_name,
            )
            score_str = f"{norm_score:.0%}" if norm_score is not None else "?"
            if norm_score is None:
                no_score += 1
        else:
            confirmed = bool(data.get("same_entity"))
            score_str = "yes" if confirmed else "no"

        # Tally
        if confirmed and expected:
            tp += 1; label = "TP OK"
        elif confirmed and not expected:
            fp += 1; label = "FP !!"
        elif not confirmed and expected:
            fn += 1; label = "FN !!"
        else:
            tn += 1; label = "TN OK"

        reasoning = data.get("reasoning", "")[:50]
        print(f"{i+1:>2} {score_str:>6} {label:>8} | "
              f"{a.canonical_name[:30]:<30} <-> {b.canonical_name[:30]:<30} | {reasoning}")

    # Metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    print("\n" + "=" * 60)
    print(f"TP={tp}  FP={fp}  TN={tn}  FN={fn}  (no_score={no_score})")
    print(f"Precision: {precision:.1%}  Recall: {recall:.1%}  F1: {f1:.1%}")

    if hasattr(provider, "get_usage"):
        usage = provider.get_usage()
        print(f"Cost: ${usage['total_cost']:.4f} ({usage['total_tokens']} tokens)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version",   default="v5-score-pct",  help="Confirm version name")
    parser.add_argument("--model",     default="mistral-nemo",  help="LLM model")
    parser.add_argument("--provider",  default="openrouter",    help="ollama or openrouter")
    parser.add_argument("--threshold", default=0.7, type=float, help="Score threshold (0-1)")
    args = parser.parse_args()
    run_benchmark(args.version, args.model, args.provider, args.threshold)
