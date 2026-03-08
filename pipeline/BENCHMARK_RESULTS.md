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

---

## Alias Confirmation — Prompt Benchmark

**Task**: Stage 2 LLM scoring — confirm/reject alias candidate pairs.
**Test set**: 30 pairs (8 TP, 22 TN), manually verified, `pipeline/data/alias_test_set.json`.
**Model**: `qwen/qwen3-14b` via OpenRouter (all results below).
**Threshold**: 0.7 (score ≥ 70% = confirmed alias).
**Cost**: ~$0.009/30 pairs (~$0.034/113 production candidates).

### Iteration history

| Version | P | R | F1 | TP | FP | FN | Key change |
|---------|---|---|----|----|----|----|------------|
| v6-jdr-context (Nemo) | 40.0% | 100% | 57.1% | 8 | 12 | 0 | Baseline — JDR context, recall=100% but 12 FPs |
| v11-desc-first | 77.8% | 87.5% | 82.4% | 7 | 2 | 1 | Breakthrough — descriptions first, Qwen3 |
| **v12-desc-first-tuned** | **77.8%** | **87.5%** | **82.4%** | **7** | **2** | **1** | **+3 incompatibility rules (Gardiens, lieu précis, lieu physique)** |
| v13-incomp-override | 80.0% | 80.0% | 80.0% | 8 | 2 | 2 | ALL rules override descriptions → regression pair 17 |
| v14-surgical | 77.8% | 80.0% | 78.8% | 8 | 2 | 2 | VETO 0 with 2 override rules → regression pair 1 |
| v15-explicit-examples | 83.3% | 62.5% | 71.4% | 5 | 1 | 3 | "prime sur les descriptions" + broader Gardiens → overfired |
| v16-minimal-examples | 77.8% | 87.5% | 82.4% | 7 | 2 | 1 | Same F1 as v12, different FP distribution |

### FINAL BEST CONFIGURATION

**Version**: `v12-desc-first-tuned`
**Model**: `qwen3:14b` (Ollama local) / `qwen/qwen3-14b` (OpenRouter)
**F1 = 82.4% | P = 77.8% | R = 87.5%** on 30-pair test set

Config: `pipeline_llm_config.example.json`
```json
"aliases": { "model": "qwen3:14b", "prompt_version": "v12-desc-first-tuned", "score_threshold": 0.7 }
```

### Key findings

- **Descriptions-first is critical** (v11 breakthrough): Qwen3 must read descriptions before
  checking name incompatibilities — reversing order shifts priors and breaks borderline TPs.
- **F1=82.4% is the prompt ceiling**: pairs 15/21/7/26 fluctuate ±10% between versions
  due to LLM temperature — fixing one set of FPs introduces another.
- **Remaining FN (pair 16)**: Peuple du ciel clair / Ciels-clairs — data quality issue,
  descriptions too different in DB regardless of prompt.
- **FPs in v12** (2): Confluence de deux rivières/Rivières cristallines (90%), Gardiens/Confluence des Esprits (75%).

### Decision: human review before DB write

FPs are structurally harmful (entity merge = wiki confusion). Solution: display confirmed
alias list with scores to Arthur before writing to DB — 30-second review, eliminates FP risk.
To implement: add `--dry-run` / interactive confirmation step in `runner.py` alias stage.

---

## Full-corpus benchmark — new civjdr layout (19 turns)

**Context**: civjdr migrated from mixed files (old) to split mj-T##/pj-T## pairs per turn (new).
Loader updated (`loader.py`) to auto-detect new layout, load only MJ files, insert synthetic
player placeholder before each. Benchmark updated: `--turn all` + `is_gm_post` filter.

**Run date**: 2026-03-03 | Model: qwen3:14b via OpenRouter | 19 turns | 12,518 words total
**Reference**: `data/reference_turn14.json` (60 entities, full-corpus ground truth)

### v15.3.4-tightnon vs v17-typerecall

| Version | Description | P | R | F1 | TP | FP | FN | Cost |
|---------|-------------|---|---|----|----|----|----|------|
| **v15.3.4-tightnon** | Current production | **46.0%** | **64.5%** | **53.7%** | **69** | **81** | **38** | $0.0091 |
| v17-typerecall | + permissive tech rules | 38.6% | 68.2% | 49.3% | 73 | 116 | 34 | $0.0100 |

**Winner: v15.3.4-tightnon stays production.** v17 is a regression.

### v17-typerecall analysis (regression)

Changes in v17 vs v15.3.4:
- `entity_filter.py`: removed lance/lances/codex/palanquin/palanquins/fresque/fresques from noise ✓
- System prompt: added permissive rule "simple tools = technologies when they have a key role"
- Result: +4 TPs (Lances T6, Sans-Ciel T5, Pèlerinage T15, Croyance en la réincarnation T18)
- But +35 FPs: LLM extracts generic ad-hoc tools (Pioches, Ciseaux à Pierre, Gourdins, Bol in T14)
  and hallucinates known technologies in early turns where they aren't introduced yet.

Root cause: "simple tools with key role" rule can't distinguish named technologies (Lances = the
civ's signature weapon) from ad-hoc tools (Pioches = mining tools used once). Context is required,
but LLM applies the rule to all turns including early ones where Lances haven't been introduced.

### entity_filter.py fix (kept regardless of v17 regression)

`lance/lances/codex/palanquin/palanquins/fresque/fresques` removed from `_GENERIC_FRENCH_NOUNS`.
These are confirmed named technologies in the reference. Language-level filtering was incorrect.
The fix is neutral for v15.3.4 (doesn't extract these in most turns anyway) but prevents future
false negatives if extraction improves.

### New baseline (old 69.5% not comparable — different corpus structure)

Old F1=69.5% was measured on a single large "old Turn 14" chunk (multiple GM posts combined).
New F1=53.7% is the correct full-corpus baseline on 19 individual turn files (new layout).
The corpus scope increased: 19 turns, 12,518 words vs ~900-word single turn.

**Production config unchanged: v15.3.4-tightnon + qwen3:14b.**

---

## Turn 11 deep-dive — pj file discovery + v18 iteration

**Context**: Turn 11 MJ+PJ files loaded together (loader.py fix). Reference: `data/reference_turn11.json` (26 entities).
**Run date**: 2026-03-03 | Model: qwen/qwen3-14b via OpenRouter | Text: 1,844 words

### Key fix: loader.py — load PJ files

PJ files contain major lore (institutions, governance, technologies) introduced by the player.
Without PJ: 817 words, 6 TPs. With PJ: 1,844 words, 20 TPs. F1: 48% → 71.4%.

### entity_filter.py fixes

- `lance/lances` etc. already removed in previous session
- Word-count threshold: `> 5` → `> 6` to allow 6-word compound tech names ("Ciseaux de bois au dents d'obsidienne")
- Accent normalization in dedup key: `_dedup_key()` strips accents so focus call (no accents) doesn't produce doublons vs main calls

### v18 iteration results (all qwen3:14b, same T11 corpus)

| Version | Calls | P | R | F1 | FPs | FNs | Cost | Key change |
|---------|-------|---|---|----|----|-----|------|------------|
| v15.3.4 (prod) | 2 | 62.5% | 76.9% | 69.0% | 12 | 6 | $0.0016 | baseline |
| v18-toolrecall | 2 | 69.0% | 76.9% | 72.7% | 9 | 6 | $0.0016 | tool OUI examples, compound name rule, zone NON |
| v18.1-validate | 3 | 85.0% | 65.4% | 73.9% | 3 | 9 | $0.0018 | + validate pass (qwen3:14b) — over-filters castes |
| v18.2-mark | 3 | 80.0% | 76.9% | 78.4% | 5 | 6 | $0.0033 | + GPT-NER mark pass — eliminates Zone X FPs |
| v18.3-focus (before dedup fix) | 3 | 60.0% | 92.3% | 72.7% | 16 | 2 | $0.0022 | + caste/institution focus call — doublon bug |
| v18.3-focus (after dedup fix) | 3 | 66.7% | 92.3% | 77.4% | 12 | 2 | $0.0022 | accent dedup fix: 16→12 FPs |
| **v18.4-combo** | **4** | **95.5%** | **80.8%** | **87.5%** | **1** | **5** | **$0.0023** | **focus(qwen3:14b) + validate(llama3.1:8b)** |

### v18.4-combo analysis

Best single-turn result: F1=87.5%, P=95.5%, 1 FP only ("Premier bâtiment").
Validate pass: 30 → 22 entities (killed 8 FPs + 2 TPs — over-filtering castes).

Remaining FNs (5): Tailleurs de pierre, Explorateurs (killed by validate), Rhombes (missed in dense text),
Confluence (place, lowercase in text), Voix de l'Aurore (killed by validate).

Root cause: Llama 3.1 8B validate pass removes castes it perceives as "generic workers".
Fix target: v18.4.1 (protect castes in validate prompt) + v18.4.2 (Nemo instead of Llama).

### v18.4.x tweaks

| Version | Calls | P | R | F1 | Vrais FPs* | FNs | validate_model | Cost |
|---------|-------|---|---|----|----|-----|----------------|------|
| v18.4-combo | 4 | 95.5% | 80.8% | 87.5% | 1 | 5 | llama3.1:8b | $0.0023 |
| v18.4.1-protectcaste | 4 | 67.6% | 88.5% | 76.7% | ~7 | 3 | llama3.1:8b | $0.0023 |
| **v18.4.2-nemo** | **4** | **82.8%** | **92.3%** | **87.3%** | **1** | **2** | **mistral-nemo** | **$0.0023** |

\* Doublons (Passes-bien/Passe-bien, Rhombes miniatures/Rhombes, Argile Vivante/Argile vive,
  Ailes-Grises/Fiers ailes grises) comptés comme FPs dans le benchmark mais mergés par l'alias
  resolver en production → 1 vrai FP residuel ("Premier bâtiment").

**Winner: v18.4.2-nemo** — F1=87.3%, R=92.3%, 2 vrais FNs (Voix de l'Aurore, Confluence).

Key finding: **Nemo > Llama pour le validate en français.**
- Llama v18.4 : trop agressif → retire castes (30→22, kill Tailleurs/Explorateurs/Voix de l'Aurore)
- Llama v18.4.1 : trop mou avec le nouveau prompt → retire quasi rien (35→34), garde Zone X
- Nemo v18.4.2 : équilibré → retire Zone X/Foyer/métaphores sans tuer les castes (36→29)

Remaining FNs (2):
- `Voix de l'Aurore` : mention en lowercase "voix de l'Aurore" dans un item de liste à puces — hors radar du focus call
- `Confluence` (place) : jamais capitalisé dans le texte — LLM ne le reconnaît pas comme nom propre

### Architecture v18.4.2-nemo (4 calls)

```
Per chunk:
  Call 1: facts+entities (qwen3:14b) — facts JSON + entités générales
  Call 2: entities-only (qwen3:14b) — filet de sécurité entités
  Call 3: focus caste/institution/tech (qwen3:14b) — castes et institutions ciblées + Rhombes

Post-dedup (accent-normalized):
  Call 4: validate (mistral-nemo) — retire sections de bâtiment, métaphores, doublons évidents

Dedup: normalisé accents → évite doublon "Assemblee des Chefs" / "Assemblée des Chefs"
```

## Full Corpus Benchmark — v18.4.2-nemo vs baseline

Run date: 2026-03-03 | 19 turns (T1–T19) | Reference: reference_entities.json (101 global entities, filtered per turn via filter_reference_by_text)

| Version | P | R | F1 | Cost |
|---------|---|---|----|------|
| v15.3.4-tightnon (baseline) | — | — | 53.7% | — |
| **v18.4.2-nemo** | **53.6%** | **64.7%** | **58.6%** | $0.024 |

**Gain over baseline: +4.9% F1** (53.7% → 58.6%)

### Per-turn breakdown

| Turn | P | R | F1 | Words | Ref | Notes |
|------|---|---|----|-------|-----|-------|
| T1  | 0%    | 0%    | 0%    | 318   | 2   | "Blanc sur Blanc", "Premier Âge" — très tôt, quasi rien en ref |
| T2  | 25%   | 33%   | 28.6% | 473   | 3   | Gourdins TP, Confluence FN |
| T3  | 100%  | 33%   | 50.0% | 627   | 3   | Arbitre des Esprits + Confluence FN |
| T4  | 75%   | 75%   | 75.0% | 705   | 8   | Best early-turn result |
| T5  | 23%   | 43%   | 30.0% | 783   | 7   | Beaucoup de FPs génériques (Tribu, Famille, Rhombes miniatures) |
| T6  | 41%   | 64%   | 50.0% | 896   | 14  | 9 TPs, FPs sur Filet/Casiers/Herbes/Baies |
| T7  | 75%   | 82%   | 78.3% | 442   | 11  | Fort, Gardiens de la Confluence récupéré |
| T8  | 50%   | 70%   | 58.3% | 637   | 10  | Doublons (Rhombes/Rhombe/Rhombes miniatures) |
| T9  | 43%   | 75%   | 54.5% | 1530  | 16  | 12 TPs, 16 FPs dont beaucoup de sous-variantes Ciels |
| T10 | 45%   | 50%   | 47.4% | 1964  | 18  | Lait de Pierre, Roche Braise, Confluents FN |
| T11 | 55%   | 55%   | 54.5% | 1844  | 22  | Zones chaude/froide/humide/sèche en FN (ref globale les inclut) |
| T12 | 83%   | 83%   | 83.3% | 681   | 12  | Excellent turn |
| T13 | 50%   | 41%   | 45.2% | 1258  | 17  | Appel de l'Abysse + 6 autres FN |
| T14 | 30%   | 33%   | 31.6% | 1198  | 9   | 6 technologies manquées (Grande Fresque, Maîtrise Profondeurs...) |
| T15 | 47%   | 69%   | 56.2% | 2031  | 13  | Foyer du Savoir FN |
| T16 | 61%   | 74%   | 66.7% | 2483  | 34  | Meilleure turn longue — 25 TPs |
| T17 | 84%   | 80%   | 82.1% | 1706  | 20  | Très fort, Nanzagouet/Tlazhuaneca bien capturés |
| T18 | 61%   | 85%   | 71.0% | 910   | 13  | Fort, Cornex récupéré |
| T19 | —     | —     | —     | 2     | 0   | Tour vide (2 mots), ignoré |

### Key findings — full corpus

**Patterns FP récurrents :**
1. **Doublons de casse/accents** : "Rhombes"/"Rhombes miniatures"/"Rhombe", "Ailes-Grises"/"Aile-grise" — alias resolver en prod
2. **Entités génériques** : "Tribu", "Villages", "Famille", "Artefacts", "Ordres" — entity_filter insuffisant
3. **Events/lieux confondus** : "Fresques Anciennes", "Sauvetage des équipes", "Exploration" extraits comme entités
4. **Sous-entités Ciels** : "Ciels-clairs", "Ciels-libres", "Ciels libres", "Enfants du ciel" — prolifération de variantes

**Patterns FN récurrents :**
1. **"Confluence" [place]** : jamais capitalisé dans le texte, invisible au LLM (FN dans T2, T3, T7, T8, T9, T10, T11, T13)
2. **Technologies ancien texte** : Lances, Pilotis, Pieux, Passerelles — LLM les voit comme objets génériques
3. **Technologies T14** : Grande Fresque, Maîtrise des Profondeurs, Artefacts translucides, Pigments, Techniques de creusage

**Note**: Le score T11 avec ref globale (F1=54.5%) est très différent du score T11 avec ref T11 (F1=87.3%).
La ref T11 ne contient que 26 entités "saillantes" ; la ref globale inclut 22 entités dont Zones/Lances/Confluents
qui sont réellement présentes dans le texte mais peu saillantes — score plus conservateur mais plus honnête.

**Winner confirmation**: v18.4.2-nemo reste le meilleur sur le full corpus (+4.9% vs baseline).

---

## v21.x — Masked-pass variants (T1-T8, ref=42 entités)

Run date: 2026-03-07 | OpenRouter | qwen3:14b sauf mention contraire | ref T1-T8 = 42 entités
Baseline : v21.0-masked (F1=67.5%, P=73.0%, R=62.8%, TP=27, FP=10, FN=16, cost=$0.022)

| Version | Description | F1 | P | R | TP | FP | FN | Cost | Entity calls |
|---------|-------------|-----|---|---|----|----|-----|------|------|
| **v21.0-masked** | baseline — 1 passe masquée, prompt normal, qwen3:14b | **67.5%** | 73.0% | 62.8% | 27 | 10 | 16 | $0.022 | 14 (8+6) |
| v21.1-masked-triple | 2 passes masquées (triple total), prompt normal, qwen3:14b | 57.9% | 50.8% | 67.4% | 31 | 30 | 15 | $0.027 | 20 (8+12) |
| v21.2-masked-prompt | 1 passe masquée, prompt ciblé, qwen3:14b | 55.8% | 48.3% | 65.9% | 29 | 31 | 15 | $0.026 | 14 (8+6) |
| v21.3-masked-llm | 1 passe masquée, prompt normal, qwen3.5-35b-a3b | 64.2% | 72.2% | 57.8% | 26 | 10 | 19 | $0.023 | 14 (8+6) |
| v21.4-masked-both | 1 passe masquée, prompt ciblé, qwen3.5-35b-a3b | 67.5% | 73.7% | 62.2% | 28 | 10 | 17 | $0.023 | 14 (8+6) |
| v21.5-scoped | 2 passes scopées (pass0=tech/belief, pass1=person/place), qwen3:14b | 46.6% | 35.6% | 67.4% | 31 | 56 | 15 | $0.054 | 20 (8+12) |
| v21.6-llama | 2 passes masquées, meta-llama/llama-3.1-8b-instruct | 48.2% | 36.3% | 71.7% | 33 | 58 | 13 | $0.034 | 20 (8+12) |
| v21.7-radical | 1 passe "catalogue anthropologue", prompt radical, qwen3:14b | 55.6% | 48.4% | 65.2% | 30 | 32 | 16 | $0.029 | 15 (8+7) |
| v21.8-radical-filtered | v21.7 + N'EXTRAIS PAS abstractions/émotions | 51.4% | 44.4% | 60.9% | 28 | 35 | 18 | $0.027 | 14 (8+6) |
| v21.9-radical-protected | v21.8 + validate GARDE TOUJOURS outils + 1024 tokens | 47.2% | 41.7% | 54.3% | 25 | 35 | 21 | $0.028 | 14 (8+6) |

### v21.1 — Triple passe : +recall mais +30 FPs

**F1=57.9%** (-9.6pp vs baseline). Recall monte à 67.4% (+4.6pp), mais la précision s'effondre à 50.8% (-22.2pp).
La 2e passe masquée génère massivement des génériques que le validate ne peut pas absorber (45 entités sur T06 seul) :
FPs : `Baies`, `Herbes`, `Légumes`, `Galette`, `Plante`, `Eau`, `Protection`, `Campements`, `Supports`, `Techniques`
Verdict : **la triple passe est contre-productive** — le validate (qwen3:14b, 512 tokens) est trop court pour filtrer 45 entités.

### v21.2 — Prompt ciblé : `Pipeau en bambou` récupéré, mais +31 FPs

**F1=55.8%** (-11.7pp vs baseline). Le prompt masqué dirige le LLM vers "technologies, ressources naturelles, croyances" — il trouve `Pipeau en bambou` (nouveau TP) et `Mémentos` (fuzzy), mais génère massivement des FPs alimentaires/génériques : `Baies`, `Herbes`, `Galette`, `Tubercules`, `Plumages`, `Feu`, `Gravures`, `Réserves`.
Verdict : **le prompt ciblé donne des signaux trop larges** — "ressources naturelles" = le LLM extrait toute la nourriture. À reformuler pour exclure explicitement les aliments.

### v21.3 — Modèle 35b-a3b sur passe masquée : trop conservateur, n'ajoute rien

**F1=64.2%** (-3.3pp vs baseline). Le `qwen3.5-35b-a3b` retourne systématiquement JSON vide (`{}`, 16 chars) sur le texte masqué — il refuse d'extraire sur un texte truffé de `_____`. La précision reste identique à v21.0 (10 FPs), mais le recall chute car la passe masquée n'apporte rien.
Verdict : **35b-a3b est trop prudent sur texte masqué** — comportement inverse de qwen3:14b (qui hallucine). Le modèle traite les `_____` comme du bruit et préfère ne rien retourner.

### v21.4 — Prompt ciblé + 35b-a3b : égalité avec v21.0

**F1=67.5%** (=baseline). Le 35b-a3b retourne toujours JSON vide sur texte masqué — la passe masquée n'apporte rien, même avec un prompt explicatif. Mais le prompt ciblé dans le contexte de `mask_entity_prompt` fait que qwen3:14b (utilisé pour la validation) est légèrement mieux orienté : `Mémentos` est capturé comme TP direct (+1 TP vs v21.3). FP stables à 10.
Verdict : **aucun gain** par rapport à v21.0 — le 35b-a3b bloque systématiquement sur `_____`.

### v21.5 — Passes scopées : hallucination familiale en "Rêves"

**F1=46.6%** (-20.9pp vs baseline). Recall stable à 67.4% (=v21.1), mais precision effondree à 35.6% — le pire résultat de toute la série v21.

Cause identifiée : la passe "persons/places/institutions" a demandé spécifiquement des institutions — le LLM a inventé une famille entière d'entités inexistantes : `Gardiens des Rêves`, `Ordre des Rêves`, `Marchands des Rêves`, `Porteurs des Rêves`, `Ordre des Rêves Éternels`, `Maison des Rêves`, `Gardiens des Rêves Éternels`, `Rituel des Rêves Éternels`... (8+ FPs rien que sur cette thématique). T06 a produit 56 raw entities → 63 après dedup (vs ~10-12 pour les autres turns) — la passe scopée a amplifié une hallucination en cascade.
Le validate (qwen3:14b, 512 tokens) n'a pas pu absorber 72 entités (56 FPs survivants après validate).

Verdict : **le scopage par type est contre-productif** — quand on demande au LLM de chercher spécifiquement des institutions sur du texte masqué, il en invente plutôt que de ne rien trouver. Le validate ne suffit pas à filtrer un tel volume.

### v21.6 — Llama : recall record (71.7%) mais precision catastrophique

**F1=48.2%** (-19.3pp vs baseline). Recall le plus élevé de toute la série v21 (71.7%, +8.9pp vs v21.0), TP=33 (record absolu), mais precision=36.3% — 58 FPs.

Comportement llama : génère des réponses massives (25 649 chars sur une extraction) et extrait absolutement tout, y compris `Feu`, `Bois`, `Branche`, `Tente`, `Eden`, `Etoiles`, `Cieux`, `Crise`, `Départ`, `Vêtements`, `Échange`. Llama ne fait pas le tri "terme propre à la civilisation" vs "mot courant" — tout ce qui est dans le texte devient une entité.

Nouveaux TPs capturés vs v21.0 : `Roches striées` (TP direct), `Paniers` (fuzzy -> `paniers immergés`), `Mémentos` (TP direct). Mais ces 3 gains sont noyés dans 58 FPs.

Verdict : **llama = filet trop large** — excellente couverture, zéro précision. Potentiellement utile si suivi d'un validate très agressif avec plus de tokens.

### v21.7 — Prompt radical : PREMIERE capture de Gourdins + Pieu

**F1=55.6%** (-11.9pp vs baseline). P=48.4%, R=65.2%, TP=30, FP=32, FN=16.

**Percée majeure** : `Gourdins` et `Pieu` sont capturés en TP direct — une **première absolue** sur toute la série v21. `Pointes de flèches` également (+1 vs v21.0). En revanche, 32 FPs (vs 10 pour v21.0) dont `Corps`, `Esprit`, `Faim`, `Fatigue`, `Naissance`, `Univers`, `Pays`, `Troupeaux d'animaux migrants` — le prompt "catalogue anthropologue" avec `drops proper-noun filter` a élargi le filet trop loin.

Explication : le prompt dit "même si ce terme ressemble à un nom commun français ordinaire" — le LLM applique littéralement en incluant des concepts abstraits (`Mort`, `Faim`, `Choix`) et des termes biologiques (`Poissons`, `Petit animal`). La validate a quand même fait son travail (22 drops sur T06 seul), mais reste insuffisante pour les concepts abstraits.

**Conclusion sur Gourdins/Pieu** : ces termes étaient récupérables — ils apparaissent dans le texte source. Le problème était que le filtre "nom propre capitalisé" les excluait systématiquement. Le prompt anthropologue contourne ce filtre.

Verdict : **potentiel réel**, mais le filtre "spécifique à la civilisation" est trop large. Piste : ajouter une exclusion explicite des concepts abstraits (émotions, états biologiques) dans le prompt.

### v21.8 — N'EXTRAIS PAS abstractions : Gourdins/Pieu tués par le validate

**F1=51.4%** (-16.1pp vs baseline). La liste `N'EXTRAIS PAS` réduit les abstractions de v21.7 (`Corps`, `Faim`, `Univers`...), mais le validate supprime `Gourdins` et `Pieu` comme "Metaphore poetique sans referent concret" — bien que la règle dise déjà "pas un outil". 35 FPs restants dont `Baies`, `Herbes`, `Galette`, `Tubercules`.

Diagnostic : le validate avec 512 tokens + 20+ entités se précipite et applique la règle "Metaphore poetique" aux noms communs qui ressemblent à du vocabulaire ordinaire. Il n'y a pas assez de contexte pour distinguer "outil culturel spécifique" de "mot ordinaire".

Verdict : **extraction fonctionne** (v21.8 masked pass trouve Gourdins/Pieu) — c'est le **validate qui est le verrou**.

### v21.9 — GARDE TOUJOURS outils : sur-compensation vers les beliefs

**F1=47.2%** (-20.3pp vs baseline, pire résultat de la série). Le nouveau validate avec clause "GARDE TOUJOURS outils" + 1024 tokens sur-corrige : maintenant il drope `Oracle`, `Ancêtres`, `Voix des cieux` comme "Metaphore poetique" (3 TPs perdus vs v21.0). Les `Gourdins`/`Pieu` ne sont même pas extraits par la passe masquée cette fois — non-déterminisme LLM. 35 FPs, 21 FNs.

Diagnostic : le validate est un système à zéro-somme — protéger une catégorie (outils) rend le modèle plus agressif sur d'autres (beliefs). Le prompt validate est trop court pour arbitrer finement entre 15+ catégories avec des règles contradictoires.

Verdict : **le validate est le goulot d'étranglement de toute la série v21** — il faut soit l'entraîner sur des exemples (few-shot with edge cases), soit augmenter drastiquement son budget (>2048 tokens avec reasoning explicite par entité).

### Conclusions v21.x

| Axe | Résultat |
|-----|---------|
| Triple passe (v21.1) | Recall +4.6pp mais précision -22.2pp → F1 -9.6pp. Le validate ne peut pas absorber 45 entités. |
| Prompt ciblé (v21.2) | Recall +3.1pp mais précision -24.7pp → F1 -11.7pp. "Ressources naturelles" = explosion de génériques alimentaires. |
| Modèle 35b-a3b (v21.3) | JSON vide sur texte masqué → aucun apport, recall -5pp → F1 -3.3pp. |
| Combo (v21.4) | Même résultat que v21.0 (F1=67.5%) — 35b-a3b reste muet malgré le prompt. |
| Passes scopées (v21.5) | F1=46.6% — hallucination en cascade sur T06. Scopage par type : LLM invente des entités dans le type demandé plutôt que de ne rien trouver. |
| Llama pour passe masquée (v21.6) | F1=48.2%, recall record 71.7% (+8.9pp) mais precision=36.3% — filet trop large, tout devient entité. |
| Prompt radical (v21.7) | F1=55.6%, **Gourdins + Pieu capturés pour la première fois** — drops proper-noun filter fonctionne. Mais 32 FPs (abstractions). |
| N'EXTRAIS PAS abstractions (v21.8) | F1=51.4% — `Gourdins`/`Pieu` trouvés par masked pass puis **tués par validate** ("Metaphore poetique"). |
| GARDE TOUJOURS outils (v21.9) | F1=47.2% — validate protège les outils mais sur-compense : drope `Ancêtres`, `Oracle`, `Voix des cieux`. -5 TPs vs v21.0. |
| **Gagnant final** | **v21.0-masked (F1=67.5%)** — inchangé. La série v21 atteint sa limite. |

**Découverte clé** : `Gourdins`/`Pieu` sont extractibles (v21.7 le prouve), mais le validate les bloque systématiquement comme "generiques". Le vrai verrou est dans le validate, pas dans l'extraction. Fixer le validate pour accepter les noms communs culturellement spécifiques sans casser les entités de type belief/spiritual est un problème d'équilibrage fin.

**FNs persistants** (résistants à toute la série v21) : `techniques de polissage`, `rituels de fertilité`, `radeaux`, `paniers immergés`, `pipeau en bambou`, `culte des ancêtres`. Ces termes sont absents ou sous-représentés dans le texte source — pas récupérables par prompt tuning seul.

---

## Comparaison modèles Qwen — Turn 11 (v18.4.2-nemo, ref T11 = 26 entités)

Run date: 2026-03-04 | OpenRouter | validate_model = mistral-nemo pour tous

| Modèle | F1 | P | R | TP | FP | FN | Coût | Temps | Notes |
|--------|-----|---|---|----|----|-----|------|-------|-------|
| qwen/qwen3-14b | 85.0% | 81.0% | 89.5% | 17 | 4 | 2 | $0.0009 | 25s | Baseline prod — meilleur ratio qualité/prix |
| qwen/qwen3.5-35b-a3b | **88.9%** | **94.1%** | 84.2% | 16 | 1 | 3 | $0.0024 | 28s | Meilleur F1, quasi-zéro bruit (1 FP) |
| qwen/qwen3.5-27b | 81.0% | 73.9% | 89.5% | 17 | 6 | 2 | $0.0068 | 43s | Dense 27B — pire des 3, beaucoup de FPs |
| qwen/qwen3.5-flash-02-23 | — | — | — | — | — | — | — | — | 404 Not Found — model ID invalide sur OpenRouter |

### FP/FN par modèle

**qwen3-14b** — FP: `Un premier bâtiment [event]`, `Passes-bien [caste]` (doublon), `Ailes-Grises [caste]` (doublon), `Rhombes miniatures [technology]` (doublon) | FN: `Confluence [place]`, `Voix de l'Aurore [institution]`

**qwen3.5-35b-a3b** — FP: `Fiers ailes grises [caste]` (variante) | FN: `Ciseaux de bois au dents d'obsidienne [technology]`, `Confluence [place]`, `Voix de l'Aurore [institution]`

**qwen3.5-27b** — FP: `Moules`, `Cratères`, `Vases rituels`, `Arbuste à baie`, `Ailes grises` (doublon), `Rhombes miniatures` (doublon) | FN: `Confluence [place]`, `Voix de l'Aurore [institution]`

### Conclusions

- **35b-a3b** gagne en F1 (+3.9pp) grâce à une précision record (94.1%) — quasi plus de bruit. Coût 2.7x qwen3-14b.
- **27b dense** est le pire des trois : le plus cher ($0.0068, 7.5x baseline), le plus de FPs hallués. Dense > MoE en coût pour un résultat inférieur.
- **qwen3-14b reste optimal** pour un usage prod quotidien : 85% F1 à $0.0009/turn.
- **Flash** : ID `qwen/qwen3.5-flash-02-23` invalide — à re-tester avec le bon ID si disponible.
- FNs persistants `Confluence [place]` et `Voix de l'Aurore [institution]` résistent à tous les modèles — problème de texte source (non capitalisés), pas de modèle.
Prochain levier : réduire FPs génériques (Tribu, Villages, Artefacts) dans entity_filter.py.

---

## v21.0-masked — Masked second-pass extraction (T1-T8)

Run date: 2026-03-07 | OpenRouter | qwen3:14b tout | ref T1-T8 = 42 entités

Architecture : v20.2-clean + passe masquée après dedup (appel entity_only sur texte avec entités remplacées par \_\_\_\_\_).

| Metric | Value |
|--------|-------|
| **F1** | **67.5%** |
| Precision | 73.0% |
| Recall | 62.8% |
| TP | 27 |
| FP | 10 |
| FN | 16 |
| Ref | 42 |
| Extracted | 37 |
| Cost | $0.0222 |
| LLM calls | 113 (8 fact + 14 entity + 8 focus + 7 validate + subject/profiling/aliases) |

Note : 14 appels `entity_extraction` = 8 passes normales + 6 passes masquées (2 turns trop courts, skip).

### FP (10)
`Antres des Echos`, `Assemblee des Chefs`, `Faucons Chasseurs`, `Guimbardes en os` (alias Rhombes), `Hameçons délicats`, `Plateau rocailleux`, `Rhombes en pierres` (alias), `Taillées dans des os` (alias), `Tambours en peau d'herbivore`, `Zone protégée`

### FN (16) — cibles visées
`gourdins`, `pieu`, `roches striées`, `techniques de polissage`, `pipeau en bambou` — **toujours FN** après passe masquée.
Autres FN : `autels des pionniers`, `culte des ancetres`, `larmes du ciel`, `morsure-des-ancetres`, `paniers immergés`, `passerelles`, `poisson fumé`, `radeaux`, `rites de déposition des morts`, `rituels de fertilité`, `vallée`

### Analyse

- **F1=67.5%** est le meilleur score T1-T8 enregistré (vs v18.4.2-nemo full corpus F1=58.6%)
- La passe masquée déclenche sur 6/8 turns — les 2 skips sont T01/T02 (trop courts après masquage)
- Les FNs cibles (gourdins, pieu, roches striées...) **ne sont toujours pas trouvés** → problème de texte source, pas de nombre d'appels. Ces termes apparaissent trop peu/trop génériquement pour que le LLM les classe comme entités.
- Les FPs sont surtout des alias multiples du même concept (Rhombes × 3) — l'alias resolver en prod devrait nettoyer.
- `Tambours en peau d'herbivore` = nouveau FP issu de la passe masquée (hallucination légère sans entités dominantes)

---

## v22.0 — Prompt révisé : rituels/architecture explicites (T1-T8, ref=34)

Run date: 2026-03-07 | OpenRouter | qwen3:14b tout | ref T1-T8 = **34 entités** (nettoyée)

Changements vs v21.0-masked :
- Référence réduite de 42 → 34 (retrait des 8 termes universellement génériques : Gourdins, Pieu, Fumage, Radeaux, Passerelles, Vallée, Techniques de polissage, Poisson fumé)
- Prompt système : règle `TOUJOURS rituels/rites/architecture` ajoutée
- Prompts facts+entity+focus : exemples OUI explicites pour `Rites de déposition des morts`, `Rituels de Fertilité`, `Pilotis`, `Paniers immergés`
- Catégorie `RITUELS/CROYANCES` ajoutée dans focus prompt

| Metric | Value |
|--------|-------|
| **F1** | **70.0%** |
| Precision | 63.6% |
| Recall | 77.8% |
| TP | 28 |
| FP | 16 |
| FN | 8 |
| Ref | 34 |
| Extracted | 44 |
| Cost | $0.0237 |
| LLM calls | 121 (8 fact + 15 entity + 8 focus + 7 validate + subject/profiling/aliases) |

### TP notables (nouveaux vs v21.0)
`Rites de déposition des morts` ✅ — récupéré grâce aux exemples OUI explicites
`Voix des cieux` ✅ — nouveau TP
`Pipeau en bambou` ✅ — récupéré (était FN dans v21.0 avec ref=42)

### FP (16)
`Campement`, `Camps temporaires`, `Chasseurs un peu trop audacieux`, `Choix`, `Enfants des Echos`, `Guimbardes en os`, `Générations à venir`, `Pièges`, `Piété filiale`, `Plateau rocailleux`, `Rhombes en pierres` (alias), `Rituels de guidance des anciens`, `Réserves de viande fumée`, `Tambours en peau d'herbivore`, `Territoire de chasses`, `Village temporaire`

### FN (8) — cibles restantes
`Autels des Pionniers`, `Enfants du Courant`, `Larmes du Ciel`, `Morsure-des-Ancêtres`, `Paniers immergés`, `Pointes de flèches`, `Rituels de Fertilité` (validate l'a tué T04 : "Metaphore poetique"), `Roches striées`

### Analyse

- **F1=70.0%** — nouveau record T1-T8 (vs v21.0-masked 67.5% sur ref=42). Comparaison partiellement biaisée par le changement de référence, mais la progression est réelle : 2 nouveaux TPs nets (`Rites de déposition des morts`, `Voix des cieux`).
- La précision recule (63.6% vs 73.0%) car plus d'entités extraites (44 vs 37) avec le recall qui monte (77.8% vs 62.8%).
- `Rituels de Fertilité` reste FN : validate T04 le coule à nouveau comme "Metaphore poetique sans referent concret". Même problème qu'en v21.x — le validate bloque les croyances/rituels perçus comme métaphores.
- `Paniers immergés` reste FN malgré l'exemple OUI explicite — présent dans T05 mais le LLM le classe en `place` (Pilotis), pas extrait séparément.
- FPs multiples sur alias (`Rhombes en pierres` + `Rhombes`) — le scorer les pénalise, mais l'alias resolver les consoliderait en prod.
- **Gagnant** : v22.0 avec la ref nettoyée est le meilleur benchmark honnête à date.

---

## v22.0 + PJ extraction — Entités joueur incluses (T1-T8, ref=33)

Run date: 2026-03-07 | OpenRouter | qwen3:14b tout | ref T1-T8 = **33 entités** (Autels des Pionniers retiré — c'est T15 PJ, hors corpus)

**Changement architectural majeur** : le pipeline extrait maintenant les entités des fichiers **PJ** (réponse du joueur), pas seulement MJ. Méthode : `FactExtractor.extract_pj_entities()` — entity_only + focused, **sans validate** (le lore joueur est canonique, pas besoin de filtrer la généricité). 47 entités PJ extraites sur 8 turns.

| Metric | Value |
|--------|-------|
| **F1** | **76.6%** |
| Precision | 64.3% |
| Recall | 94.7% |
| TP | 36 |
| FP | 20 |
| FN | 2 |
| Ref | 33 |
| Extracted | 56 |
| Cost | $0.0348 |
| LLM calls | 149 (8 fact + 23 entity + 16 focus + 7 validate + subject/profiling/aliases) |

Note : 23 appels entity = 8 GM normaux + 7 GM masqués + 8 PJ. 16 appels focus = 8 GM + 8 PJ.

### Nouveaux TPs grâce au PJ
`Morsure-des-Ancêtres` ✅ (PJ T06) — introuvable depuis le MJ seul
`Les Larmes du Ciel` ✅ (PJ T06) — introuvable depuis le MJ seul
`Paniers immergés` ✅ (PJ T05) — introuvable depuis le MJ seul
`Enfants du Courant` ✅ (PJ T07) — maintenant TP
`Rituels de Fertilité` ✅ — trouvé dans PJ (le validate MJ le tuait encore)

### FN (2) — résistants à tout
`Pointes de flèches` — dans MJ T05 mais validate le coule
`Roches striées` — dans MJ T05+T06 mais validate le coule

### FP notables (20)
Sur-extraction PJ : `Art de la chasse`, `Outils de chasse`, `Expéditions de chasse` (3 variantes du même concept — alias resolver les consolide), `Confluents`, `Passerelles` (generic). Doublons : `Rhombes en pierres` (alias), `Rite de guidance des anciens` (alias de `Rituels de Fertilité`). Bruit PJ : `Naissance sous de mauvais auspices`, `Esprit qui veille sur les vivants`.

### Analyse

- **F1=76.6%** — nouveau record absolu T1-T8, +6.6pp vs v22.0 sans PJ (70.0%), +9.1pp vs v21.0-masked (67.5%)
- **Recall=94.7%** — quasi-exhaustif. On rate seulement 2 entités sur 33, et les deux sont présentes dans le texte MJ mais bloquées par le validate.
- La précision (64.3%) recule à cause de l'over-extraction PJ (47 entités dont ~20 FPs). Le ratio signal/bruit PJ est plus faible qu'en MJ — le joueur est verbeux, le LLM saisit des expressions qui ne sont pas des entités nommées stables.
- Les FPs PJ (`Art de la chasse`, `Expéditions de chasse`, `Outils de chasse`) sont des concepts que l'alias resolver regroupe — en prod le bruit serait réduit.
- `Roches striées` et `Pointes de flèches` : dans le texte MJ (`"si les chasseurs veulent des pointes de flèches, il leur faut des roches striés"`), mais le validate les bloque systématiquement. Seule une passe PJ les récupérerait si le joueur les mentionne — sinon FN définitifs.
- **Architecture retenue** : PJ extraction est désormais le comportement par défaut du pipeline. C'est le changement le plus impactant depuis v18.

---

## v22.0 + PJ extraction + no-choice filter — Baseline finale (T1-T8, ref=31)

Run date: 2026-03-07 | OpenRouter | qwen3:14b tout | ref T1-T8 = **31 entités**

**Deuxième fix architectural** : segments `choice` exclus de l'extraction d'entités. Les bullets de choix MJ (`- Des tambours en peau d'herbivore`, `- Des guimbardes en os`) listent des options non retenues par le joueur — les extraire produit des entités fantômes. Le fix : `relevant_text` dans `extract_facts()` exclut les segments de type `choice`. Les entités canoniques (celles choisies) apparaissent dans le texte narratif ou dans le PJ suivant.

| Metric | Value |
|--------|-------|
| **F1** | **82.4%** |
| Precision | 70.0% |
| Recall | 100.0% |
| TP | 35 |
| FP | 15 |
| FN | **0** |
| Ref | 31 |
| Extracted | 50 |
| Cost | $0.0319 |

### FP résiduels (15) — acceptables
Bruit PJ : `Rituels de rachat`, `Ordre des Anciens`, `Enfants des Anciens`, `Croyance`, `Fille` — expressions narratives capturées sans validate.
Géographiques génériques : `Campements`, `Sommet des montagnes`, `Village temporaire`, `Territoire de chasses`, `Passerelles`.
Doublons/alias : `Cercle` (alias de `Cercle des Sages`), `Confluents`, `Réserves de viande fumée`.

### Bilan de la session (2026-03-07)

| Version | F1 | P | R | FN | Changement |
|---------|-----|---|---|----|-----------|
| v21.0-masked (ref=42) | 67.5% | 73.0% | 62.8% | 16 | baseline session |
| v22.0 sans PJ (ref=34) | 70.0% | 63.6% | 77.8% | 8 | prompts rituels/architecture |
| v22.0 + PJ (ref=33) | 76.6% | 64.3% | 94.7% | 2 | extraction PJ activée |
| **v22.0 + PJ + no-choice (ref=31)** | **82.4%** | **70.0%** | **100%** | **0** | segments choice exclus |

**Découvertes clés** :
1. Le pipeline ignorait les fichiers PJ depuis le début — entités joueur (Morsure-des-Ancêtres, Larmes du Ciel, Paniers immergés) invisibles.
2. Les options non retenues des `## Choix` MJ polluaient l'extraction (Tambours, Guimbardes = jamais adoptés).
3. Avec ces deux fix, recall=100% sur 31 entités. Les 15 FPs résiduels sont du bruit PJ sans validate — acceptable en prod (alias resolver + entity_filter les consolident).

---

## v22.2.1-pastlevel — Test T1-T8 (ref=31)

Run date: 2026-03-08 | Ollama local | qwen3:14b | ref T1-T8 = **31 entités**

**Nouveautés v22.x** :
- Prompts sans aucun nom d'entité hardcodé (correction hallucination : "Grande Prospection", "Maladie des Antres" extraites sur T02 alors qu'elles n'y apparaissent pas → fix en remplaçant les exemples concrets par des patterns structurels)
- Support type `event` : faits historiques avec nom propre littéral dans le texte
- Carry-forward contexte tour par tour : `prev_tech_era` + `prev_fantasy_level` injectés dans le system prompt d'extraction
- Tags LLM générés dans le résumé GM : `thematic_tags` (16 catégories), `tech_era` (10 niveaux), `fantasy_level` (5 niveaux) — résumé et tags fusionnés en un seul appel LLM
- Migration 010 : 5 nouvelles colonnes sur `turn_turns` (thematic_tags, tech_era, tech_era_reasoning, fantasy_level, fantasy_level_reasoning)

| Metric | Value |
|--------|-------|
| **F1** | **66.7%** |
| Precision | 51.5% |
| Recall | 94.6% |
| TP | 35 |
| FP | 33 |
| FN | 2 |
| Ref | 31 |
| Extracted | 68 |

### FN (2) — résistants
`culte des ancetres` — croyance implicite, non nommée explicitement dans le texte
`rites de deposition des morts` — idem, paraphrasé différemment selon les tours

### FP notables (33)
Trop génériques : `Sagesse`, `Défunts`, `Mères`, `Nouveau-nés`, `Parents`, `Crues`, `Nuages`, `Lieu de vie`, `Village temporaire`, `Piété filiale`, `Respect aux défunts`
Variantes trop larges : `Art de la chasse`, `Outils et armes`, `Techniques de chasses`, `Outils de chasse`
Doublons : `Cercle de ses sages` (variante de `Cercle des Sages`), `Rhombes sacrés` (alias de `Rhombes`)
Autres : `Rituel funéraire`, `Rituels des crêtes`, `Radeaux amarrés`, `Passerelles`

### Analyse

- Recall quasi-identique au meilleur (94.6% vs 100%) malgré la suppression de tous les noms hardcodés — **non-régression validée**
- Précision en chute (51.5% vs 70.0%) : sans validate nemo, les termes génériques ne sont pas filtrés
- **Régression nette vs v22.0+PJ+no-choice (82.4%)** : la différence vient de l'absence de validate nemo + la suppression des exemples négatifs concrets qui guidaient le LLM
- Non-régression sur l'event type : `Grande Prospection de la vallée basse` correctement capturé sur T18

### Prochaine étape recommandée
Ajouter validate nemo en v22.3 (même architecture que v18.4.2-nemo) pour filtrer les FPs génériques sans toucher aux vrais positifs.
