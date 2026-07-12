# Handoff — Generic Engine (branch `feat/generic-engine`)

> Paste-ready briefing for the next worker picking up the generic-engine work.
> Full developer doc: `docs/generic-engine.md`. Spec: `AURELM_GENERIC_ENGINE_WISHLIST.md`.

## What this is

Aurelm was extended into a **generic entity-relation engine + headless
exporters**, reusable on any corpus (not just the civ JDR). First non-civ
customer: the novel in `../civjdr_roman`. All work is on branch
`feat/generic-engine` (pushed to GitHub + Gitea, ~19 commits, not merged to main).
Two phases are done: (1) the engine itself (exporters, profiles, ingestion, seed,
chapter-by-chapter incremental) and (2) a quality-tuning cycle answering the
customer feedback. **Both are considered done — do not re-open anything without
Alexi's instruction; the "Still open" list below is on-request only.**

## Read first

- `docs/generic-engine.md` — architecture, commands, all details.
- Memory `project-generic-engine-verified-seam-map` — code-level map + full log.
- Memory `project-jdr-priority-over-generic-engine` — the guard-rail.

## Hard rules

1. **Chapter by chapter, never full.** One run = one chapter, incremental, on the
   same DB. History + relations accumulate across chapters. Never process a whole
   corpus in one pass.
2. **Civ pipeline stays green.** After any change: `cd pipeline && py -3.12 -m pytest`
   → expect ~261 passed / 5 skipped; the only failures are 2 `_real`
   LLM-integration tests needing a live Ollama (ignore them).
2b. **Every novel-affecting change must stay CIV-safe AND generic.** The rule Alexi
   set: it must work for ANY content, not overfit to the roman's seed. Novel-only
   behaviour is threaded through `DomainProfile` fields (civ defaults = unchanged),
   never by editing civ prompts/logic.
3. **Always ask Alexi before any LLM run.** One chapter per run (~$0.003,
   OpenRouter/qwen3:14b, key already in `pipeline/.env`).

## What's delivered (all validated)

- **Exporters** (`exporters/`, read-only, CJK-capable):
  - `python -m exporters graph --db X --center "Nom" --depth 2 --filter entity_type=person` → radial mindmap PNG+SVG
  - `python -m exporters characters --db X --out DIR` → **glossaire persos + historique PAR CHAPITRE**
  - `python -m exporters glossary --db X --out DIR`, `python -m exporters history --db X --out DIR`
- **Domain profiles** (`pipeline/pipeline/domain_profile.py`): `civ` (unchanged) + `novel` (person-centred, person↔person relation gate).
- **Generic ingestion**: `--corpus-type documents` (`document_loader.py`, 1 chapter = 1 turn, zero schema change).
- **Cast seed**: `--seed ../civjdr_roman/etat/noms.md` (`novel_seed.py`) — anchors canonical persons + FR/EN/ZH aliases; fixes fake persons and cross-language resolution (神谕者→Oracle).
- Text safeguards: CJK fuzzy matching, generic person-noun filtering.
- **Extraction versions**: `novel-v1` (baseline) and `novel-v2` (= v1 + a generic
  validate/false-positive pass; marginal on a seeded corpus, valuable unseeded).

## Quality tuning cycle (done, after `FEEDBACK_NOVEL_V1_ROMAN_T05.md`)

The roman's Claude ran the engine on a real chapter and filed 5 findings. Audits
showed the mature CIV pipeline is multi-pass (facts+entity+focus+masked+validate)
while novel-v1 was facts+entity only — and the quality techniques are mostly
content-agnostic. Fixes (all civ-safe, threaded via `DomainProfile`):

- **Alias judge antonymy** (P1, `da65d72`): new `v14-antonymy-generic` prompt in
  `alias_resolver.py`; `DomainProfile.alias_prompt_version` (novel→v14, civ→config
  v12). Two opposite peoples ("ciel-clair" vs "nuages") no longer merge (20% vs old
  75%). Trade-off: a near-identical typo variant may not merge (precision>recall).
- **Profiling context scope** (P4/P5, `4994011` + `f2b9a46`): novel scopes each
  entity's context to its own sentence(s) via `tight_profiling_context` — stops
  one character's trait bleeding into another's description. Extends FORWARD only
  (up to `TIGHT_CONTEXT_MIN=320`) so relations still see co-occurrence but a
  preceding neighbour's trait can't leak. (First cut was sentence-only and killed
  relations 4→0 — a self-introduced regression, since fixed.)
- **Relation quality** (P2 + romance, `f2b9a46`): novel ontology gains
  amant-de/aime (romance) + apprenti-de; `DomainProfile.inverse_relations` flips
  inverse types to canonical direction (enfant-de→parent-de, apprenti-de→mentor-de)
  so the graph is consistently oriented. The central romance now types as `aime`,
  not `ami-de`.

## Process a chapter (from `pipeline/`)

```bash
py -3.12 -m pipeline.runner --data-dir <ONE_CHAPTER_DIR> --civ "Roman" \
  --corpus-type documents --seed ../civjdr_roman/etat/noms.md \
  --extraction-version novel-v1 --db aurelm_roman.db \
  --llm-provider openrouter --llm-config pipeline_llm_config.json
# repeat for the next chapter on the SAME db, then export.
```

## Gotchas

- `../civjdr_roman` is a **live repo** (restructured mid-work: `chapitres/` → `book/`). Re-check the current chapter dir before running.
- Chaining 2+ LLM runs in one background task hits the env kill limit — run **one chapter per task** (matches the architecture).
- Every real bug this project was found by **real runs**, never by the (green) tests — incl. a self-introduced one (over-tight profiling scope killed relations, caught only by measuring the side effect). **Validate the WHOLE output, not just the intended effect.** "No real run = unverified."

## Still open (from the feedback / tuning) — don't build without asking

- **Relation richness**: relations are clean + correctly typed but sparse (~1/chapter — the tight-context trade-off). They accumulate incrementally. To get more: bump `TIGHT_CONTEXT_MIN` (320→~550), relying on the prompt anti-bleed guard — measure on one T05 run.
- **P3 — alias applied to the wrong survivor**: a confirmed merge keeps the entity with the most mentions, so an epithet ("Sage") can beat the real name ("Front-Levé"); the merge is also swallowed by a broad try/except in `alias_resolver.store_aliases`. Deterministic fix: prefer the seeded canonical as survivor + don't swallow the merge.
- **P5-bis — Cendre typed `person`**: it's a crane, but `noms.md`'s enforced-persons table lists it there → the seed types it person. Seed-data / ontology fix.
- Per-chapter relation *viewing* (relations lack `turn_id`). Decided unnecessary.
- Chinese *extraction* prompts (seed carries cross-language; French prompts are weak on ZH).
- `--include-translations` CLI flag.
