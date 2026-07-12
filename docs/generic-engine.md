# Generic Engine — entity-relation engine + headless exporters

> Turns Aurelm from a civ-JDR GM toolkit into a **generic entity-relation engine**
> with **headless exporters**, reusable on any corpus. First non-civ customer: a
> novel (`../civjdr_roman`). Merged to main via PR #1 (merge commit `5a2867d`;
> was branch `feat/generic-engine`).

## 0. One-line model

A **customer** = a corpus → its own Aurelm DB. Aurelm **extracts** entities /
relations / mentions / per-chapter history from that corpus, then **exports**
headless: a **mindmap** (PNG/SVG), a **glossary**, a **character glossary with
per-chapter history**, an **entity history**. Domain-neutral, config-driven, no
per-customer code.

## 1. Hard rules

- **The civ pipeline stays green.** Every change is regression-tested against the
  civ path (full pipeline suite: `cd pipeline && py -3.12 -m pytest`, expect
  ~253 passed / 5 skipped; the only failures are the 2 `_real` LLM-integration
  tests that need a live Ollama — ignore them).
- **Chapter by chapter, never full.** A corpus is processed **one chapter at a
  time, incrementally**. A run = a chapter. The pipeline accumulates entities,
  per-chapter history and relations across chapters. Never run the whole corpus
  in one pass (it is both wrong for the workflow and hits the env's background
  time limit on large profiling).
- **No hardcoded game data.** Ontology, prompts and cast are config/data-driven
  (domain profiles + the customer's own `noms.md`), never Python constants.

## 2. Architecture

```
corpus (chapters)                                headless artefacts
   │                                                    ▲
   ▼                                                    │
document_loader ──► turn_raw_messages ──► chunk ──► extract ──► profile ──► aliases
   (--corpus-type documents)              (1 chapter = 1 turn)      │
   novel_seed (--seed noms.md) ───────────────────────────────────┘
   pre-seeds the known cast + cross-language aliases
                                                        exporters/ (read-only)
```

The four core tables are **domain-neutral**: `entity_entities`, `entity_aliases`,
`entity_mentions`, `entity_relations` (+ `turn_turns` for chapter numbers). The
exporters and the generic path read only these.

## 3. Domain profiles — `pipeline/pipeline/domain_profile.py`

The ontology gate is just **two constants** guarding two call sites; both now read
the **active profile**:

- `entity_filter.VALID_ENTITY_TYPES` (used at `fact_extractor` entity gate)
- `entity_profiler.VALID_RELATION_TYPES` (used in `_resolve_and_insert_relations`)

`DomainProfile(name, entity_types, relation_types, relation_endpoint_types)`:

- **`civ`** — the exact historical vocab; the legacy constants are now *aliases*
  of `CIV_PROFILE` (byte-identical, civ unchanged).
- **`novel`** — person-centred narrative ontology. entity types
  `person/place/creature/event/group/object/belief`; relation types
  `parent-de / enfant-de / marié-à / mentor-de / héritier-du-geste / même-peuple
  / observe / ami-de / ennemi-de`. **`relation_endpoint_types={"person"}`** — a
  hard, deterministic gate that keeps only person↔person edges (drops the
  place/group edges the LLM draws despite the prompt asking otherwise).

A profile is selected by the extraction version: `ExtractionVersion.profile`
(default `"civ"`). The novel version is `novel-v1`
(`extraction_versions/novel.py`, French person-centred prompts). The runner
threads `get_profile(version.profile)` into profiling.

## 4. Generic ingestion — `pipeline/pipeline/document_loader.py`

`--corpus-type documents` routes Step 3 to `load_documents()` instead of the
Discord loader. **Zero schema change**: each chapter is written into
`turn_raw_messages` with the Discord loader's synthetic-value trick — a
`__player__` placeholder before each chapter makes the chunker cut a boundary, so
each chapter becomes one `is_gm_post` turn authored by a single `Narrator`
(resolved as GM by the existing fallback). MJ/PJ-specific stages (subject
extraction, inter-civ relations) are skipped for documents.

Key detail: all synthetic ids/timestamps are keyed on the **chapter number**
(parsed from the filename, e.g. `CHAP_T05` → 5), NOT the batch index — so
loading `[T05]` then `[T06]` separately composes idempotently (this is what makes
chapter-by-chapter work). Language variants (`*.zh.md`) are excluded by default.

## 5. Deterministic cast seed — `pipeline/pipeline/novel_seed.py`

`--seed <path to noms.md>` runs as Step 2.5 (documents only), before extraction.
`parse_noms()` reads the corpus's canonical name registry (`etat/noms.md`, a
`slug | FR | EN | ZH` markdown table):

- **enforced persons table** → person entities with FR canonical + EN/ZH aliases.
- **advisory table** → peoples/places/things, typed by keyword
  (`peuple/gens`→group, `(plat)/(racine)`→object, default→place).

`apply_seed()` inserts them (idempotent). Because the runner builds its
`entity_lookup` from the DB, the seeded cast is fed to the extraction pattern pass
automatically — mentions **canonicalize** to real characters (kills generic-noun
persons) and **cross-language** names resolve (`神谕者`→`Oracle`). No change to
`fact_extractor`.

## 6. Text-quality safeguards (all language-level, civ-safe)

- **CJK fuzzy matching** (`fact_extractor._CJK_RE`): the fuzzy prefilter skipped
  names < 4 chars as noise — a latin floor that dropped every 2-3 char Chinese
  alias. Now the floor is 2 for CJK names, 4 for latin. This is what makes the
  seeded ZH aliases resolve in Chinese text.
- **Generic person-nouns** (`entity_filter._GENERIC_FRENCH_NOUNS`): `Fille`,
  `Vieux`, `Femme`, `Jeune homme`, … filtered as noise; compound/proper names
  (`Fille des Nuages`, `Vieux-Chêne`) kept.

## 7. Headless exporters — `exporters/`

Standalone, **read-only** package (DB opened `mode=ro`, so an export can never
mutate a game DB), like `wiki/`. Deps: `exporters/requirements.txt`
(networkx + matplotlib). CJK-capable (auto-detects Noto Sans SC / SimHei; SVG
text exported as paths). All styling in `exporters/style.py` (`ExportStyle`), no
hardcoded FR text.

```bash
# radial ego-graph mindmap (PNG + SVG), persons only, 2 hops
python -m exporters graph      --db X --center "Nom" --depth 2 --filter entity_type=person --out out/map
# character glossary: per person, aliases + description + PER-CHAPTER history
python -m exporters characters --db X --out out/chars
# plain glossary / per-entity history
python -m exporters glossary   --db X --out out/gloss
python -m exporters history    --db X --out out/hist
```

The **character glossary** merges, richest-first: profiling per-chapter
turn-summaries, else mention contexts. Mentions accumulate reliably, so a chapter
is never dropped.

## 8. End-to-end: processing the roman, chapter by chapter

Run from `pipeline/` (provider OpenRouter/qwen3:14b; key already in
`pipeline/.env`). **Ask before any LLM run; one chapter per run (~$0.003).**

```bash
# each chapter into its own one-file dir, run against the SAME db (incremental)
py -3.12 -m pipeline.runner \
  --data-dir <ONE_CHAPTER_DIR> --civ "Roman" \
  --corpus-type documents --seed ../civjdr_roman/etat/noms.md \
  --extraction-version novel-v1 --db aurelm_roman.db \
  --llm-provider openrouter --llm-config pipeline_llm_config.json
# → repeat for the next chapter; history + relations accumulate.
# then export:
python -m exporters characters --db aurelm_roman.db --out out/chars
python -m exporters graph      --db aurelm_roman.db --center "Grain-de-Suie" --depth 2 --filter entity_type=person --out out/map
```

`../civjdr_roman` is a **live repo** — it was restructured mid-development
(`chapitres/` → `book/`). Always re-check the current chapter directory.

## 9. Why chapter-by-chapter accumulation works (and a bug that broke it)

Incremental re-profiling relies on `pipeline_turn_status` (turn↔run link, written
by `mark_turn_processed`). A latent bug in `_periodic_entity_dedup` broke the
whole thing: it migrated a merged entity's aliases with a plain
`UPDATE entity_aliases SET entity_id=…`; when both entities shared an alias (e.g.
two `Cendre` both carrying the seeded ZH `阿灰`) the `(entity_id, alias)` UNIQUE
constraint fired and **aborted the run mid-turn** → the turn was never marked →
later chapters couldn't re-profile earlier characters → per-chapter history and
relations froze at chapter 1. Fix: `UPDATE OR IGNORE`. After it, T05-then-T06
correctly accumulate `Tours [1, 2]` per character.

**Lesson (proved 5× this cycle): only a real LLM run verifies the pipeline.** All
five real bugs (profiling param shadowing, object relations, CJK floor, noun
leaks, dedup crash) were found by runs, never by the (green) test suite.

## 10. Deliberately NOT done

- **Per-chapter relation *viewing*.** Relations now *accumulate*, but
  `entity_relations` rows are inserted without `turn_id`, so you can't yet filter
  the graph to "chapter N". Decision: not needed — the accumulated graph suffices.
  To add it later: populate `turn_id` on relations + a `--chapter` filter on the
  graph exporter.
- **Chinese *extraction*.** The LLM extraction itself is weak on Chinese (novel-v1
  prompts are French); the deterministic seed carries cross-language resolution.
  A Chinese corpus would want ZH extraction prompts.
- **`--include-translations`** CLI flag (the loader supports it; not wired to CLI).
