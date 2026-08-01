# CLAUDE.md — Aurelm

## Mindset
Tu es un expert senior. Là pour résoudre, pas pour tourner autour — trancher, clarifier, avancer.

## Configuration
**IMPORTANT** : Toujours lire le fichier `../archives/ProjectTracker/.env` au démarrage pour accéder aux credentials Git/Gitea/GitHub nécessaires pour les opérations sur les repositories.

## Réseau
D'autres Claude experts bossent sur d'autres projets ici. Chacun a son propre repo. Via duo-partner : demande un avis, partage une solution, ou demande-leur d'explorer leur codebase si besoin.

## Context — Why This Project Exists

This is a tool for **Arthur ("Mug")**, Game Master of a multiplayer civilization-building tabletop RPG played on Discord. Arthur runs 3+ civilizations simultaneously, each controlled by a different player. The game spans millennia of in-game time with complex interlocking narratives.

**The problem**: Arthur drowns in lore. Hundreds of turns across multiple civilizations, named entities, technologies, political systems, alliances — he can't keep track of it all. He needs automated consistency checking and instant recall.

**The solution**: Aurelm ingests game turns from Discord, structures them with ML, builds a wiki, and gives Arthur an intelligent Claude agent he can ask things like "Est-ce que les Confluents ont déjà du bronze ?" or "Compare les forces militaires de toutes les civs".

### Related Repo — civjdr

`C:\Users\alexi\Documents\projects\civjdr` is the **player's repo** (one of Arthur's players). It contains real game data in `Background/YYYY-MM-DD-*.md` files — perfect test corpus for the ML pipeline. The `civjdr/CLAUDE.md` has extensive domain knowledge about one civilization (Civilisation de la Confluence) that serves as ground truth for NER and entity extraction testing.

### Known Civilizations in the Game

- **Civilisation de la Confluence** (player: Rubanc) — river valley civ with living clay tech, five-caste system, discovered ancient ruins
- **Cheveux de Sang** — foreign sea-faring civilization, first contact made
- **Nanzagouets / Tlazhuaneca** — another foreign civilization
- Others TBD as Arthur expands

## Project Overview

Aurelm is a Game Master toolkit for multiplayer civilization-building tabletop RPGs. It ingests Discord game turns, processes them through a local ML pipeline, generates a wiki, and exposes a Claude agent for GM queries.

**Primary user**: "Mug" (Arthur), GM running a 3+ civilization game. Has an RTX 5070 Ti (16GB VRAM). Wants zero maintenance and useful answers on complex cross-civilization contexts.

## Architecture

```
Flutter Desktop GUI (Dashboard)
        │
        ├── Discord Sync (read-only bot)
        ├── ML Pipeline (LLM-based via Ollama — qwen3:8b dev / qwen3:14b prod)
        ├── Wiki Generator (MkDocs Material)
        ├── SQLite Database
        └── Claude Agent (via the etheryale proxy — one OpenAI-compatible backend)
              └── MCP Server (TypeScript, connected to wiki/DB)
```

### Directory Layout

- **gui/**: Flutter Desktop (Dart, Riverpod 2.6, Drift, GoRouter) — GM dashboard. ~110 Dart source files, 7 test files. Flutter 3.38.8 installed locally. CI also builds via GitHub Actions. Run `dart run build_runner build --delete-conflicting-outputs` after any schema/DAO change.
- **bot/**: Python Discord bot + HTTP API + Claude agent. `python -m bot --db aurelm.db` starts the bot. **36 tools**: lore recall (listCivs, getCivState, getTurnDetail, searchLore, getEntityDetail, sanityCheck, timeline, compareCivs, searchTurnContent, getStructuredFacts, listSubjects, getSubjectDetail, getNotes, getFavorites, getCivRelations, getEntitiesByTag, deepExplore); **map read** (getMaps, getMapOverview, getCell, getCellHistory, getTerritory, findEntityOnMap, groundCivTerrain, findNearest, whatIsBetween, proposeSpawnPositions); **map write** (foundSettlement, expandTerritory, cedeTerritory, moveEntity, recordEvent, annotate, discoverAround — narrative acts logged to `map_cell_events`, semantic anchors only, never `(q,r)`); **memory** (`editMemory`, `discoverMemory` — the agent's own memory, see `docs/agent-memory.md`). Turn transactionality (begin/commit/abort_turn) is orchestration-only (importable, absent from `tool_definitions`). aiohttp HTTP server on :8473, discord.py for Discord gateway. **Agent backend: the etheryale proxy** (`ai.etheryale.com/v1`, OpenAI-compatible, fronting all Claude + GPT models) via the **OpenAI SDK** — NOT the Anthropic SDK, and no `claude -p` fallback (both removed). Auth is `x-api-key`. Per-request model picker + reasoning-effort knob (`reasoning_effort`) + visible-reasoning toggle (`include_reasoning`), all from the Flutter chat UI. Leaked tool-call syntax is stripped from the visible answer (`_strip_tool_call_syntax`). **The system prompt is assembled PER REQUEST**: static SOUL.md + domain-knowledge, plus relevance-recalled agent notes and memories. **261 tests passing.** Contract + traps: `docs/deployment.md`, the memory `reference_etheryale_proxy_llm_contract`.
- **pipeline/**: Python ML pipeline — ingestion, LLM entity extraction, chunking, summarization, subject tracking (MJ↔PJ). 10-stage pipeline (+ stage 6.5 preanalysis). `--model`, `--extraction-version`, and `--exclude-entity-types` CLI args (the last = opt-in entity-type suppression at the ontology gate; `run_pipeline(..., exclude_entity_types=[...])`, cascade-free — see `docs/exclude-entity-types.md`). Reference entities in `pipeline/data/reference_entities.json`.
- **pipeline/scripts/**: Standalone benchmark/scoring/profiling utilities. See `pipeline/scripts/README.md` for usage. Not part of the pipeline itself — run manually for evaluation and tuning.
- **wiki/**: MkDocs Material — auto-generated game wiki
- **exporters/**: Standalone **read-only** headless exporters (`python -m exporters <graph|glossary|characters|history> --db X`). Turn any Aurelm DB into a mindmap (PNG/SVG), a glossary, a character glossary with per-chapter history. networkx + matplotlib, CJK-capable. Part of the generic-engine work — see `docs/generic-engine.md`.
- **mcp-server/**: TypeScript MCP server — exposes tools to Claude agent. `npm install` done, dependencies ready.
- **database/**: SQLite schema and migrations
- **docs/**: Developer documentation (see `architecture.md` for full data flow; `generic-engine.md` for the generic entity-relation engine)

## Roadmap

### Done
- [x] **Step 1**: Repo scaffolding — structure, all stubs, schema, configs, first commit pushed to GitHub
- [x] **Step 2**: ML Pipeline — markdown loader (Format A + B), LLM-based entity extraction (dual calls: facts+entities and entities-only), versioned extraction strategies (v1-baseline, v2-fewshot with model-specific prompts), enhanced classifier, extractive summarizer fallback, pipeline orchestrator. Entity noise filtering via `entity_filter.py`. Reference entity DB for validation (`pipeline/data/reference_entities.json`, 124 entities). 103 tests passing.

- [x] **Step 3**: Wiki generator — auto-generates 8+ MkDocs Material pages (per-civ overview/turns/entities, global timeline, entity index, pipeline stats) with noise filtering, admonitions for choices/OOC, and dynamic nav update.

- [x] **Step 4**: MCP Server — 9 tools (listCivs, getCivState, searchLore, sanityCheck, timeline, compareCivs, getEntityDetail, getTurnDetail, searchTurnContent). Read-only SQLite via AURELM_DB_PATH, fuzzy civ name matching, structured Markdown output for LLM consumption, sanityCheck with keyword extraction + entity inventory. 24 integration tests passing.

- [x] **Step 5**: Agent persona — SOUL.md persona + domain-knowledge.md pre-seeded context (now in `bot/prompts/`).

- [x] **Step 6**: Flutter GUI — 65 Dart source files across 6 layers (data/models/providers/screens/widgets/core). Drift ORM mapping all DB tables, 5 DAOs with reactive streams, Riverpod providers, GoRouter with NavigationRail shell. Screens: dashboard (civ cards, pipeline status, quick search), civ detail (entity breakdown chart, top entities, recent turns), entity browser (search/filter/list + detail with aliases/relations/mentions), timeline (chronological turns with filters), graph (force-directed with graphview, per-civ filter, legend). Settings: DB path picker, theme toggle. 6 unit/widget tests, 2 GitHub Actions workflows (Windows EXE build + test). CI adapted from Haomirai pattern.

- [x] **Step 7**: End-to-end integration — Python bot package (discord.py + aiohttp + Anthropic SDK), 9 tools ported from TS to Python, HTTP API (/health, /status, /sync), Discord gateway (mentions/DMs -> Claude agent with tool use), fetcher (channel history -> DB), pipeline `run_pipeline_for_channels()` for multi-civ sync. Flutter: BotService (subprocess lifecycle), SyncService (HTTP client), bot_provider (health polling, sync state), updated PipelineStatusCard with bot status + sync button. Config via `aurelm_config.json` + env vars. 32 bot tests + 62 pipeline tests + 48 MCP tests all passing.

- [x] **Step 8**: Incremental pipeline + progress tracking — migration 004 (pipeline_turn_status, pipeline_progress tables), incremental entity profiling (merges new turn summaries into existing), real-time progress API for Flutter UI, `--track-progress` CLI flag. 104 tests passing.

- [x] **Step 8b**: Subject tracking (MJ↔PJ) — migration 006 (subject_subjects, subject_options, subject_resolutions tables), new pipeline stage [7/10] between extraction and profiling, `subject_extractor.py` (4 LLM calls/turn: MJ choices, PJ initiatives, resolution matching, consequence detection), `subject_helpers.py` (DB helpers), wiki subjects page under Connaissances. 195 pipeline tests passing (8 new).
  - **Tuning session**: confidence threshold 0.7 (default), ALL resolution attempts stored in DB regardless of threshold (for transparency/reporting), `num_ctx=32768` (full 32K context window), text truncation removed. `loader.py` bug fixed: `parse_format_c()` was splitting content at first `##` heading, silently truncating files like T18 PJ (41K→85 chars). MJ prompt updated to detect implicit narrative choices (not just explicit `## Choix` sections) — e.g. multiple artisan observations presented as alternatives.

- [x] **Step 8c**: Flutter GUI improvements — Subjects screen (list + detail), turn detail (GM/PJ blocks, Markdown), timeline filter fix, entity names in mentions, GitHub link.

- [x] **Step 8d**: GM/PJ turn fusion — migration 007, runner.py PJ segment insertion, Flutter turn detail shows both sections with colored left-border.

- [x] **Step 8e**: Turn detail UX — single GM/PJ blocks, Markdown rendering via flutter_markdown, search with highlight fallback, entity fast travel chips.

- [x] **Step 8f**: Alias entity merge + GUI enhancements:
  - **Full alias merge** (`alias_resolver.py`) — redirect mentions + relations, union tags, deactivate secondary, orphan chain resolution (`_resolve_orphan_pointers`, `_find_active_root`). 44 alias resolver tests.
  - **Migration 014** — `first_seen_turn_id` on `entity_aliases`
  - **Naming history** Flutter widget — chronological alias chain with turn links + auto-highlight on open (`NamingHistory` widget, `namingHistoryProvider`)
  - **Entity tags** — LLM-assigned semantic tags (`ENTITY_TAG_VOCAB` in profiler), migration 013, Flutter tag chips + filter
  - **Ctrl+F search** in turn detail — keyboard shortcut, multi-highlight (fuzzy regex: space/hyphen interchangeable + optional plural), match count badge, scroll-to-first-match via `GlobalKey + Scrollable.ensureVisible`
  - **Entity→turn fast travel** — `MentionTimeline` passes `mentionText` as highlight, auto-focuses search on arrival
  - **Fixed `run_migrations()`** — comment lines before SQL no longer cause ALTER TABLE to be skipped
  - **Fixed incremental profiler** — LEFT JOIN + `description IS NULL` covers entities from crashed runs

- [x] **Step 8g**: Chat system — NDJSON streaming from bot to Flutter, thinking blocks display, full tool results with expandable cards, message queue with Escape cancel, fused queue bubble, persistent sessions with tags (migration 016-017), auto-tag sessions by civilization, sessions drawer with resume + management UI, text selection everywhere (SelectionArea). 94 bot tests passing.

- [x] **Step 8h**: Agent tools v2 — added listSubjects, getSubjectDetail, getEntitiesByTag, getStructuredFacts, getNotes, deepExplore tools. Consolidated 18→12 tools then expanded to 14 with standard filter params. Rewrote SOUL.md + domain-knowledge.md with subjects + tag awareness. Subject auto-tagging by domain + Flutter filter. Auto-apply migrations on bot startup.

- [x] **Step 8i**: Notes system — migration 019 (notes table with entity_id/subject_id/turn_id FK), Flutter notes CRUD with side rail UI (vertical rail on left of detail screens, hover-expanding tags showing note titles, draggable floating windows via OverlayEntry for view/edit/add). NotesSideRail wrapper on entity/subject/turn detail screens. NotesPanel alternative for inline display.

- [x] **Step 8j**: Notes bug fix + enhancements — FK constraint fixes, pinned notes flag, agent notes type (system prompt injection), migration 020.

- [x] **Step 8k**: Granular tool params — showMentions, showFacts, showTimeline, showNotes per detail tool to reduce context bloat.

- [x] **Step 8l**: deepExplore sub-agent — internal Claude API call within tool execution for autonomous DB exploration.

- [x] **Step 8m**: Favorites system — migration 024 (`user_favorites` table), `FavoritesRepository` (raw SQL, no codegen), `favoritesProvider` (StateNotifier, Set<"type_id">), `favoritesOnly` filter on entities/subjects/timeline, star buttons in detail screens (entity/subject/turn), ⭐ chip in 3 filter bars, bot tool `getFavorites`.

- [x] **Step 8n**: Relations inter-civilisations — civ relation profiler LLM (`civ_relation_profiler.py`), detection in `runner.py`, `getCivRelations` bot tool, Flutter `CivRelationsRepository` + relations UI in civ detail screen.

- [x] **Step 8p**: Chat enhancements — quote stealth display (collapsed `_QuoteCard` instead of raw blockquote in user bubble), graceful `claude -p` CLI fallback on any Anthropic API error with orange bottom-right toast, lore hyperlinks in chat (turns T4, civ names, subjects #18 — fixed `_isInsideMarkdownLink` for bare `(`, dedicated `#N` regex pass), subject tags colored with entity palette (list tile, detail, filter bar).

### In Progress
- [ ] **Step 8o**: Civ Alias Resolver — UI-driven mapping of unresolved civ entity names to known civs. Migration 028 (`civ_aliases` + `civ_alias_dismissed`), pipeline `_detect_civ_mentions` uses aliases, `CivAliasResolverScreen` (done), `CivAliasRepository` (done), CivDetailScreen aliases section, backfill test, `gm_lock` buttons in relations/alias screens.

### Generic Engine — merged to main (PR #1, `5a2867d`; was branch `feat/generic-engine`)

Turns Aurelm into a **generic entity-relation engine + headless exporters**, reusable on any corpus (first non-civ customer: the novel `../civjdr_roman`). **Civ path stays byte-identical / green throughout.** Full doc: `docs/generic-engine.md`. Handoff: `HANDOFF_GENERIC_ENGINE.md`. Spec: `AURELM_GENERIC_ENGINE_WISHLIST.md`.

- [x] **P1 — Exporters**: standalone read-only `exporters/` package. `graph` (radial ego-graph mindmap PNG/SVG), `glossary`, `characters` (persons + per-chapter history), `history`. CJK-capable, no hardcoded FR. Also serves existing civ DBs.
- [x] **P2 — Configurable ontology**: `domain_profile.py` (`civ`/`novel`); the 2 ontology gates + prompts are profile-aware; `novel-v1` extraction version; person↔person relation endpoint gate.
- [x] **P3 — Generic ingestion**: `--corpus-type documents` (`document_loader.py`), 1 chapter = 1 turn, **zero schema change**, chapter-number-keyed synthetic ids.
- [x] **Deterministic cast seed**: `--seed etat/noms.md` (`novel_seed.py`) — anchors canonical persons + FR/EN/ZH aliases; kills fake persons, resolves cross-language names (神谕者→Oracle).
- [x] **Incremental accumulation**: processes **chapter-by-chapter** (never full); per-chapter history + relations accumulate. Fixed a dedup crash (shared alias) that had broken this.
- [x] **Quality tuning** (after `FEEDBACK_NOVEL_V1_ROMAN_T05.md`): antonymy-aware alias judge (novel — opposite peoples don't merge); sentence-scoped profiling context (novel — no cross-character description bleed); relation romance/direction typing + inverse normalization; `novel-v2` (validate pass); **alias-survivor fix** — a seeded canonical name beats a frequent epithet (this is the *feedback* "P3", distinct from "P3 — Generic ingestion" above); relation-richness window lever **measured & disproven** (real lever = a chapter-level coreference-aware relation pass, not shipped).
- **Rule**: one chapter per LLM run (~$0.003); never the full corpus at once.

### Next Steps
- [x] **Merged `feat/generic-engine` to main** — PR #1, merge commit `5a2867d` (2026-07-12).
- [x] **Chat agent → etheryale proxy** (PRs #4-6): dropped the 3-backend setup (Anthropic SDK + Ollama + `claude -p`) for one OpenAI-compatible client on the etheryale proxy; per-request model picker, reasoning-effort knob, visible-reasoning toggle; fixed a latent sparse-`tool_calls` crash (fixed proxy-side too).
- [x] **Step 10**: Deployment — **done + adversarially reviewed** (PRs #7-13). Self-contained Windows installer (`Aurelm-Setup.exe`: Flutter EXE + embedded CPython + `bot/` + `pipeline/pipeline/` + `database/`), a 4-step first-run wizard (activation code → DB migrate → Discord bot + channel↔civ mapping → Ollama/OpenRouter engine + in-app model download), all secrets DPAPI-sealed and injected via the bot subprocess env, one-time enrollment code via the proxy. **Full reference: `docs/deployment.md`.** Remaining is irreducibly on the user's side (create their Discord app, install Ollama if chosen) — the wizard guides + verifies it.
- [x] **Agent memory layer** (PRs #18-21, `0df2b8c`) — the agent keeps **its own memory**, written from Arthur's feedback and recalled per request. Increments: (1) dynamic relevance-recall of agent notes, replacing the static startup prompt; (2) `agent_memory` table (migration 039) + the agent writing memories itself; (2b) the Flutter review screen (Settings → Mémoire de l'agent); (3) precedence over pipeline data + `source_turn` "as of T*n*" anchoring; (4) tools unified into a single **`editMemory`** (create/update/forget) with **keys surfaced at recall** so the agent can reuse them. **Full reference + the plan for `discoverMemory` and memory→DB links: `docs/agent-memory.md`.** Known gap: whether a live model actually calls `editMemory` well is unproven (needs a live-LLM test / dogfood).
- [x] **Step 9**: Graph — DONE. The force-directed hairball was already replaced by a radial ego-graph (`4b79a52`); this round **polished** it (PR #16, `00d3cd6`): **auto-fit framing** (`EgoGraphLayout.compute` lays out in unit space then scales+centres to fill the pane, replacing the fixed 220/340px caps — mirrors the exporter's `set_xlim/ylim`), **edge-label declutter** (label base pushed outward 0.55→0.62 + wider collision grid), larger labels. Proof: 6 pure-layout RED→GREEN tests (`test/screens/graph_layout_test.dart`), a new E2E click-through asserting `EgoPainter` actually paints (9/9 on `-d windows`), and a real-font offscreen render.

### Map system — DONE + validated by an external consumer (Demiurgos)

Ingest a **Theomen**-generated world and serve it to an LLM GM. Chain: **Theomen (generates) → Aurelm (canon store + LLM tools) → Demiurgos (grounds its GM)**. Full docs: `docs/map-tools-design.md` (tools/fog/turns), `docs/map-ingestion-plan.md` (ingestion + real-format truths). Handoff: `HANDOFF.md`. Memory: `project_map_ingestion_theomen_contract`, `project_aurelm_demiurgos_technology_split`.

- [x] **Ingestion** — `bot/world_reader.py` (pure-stdlib GMVC decoder, no numpy) + `bot/map_ingestion.py` (crop-on-ingest, log-inverted resources, semantic per-cell record → `map_cells.metadata`). CLI: `python -m bot.map_ingestion`. Validated on the **real complete Theomen v2 export** (planet 1625×812).
- [x] **Theomen v2 point-budget format** (`4696161`) — a cell carries a **variable-size SET of elements** (families deposit/landmark/constraint) whose signed points sum to `budget_score`; single `elements.json` registry; chunks carry `element_count` + `element_0..7` (uint16). Replaced the v1 one-feature+one-deposit model. **Zero DB migration** (metadata is a JSON blob).
- [x] **LLM map tools** (`docs/map-tools-design.md`) — the LLM **never touches `(q,r)`**; targets by name / relative direction / spawn rank / civ seat. Reads: groundCivTerrain, findNearest, whatIsBetween, proposeSpawnPositions, getMapOverview. Writes (chronicle acts → `map_cell_events`): foundSettlement, expandTerritory, cedeTerritory, moveEntity, recordEvent, annotate, discoverAround. Turn transactionality (begin/commit/abort_turn) is orchestration-only.
- [x] **Fog of war (V2)** — spatial (`map_cell_discovery` per-civ) **and** content: `groundCivTerrain(maxHiddenLevel)` gates elements by prospecting depth; `fog=false` = GM omniscience. Aurelm holds **no tech model** — Demiurgos passes the depth.
- [x] **Chronicle read-back + aging** — `groundCivTerrain` surfaces the last N `map_cell_events` per province (`eventsPerCell`), closing the write→read loop; `game_time` stamp (migration 043) + `sinceGameTime` cutoff let Demiurgos **age** events (Aurelm stores + filters mechanically, **no aging policy of its own**).
- [x] **First consumer validated** — Demiurgos consumes Aurelm **in-process** (imports `bot.tools`); its Scribe writes the chronicle on a turn connection (commit persists / abort discards, E2E-verified) and reads it back into the GM prompt. Requests it drove: chronicle read-back, civ-seat anchor, event aging — all shipped TDD.
- [x] **Migration-runner hardening** (`8da9225`) — found + fixed a duplicate-number collision (two 035_/036_ files) that silently skipped `map_cell_discovery` on some DBs: renumbered map migrations → 041/042, runner now applies by **SET membership** (not `> MAX`), + a **loud guard** on duplicate numbers. Rule: every migration gets a unique `NNN_` prefix.
- **⚠️ Known bug (not fixed)**: `bot/discord_service.py` `verify()` has a blanket `catch (_)` that masks the real Discord error (401/timeout/etc.) as "impossible de joindre Discord". Map 401→invalid-token, 5xx→server, only real SocketException→network. Surfaced during the dogfood.

### Dogfood (first-run wizard, real use) — in progress
- [x] **Launcher cwd fix** (`b200bac`) — dev `py -m bot` resolved cwd from the DB dir; when the DB is outside the repo (the wizard default) the bot package wasn't importable ("No module named bot"). Now resolves the repo root from the EXE.
- [x] **Wizard resumability** (`3e2d9f3`) — an interrupted setup burned the single-use activation code → lock-out; the wizard now resumes past activation when a key is already sealed.
- [x] **DB location picker** (`388c0f7`) — the DB step opens the native "Save As" dialog to choose folder + filename (`file_picker.saveFile`), not just the default path.
- **Next**: the actual end-to-end first-run (real activation code, Discord app, Ollama) — the real-signal validation.

## Environment Notes (Dev Machine)

- **OS**: Windows 10/11
- **Node.js**: v25.2.1 (mcp-server ready)
- **Python**: 3.12 (pipeline ready)
- **Flutter**: 3.38.8 installed locally. Drift codegen: `dart run build_runner build --delete-conflicting-outputs` après tout changement table/DAO.
- **Ollama**: v0.15.6 installed, `qwen3:8b` + `llama3.1:8b` pulled. Default dev model: `qwen3:8b`
- **Arthur's machine**: RTX 5070 Ti 16GB VRAM — `ollama pull qwen3:14b` (12GB VRAM, 100% GPU, excellent French)
- **Proxy required** for external HTTPS: `http://127.0.0.1:7897`
- **Git push — push each remote SEPARATELY** (the dual push-URL on `origin` fails because GitHub and Gitea need *different* proxy regimes). GitHub needs the proxy; Gitea (VPS142) must **NOT** use it: `git -c http.proxy=http://127.0.0.1:7897 push https://github.com/AlexisTrouve/Aurelm.git HEAD:main` then `git -c http.proxy= push https://git.etheryale.com/StillHammer/Aurelm.git HEAD:main`. See memory `reference_aurelm_dual_push_network_regime`.
- **GitHub API calls**: Use Python `urllib` with proxy (no `gh` CLI, no `wget`)
- **GitHub user**: AlexisTrouve
- **GitHub repo**: https://github.com/AlexisTrouve/Aurelm
- **Gitea mirror**: https://git.etheryale.com/StillHammer/Aurelm
- **Always remove tokens from git remote URLs after push**

## Tech Stack

- **TypeScript** for MCP server (strict mode, ES2022 target)
- **Python 3.11+** for ML pipeline (Ollama client, httpx)
- **Dart/Flutter** for GUI
- **SQLite** as single database (no ORM — raw SQL with prepared statements)
- **Ollama** for local LLM inference (qwen3:8b dev, qwen3:14b prod — fits 8/16GB VRAM)
- **Etheryale proxy** (`ai.etheryale.com/v1`, OpenAI-compatible) as the single agent backend, via the OpenAI SDK (`x-api-key` auth). The old Anthropic-SDK / Ollama / `claude -p` trio is gone.

## Coding Conventions

### TypeScript (mcp-server)
- Strict TypeScript, no `any` types
- ES modules (`import`/`export`)
- Functional style where possible, classes for MCP tool definitions
- Error handling: explicit Result types, no silent catches

### Python (pipeline)
- Type hints on all public functions
- Docstrings on modules and public functions
- pytest for testing
- No global state — pass dependencies explicitly

### SQL (database)
- All tables prefixed with purpose (e.g., `turn_`, `entity_`, `civ_`)
- Migrations are numbered: `001_initial.sql`, `002_add_xyz.sql`
- Foreign keys always enforced (`PRAGMA foreign_keys = ON`)

### General
- French for all game content, English for code and comments
- Commit messages in English
- No secrets in code — use environment variables
- **No hardcoded game-specific data** in pipeline code — entity names, castes, technologies, civilizations etc. are extracted by the LLM, not by pattern lists. Noise filtering (generic French words, URLs, markdown artifacts) is OK because it's language-level, not game-specific.

## Key Concepts (Domain)

- **Turn**: A GM post on Discord containing narrative, choices, and consequences
- **Civilization**: A player-controlled entity with its own history, tech, politics
- **Entity**: Named thing extracted by LLM — person, place, technology, institution, resource, creature, event, civilization, caste, belief
- **Subject**: An open thread between GM and player — MJ→PJ (choice/question awaiting player response) or PJ→MJ (player initiative awaiting GM treatment). Tracked with status (open/resolved/superseded/abandoned) and resolution details.
- **Sanity Check**: Cross-referencing a GM statement against established lore for consistency
- **Lore**: The accumulated canonical facts about the game world
- **Living Clay (Argile Vivante)**: Example of a civilization-specific technology — hardens instantly on air contact
- **Caste System**: Civilizations develop complex social structures (e.g., Confluence's five-caste oligarchy: Air, Feu, Eau, Terre, Éther)

## Development Workflow

1. Database schema changes go in `database/migrations/` with sequential numbering
2. MCP tools in `mcp-server/src/tools/` — one file per tool
3. Pipeline modules in `pipeline/pipeline/` — one file per processing stage
4. Wiki templates and generation logic produce markdown in `wiki/docs/`
5. GUI state management via Riverpod providers

## Testing

- `cd mcp-server && npm test` — MCP server tests (48 tests via vitest)
- `cd pipeline && pytest` — Pipeline tests (~253 passed / 5 skipped on `feat/generic-engine`: adds test_domain_profile, test_document_loader, test_novel_seed, test_fuzzy_cjk, test_dedup_alias to the civ suite). The only 2 failures are `_real` LLM-integration tests needing a live Ollama — ignore them.
- `cd Aurelm && py -3.12 -m pytest exporters/tests` — Exporters tests (~23: graph render incl. CJK, glossary, characters, history, ego-graph layout, read-only DB).
- `python -m pytest bot/tests/` — Bot tests (135 tests: tools, config incl. `pipeline_llm_key`, dispatch, notes, deep_explore, migrations, model/effort filters)
- `cd gui && flutter test` — GUI tests (7 tests: widget tests for EntityTypeBadge/StatCard/EmptyState, model tests for FilterState/GraphData/AppConstants). Requires `dart run build_runner build` first for Drift codegen.
- **Test data**: Use `../civjdr/Background/*.md` as real game data for pipeline testing

### ⚠️ Pipeline LLM runs — règles impératives

**Ne JAMAIS lancer un full pipeline (19 tours) pour valider un changement. C'est long et ça coûte de l'argent.**

Pour tester sur 2-3 tours seulement, copier les fichiers concernés dans un dossier temporaire :
```bash
mkdir /tmp/civjdr_t01t02
cp "../civjdr/Background/"*T01* /tmp/civjdr_t01t02/
cp "../civjdr/Background/"*T02* /tmp/civjdr_t01t02/
py -3.12 -m pipeline.runner --data-dir /tmp/civjdr_t01t02 --civ Confluence --player Rubanc --db aurelm_test_quick.db --extraction-version v22.2.1-pastlevel --llm-provider openrouter --llm-config pipeline_llm_config.json
```

Le runner n'a pas de flag `--turns` — la seule façon de limiter est de limiter les fichiers en input.

**Toujours demander confirmation à l'humain avant de lancer un run LLM complet.**

**Pour valider un refactoring/changement technique** (imports, structure, DB) : `--no-llm` suffit. Vérifier que les segments/turns sont en DB, c'est bon. Un run LLM complet (extraction → subjects → profiling → aliases) ne sert que si on change la logique d'extraction ou les prompts.
