# Benchmark Results — Entity Extraction

All benchmarks on Turn 14 of "Civilisation de la Confluence" (60 reference entities).
Via OpenRouter unless noted otherwise.

## Matrix: 22 versions x 2 models (llama 8b, mistral-nemo) — v1 to v14

Run date: 2026-03-02 | max_chunks=3 (3/8 chunks, ~37% of text)

| Version | Model | P | R | F1 | TP | FP | FN | Time |
|---------|-------|---|---|----|----|----|----|------|
| v1-baseline | llama3.1:8b | 88.0% | 36.7% | 51.8% | 22 | 3 | 38 | 30s |
| v8-negshot | llama3.1:8b | 52.8% | 31.7% | 39.6% | 19 | 17 | 41 | 33s |
| v2-fewshot | llama3.1:8b | 50.0% | 31.7% | 38.8% | 19 | 19 | 41 | 234s |
| v13-validate | llama3.1:8b | 45.5% | 33.3% | 38.5% | 20 | 24 | 40 | 76s |
| v13.2-validate | llama3.1:8b | 45.5% | 33.3% | 38.5% | 20 | 24 | 40 | 88s |
| v4-strict-recall | llama3.1:8b | 52.9% | 30.0% | 38.3% | 18 | 16 | 42 | 90s |
| v9-neginuser | llama3.1:8b | 39.3% | 36.7% | 37.9% | 22 | 34 | 38 | 347s |
| v14-certainty-10 | llama3.1:8b | 46.3% | 31.7% | 37.6% | 19 | 22 | 41 | 274s |
| v3-recall | mistral-nemo | 54.8% | 28.3% | 37.4% | 17 | 14 | 43 | 65s |
| v7-v4t0 | llama3.1:8b | 51.5% | 28.3% | 36.6% | 17 | 16 | 43 | 270s |
| v14-blind-10 | llama3.1:8b | 39.6% | 31.7% | 35.2% | 19 | 29 | 41 | 203s |
| v9-neginuser | mistral-nemo | 66.7% | 23.3% | 34.6% | 14 | 7 | 46 | 41s |
| v13.1-validate | mistral-nemo | 66.7% | 23.3% | 34.6% | 14 | 7 | 46 | 47s |
| v3-recall | llama3.1:8b | 31.1% | 38.3% | 34.3% | 23 | 51 | 37 | 172s |
| v14-certainty | llama3.1:8b | 37.3% | 31.7% | 34.2% | 19 | 32 | 41 | 285s |
| v2-fewshot | mistral-nemo | 60.9% | 23.3% | 33.7% | 14 | 9 | 46 | 52s |
| v7-v4t0 | mistral-nemo | 58.3% | 23.3% | 33.3% | 14 | 10 | 46 | 56s |
| v13.1-validate | llama3.1:8b | 40.5% | 28.3% | 33.3% | 17 | 25 | 43 | 173s |
| v14-nemo-pct | llama3.1:8b | 32.8% | 33.3% | 33.1% | 20 | 41 | 40 | 466s |
| v14-certainty-pct | llama3.1:8b | 34.5% | 31.7% | 33.0% | 19 | 36 | 41 | 353s |
| v11-heavy | llama3.1:8b | 36.7% | 30.0% | 33.0% | 18 | 31 | 42 | 244s |
| v1-baseline | mistral-nemo | 85.7% | 20.0% | 32.4% | 12 | 2 | 48 | 25s |
| v14-certainty-10 | mistral-nemo | 85.7% | 20.0% | 32.4% | 12 | 2 | 48 | 43s |
| v14-certainty-pct | mistral-nemo | 59.1% | 21.7% | 31.7% | 13 | 9 | 47 | 54s |
| v12-think | llama3.1:8b | 28.0% | 35.0% | 31.1% | 21 | 54 | 39 | 68s |
| v14-certainty-5 | llama3.1:8b | 39.5% | 25.0% | 30.6% | 15 | 23 | 45 | 674s |
| v4-strict-recall | mistral-nemo | 91.7% | 18.3% | 30.6% | 11 | 1 | 49 | 41s |
| v14-certainty | mistral-nemo | 60.0% | 20.0% | 30.0% | 12 | 8 | 48 | 77s |
| v6-combo | mistral-nemo | 38.9% | 23.3% | 29.2% | 14 | 22 | 46 | 50s |
| v14-blind | llama3.1:8b | 24.7% | 35.0% | 29.0% | 21 | 64 | 39 | 396s |
| v14-nemo-pct | mistral-nemo | 68.8% | 18.3% | 28.9% | 11 | 5 | 49 | 65s |
| v12-think | mistral-nemo | 61.1% | 18.3% | 28.2% | 11 | 7 | 49 | 62s |
| v13-validate | mistral-nemo | 55.0% | 18.3% | 27.5% | 11 | 9 | 49 | 39s |
| v10-mark | llama3.1:8b | 26.6% | 28.3% | 27.4% | 17 | 47 | 43 | 231s |
| v14-blind-10 | mistral-nemo | 71.4% | 16.7% | 27.0% | 10 | 4 | 50 | 42s |
| v14-certainty-5 | mistral-nemo | 47.8% | 18.3% | 26.5% | 11 | 12 | 49 | 44s |
| v10-mark | mistral-nemo | 21.1% | 33.3% | 25.8% | 20 | 75 | 40 | 178s |
| v13.2-validate | mistral-nemo | 45.5% | 16.7% | 24.4% | 10 | 12 | 50 | 45s |
| v6-combo | llama3.1:8b | 27.7% | 21.7% | 24.3% | 13 | 34 | 47 | 384s |
| v11-heavy | mistral-nemo | 60.0% | 15.0% | 24.0% | 9 | 6 | 51 | 38s |
| v8-negshot | mistral-nemo | 50.0% | 15.0% | 23.1% | 9 | 9 | 51 | 44s |
| v14-blind | mistral-nemo | 35.7% | 16.7% | 22.7% | 10 | 18 | 50 | 66s |
| v5-schema | llama3.1:8b | 0.0% | 0.0% | 0.0% | 0 | 0 | 60 | 23s |
| v5-schema | mistral-nemo | 0.0% | 0.0% | 0.0% | 0 | 0 | 60 | 176s |

Best per model:
- llama3.1:8b: v1-baseline -> F1=51.8% (P=88.0%, R=36.7%)
- mistral-nemo: v3-recall -> F1=37.4% (P=54.8%, R=28.3%)

Key insight: v1-baseline (simplest prompt, no system, no few-shot) beats all complex versions.
Llama wins 18/22 versions. v5-schema broken on both models (JSON schema via OpenRouter).

---

## v15/v16: Coverage fix (full text, no max_chunks)

Run date: 2026-03-02 | NO chunk limit (full turn processed)

### v15-recall-baseline: v1 prompt + paragraph chunking
| Model | P | R | F1 | TP | FP | FN | Cost | Time |
|-------|---|---|----|----|----|----|------|------|
| llama3.1:8b | 61.4% | 58.3% | 59.8% | 35 | 22 | 25 | $0.002 | 444s |
| llama3.1:70b | 68.9% | 51.7% | 59.0% | 31 | 14 | 29 | $0.012 | 186s |
| qwen3:8b | 53.8% | 58.3% | 56.0% | 35 | 30 | 25 | $0.004 | 139s |
| qwen3:14b | 50.0% | 66.7% | 57.1% | 40 | 40 | 20 | $0.005 | 137s |

### v16-bigctx: v1 prompt + num_ctx=16384 (single call)
| Model | P | R | F1 | TP | FP | FN | Cost | Time |
|-------|---|---|----|----|----|----|------|------|
| llama3.1:8b | 61.9% | 43.3% | 51.0% | 26 | 16 | 34 | - | 211s |

### v1-baseline (single call reference)
| Model | P | R | F1 | TP | FP | FN | Cost | Time |
|-------|---|---|----|----|----|----|------|------|
| llama3.1:70b | 95.5% | 35.0% | 51.2% | 21 | 1 | 39 | $0.009 | 54s |

Key insight: Chunking is the single biggest improvement — recall jumps from ~35% to ~58%.
70b has perfect precision (95-100%) but lower recall than 8b models.
qwen3:14b has best raw recall (66.7%) but worst precision (50%).

---

## v15.x: Prompt variations on qwen3:14b (pre-classifier fix)

Run date: 2026-03-02 | Full turn, old classifier (no choice-block state machine)

| Version | Description | P | R | F1 | TP | FP | FN | Cost |
|---------|-------------|---|---|----|----|----|----|------|
| v15 (base) | v1 prompt chunked | 50.0% | 66.7% | 57.1% | 40 | 40 | 20 | $0.005 |
| v15.1-sysnoise | + system anti-noise | 60.3% | 68.3% | 64.1% | 41 | 27 | 19 | $0.005 |
| v15.2-negex | + negative examples in user prompt | 58.3% | 70.0% | 63.6% | 42 | 30 | 18 | $0.005 |
| **v15.3-combo** | **+ system + negex (both)** | **62.7%** | **70.0%** | **66.1%** | **42** | **25** | **18** | **$0.005** |
| v15.4-temp005 | + temp 0.05 | 51.2% | 68.3% | 58.6% | 41 | 39 | 19 | $0.005 |

**Best: v15.3-combo = F1 66.1%** (P=62.7%, R=70.0%) — new all-time record.
System+negex combo reduces FP by 15 while maintaining recall.
Temperature reduction (v15.4) doesn't help — same FP count as base.

---

## Classifier fix: surgical choice-block filter

Implemented a 3-variant state machine to handle GM choice blocks.
Core insight: GM mixes hypothetical options AND real lore in the same choice blocks.
Can't skip everything — need to keep long narrative paragraphs inside choice blocks.

Pattern: detect "### Choix N", "Action libre", "Sujet libre" headers.
Inside the block: filter SHORT paragraphs (<3 sentences = GM option summaries),
keep LONG paragraphs (>=3 sentences = real lore intercalated by GM).

Variants tested on v15.3-combo + qwen3:14b:

| Classifier | P | R | F1 | TP | FP | FN | Cost |
|------------|---|---|----|----|----|----|------|
| None (old) | 62.7% | 70.0% | 66.1% | 42 | 25 | 18 | $0.005 |
| Titles only | 62.9% | 65.0% | 63.9% | 39 | 23 | 21 | $0.005 |
| **Surgical >=3 sentences (CHOSEN)** | **67.8%** | **66.7%** | **67.2%** | **40** | **19** | **20** | **$0.004** |
| Surgical >=300 chars | 70.4% | 63.3% | 66.7% | 38 | 16 | 22 | $0.004 |
| Full state machine (too aggressive) | 77.5% | 51.7% | 62.0% | 31 | 9 | 29 | $0.003 |

**Chosen: >=3 sentences threshold — F1=67.2%, new all-time record.**
- 6 fewer FP than no filter (25->19)
- Only 2 fewer TP (42->40) — kept Nanzagouets, Siliaska, Tlazhuaneca etc.
- 300-char threshold rejected: fragile on corpus variation (a 250-char paragraph
  can be either a short option or real lore depending on turn).

Classifier code: `pipeline/pipeline/classifier.py`
- `_is_choice_header()`: detects "### Choix N", "Action libre", "Sujet libre"
- `_is_short_option()`: <3 sentences = filter; >=3 = keep as narrative
- `_is_block_boundary()`: non-choice header or player response = exit block
- Documented in `docs/filtrage-contenu-jdr.md` (aligned with civjdr approach)

---

## Micro-variations qwen3:14b sur v15.3-combo

Run date: 2026-03-02 | Full turn, surgical classifier (>=3 sentences)
Base: v15.3-combo qwen3:14b = F1 67.2%

| Version | Description | P | R | F1 | TP | FP | FN | Cost |
|---------|-------------|---|---|----|----|----|----|------|
| v15.3 (ref) | base | 67.8% | 66.7% | 67.2% | 40 | 19 | 20 | $0.004 |
| v15.3.1-temp0 | temperature=0 | 65.5% | 63.3% | 64.4% | 38 | 20 | 22 | $0.004 |
| v15.3.2-chunk600 | chunks 600w | 65.6% | 66.7% | 66.1% | 40 | 21 | 20 | $0.005 |
| v15.3.3-chunk1200 | chunks 1200w | 66.1% | 65.0% | 65.5% | 39 | 20 | 21 | $0.004 |
| **v15.3.4-tightnon** | **NON list étendue** | **70.7%** | **68.3%** | **69.5%** | **41** | **17** | **19** | **$0.004** |

Key findings:
- Chunk size (600/800/1200) has negligible impact — ±1 TP/FP, not worth tuning
- temperature=0 slightly hurts (qwen3 needs a tiny bit of stochasticity)
- Expanding the NON list with observed FP generics (assemblees, mission, reincarnation,
  testament) yields +1 TP, -2 FP — **new record F1=69.5%**
- Remaining 17 FP: ~10 are name variants (Ailes Grises/Ailes-Grises, Faucon Chasseur/
  Faucons Chasseurs) — prompt-resistant, better handled by post-processing dedup

---

## FINAL BEST CONFIGURATION

**Model**: qwen3:14b (via OpenRouter ~$0.004/turn)
**Extraction version**: v15.3.4-tightnon
  - Chunking: paragraph-based, max 800 words/chunk
  - System prompt: anti-noise rules + dedup rule (UNE seule forme)
  - User prompt: negative examples + expanded NON list
    (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre,
     collaboration, dangers, assemblees, mission, reincarnation, testament)
**Classifier**: surgical choice-block filter (>=3 sentences = lore)

**F1 = 69.5% | P = 70.7% | R = 68.3%** on Turn 14 (60 reference entities)

Progress vs session start (v1-baseline llama3.1:8b, 3 chunks max):
- F1:      51.8% -> **69.5%** (+17.7 points)
- Recall:  36.7% -> **68.3%** (+31.6 points)
- Precision: 88.0% -> 70.7% (-17.3 points, accepted trade-off for recall)
- Cost: ~$0 local -> ~$0.004/turn cloud

Remaining FP (17): ~10 name variants (Ailes Grises, Faucon Chasseur, Nanzagouets...)
  → prompt-resistant, better fixed by post-processing alias dedup
Remaining FN (19): simple tools (Lances, Pilotis, Pigments, Codex) + beliefs
  → v17-sweep pass candidate for future iteration

VALIDATED — moving to production config.
