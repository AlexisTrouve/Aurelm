# Handoff — Generic Engine (branch `feat/generic-engine`)

> Paste-ready briefing for the next worker picking up the generic-engine work.
> Full developer doc: `docs/generic-engine.md`. Spec: `AURELM_GENERIC_ENGINE_WISHLIST.md`.

## What this is

Aurelm was extended into a **generic entity-relation engine + headless
exporters**, reusable on any corpus (not just the civ JDR). First non-civ
customer: the novel in `../civjdr_roman`. All work is on branch
`feat/generic-engine` (pushed to GitHub + Gitea). **This cycle is considered
done — do not re-open anything without Alexi's instruction.**

## Read first

- `docs/generic-engine.md` — architecture, commands, all details.
- Memory `project-generic-engine-verified-seam-map` — code-level map + full log.
- Memory `project-jdr-priority-over-generic-engine` — the guard-rail.

## Hard rules

1. **Chapter by chapter, never full.** One run = one chapter, incremental, on the
   same DB. History + relations accumulate across chapters. Never process a whole
   corpus in one pass.
2. **Civ pipeline stays green.** After any change: `cd pipeline && py -3.12 -m pytest`
   → expect ~253 passed / 5 skipped; the only failures are 2 `_real`
   LLM-integration tests needing a live Ollama (ignore them).
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
- 5 real bugs this cycle were all found by **real runs**, never by the (green) tests. "No real run = unverified."

## Deliberately NOT done (don't build without asking)

- Per-chapter relation *viewing* (relations lack `turn_id`). Decided unnecessary.
- Chinese *extraction* prompts (seed carries cross-language; French prompts are weak on ZH).
- `--include-translations` CLI flag.
