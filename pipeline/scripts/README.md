# Pipeline Scripts

Benchmark, scoring and profiling utilities for the Aurelm ML pipeline.
These are **standalone scripts** (not part of the pipeline itself) — run them manually for evaluation and tuning.

## Benchmarks

### `benchmark.py`
Entity extraction benchmark on selected turns. Runs extraction with a specific version/model, scores against `pipeline/data/reference_entities.json`.

```bash
cd pipeline && py -3.12 scripts/benchmark.py --db aurelm_test.db --turn last --version v22.2.1-pastlevel --llm-config pipeline_llm_config.json
```

### `benchmark_matrix.py`
Batch comparison: all extraction versions x selected models (via OpenRouter) on a single turn. Produces a P/R/F1 summary table.

```bash
cd pipeline && py -3.12 scripts/benchmark_matrix.py --db aurelm_test.db --turn 14
```

### `benchmark_aliases.py`
Alias confirmation prompt benchmark. Tests different `confirm_version` prompts on a 30-pair test set, reports P/R/F1.

```bash
cd pipeline && py -3.12 scripts/benchmark_aliases.py --db aurelm_fullrun.db
```

### `benchmark_validate.py`
Validate prompt benchmark. Loads raw entities from `pipeline_llm_calls`, tests each VALIDATE_VERSIONS prompt against T01-T08 reference ground truth.

```bash
cd pipeline && py -3.12 scripts/benchmark_validate.py --db aurelm_fullrun.db
```

## Scoring

### `score_t1_t8.py`
Per-turn and global P/R/F1 scores for T01-T08 against `pipeline/data/reference_turns_t1_t8.json`. Fuzzy, accent-insensitive matching.

```bash
cd pipeline && py -3.12 scripts/score_t1_t8.py --db aurelm_fullrun.db
```

### `score_t11.py`
Same as above but for T11 only, against `pipeline/data/reference_turn11.json`. Includes per-entity TP/FP/FN details in verbose mode.

```bash
cd pipeline && py -3.12 scripts/score_t11.py --db aurelm_fullrun.db -v
```

## Testing

### `test_t1_t8.py`
Full pipeline integration test on a turn range (e.g., T01-T03). Runs all 10 stages, shows per-turn extraction funnel (raw -> dedup -> final), lookup growth, entity distribution.

```bash
cd pipeline && py -3.12 scripts/test_t1_t8.py --turns 1-3 --version v22.2.1-pastlevel --llm-config pipeline_llm_config.json
```

## Profiling

### `run_profiler.py`
Profiles all entities missing descriptions/tags from a given DB. Uses OpenRouter provider.

```bash
cd pipeline && py -3.12 scripts/run_profiler.py --db aurelm_fullrun.db --llm-config pipeline_llm_config.json
```

## When to use what

| Situation | Script |
|---|---|
| Changed extraction prompts | `benchmark.py` or `benchmark_matrix.py` |
| Changed validate prompts | `benchmark_validate.py` |
| Changed alias confirmation | `benchmark_aliases.py` |
| Quick quality check after full run | `score_t1_t8.py` |
| Full integration test on N turns | `test_t1_t8.py` |
| Entities missing descriptions | `run_profiler.py` |
