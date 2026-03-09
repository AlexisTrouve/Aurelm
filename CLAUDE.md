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

**The solution**: Aurelm ingests game turns from Discord, structures them with ML, builds a wiki, and gives Arthur an intelligent agent (OpenClaw) he can ask things like "Est-ce que les Confluents ont déjà du bronze ?" or "Compare les forces militaires de toutes les civs".

### Related Repo — civjdr

`C:\Users\alexi\Documents\projects\civjdr` is the **player's repo** (one of Arthur's players). It contains real game data in `Background/YYYY-MM-DD-*.md` files — perfect test corpus for the ML pipeline. The `civjdr/CLAUDE.md` has extensive domain knowledge about one civilization (Civilisation de la Confluence) that serves as ground truth for NER and entity extraction testing.

### Known Civilizations in the Game

- **Civilisation de la Confluence** (player: Rubanc) — river valley civ with living clay tech, five-caste system, discovered ancient ruins
- **Cheveux de Sang** — foreign sea-faring civilization, first contact made
- **Nanzagouets / Tlazhuaneca** — another foreign civilization
- Others TBD as Arthur expands

## Project Overview

Aurelm is a Game Master toolkit for multiplayer civilization-building tabletop RPGs. It ingests Discord game turns, processes them through a local ML pipeline, generates a wiki, and exposes an MCP-based agent (OpenClaw) for GM queries.

**Primary user**: "Mug" (Arthur), GM running a 3+ civilization game. Has an RTX 5070 Ti (16GB VRAM). Wants zero maintenance and useful answers on complex cross-civilization contexts.

## Architecture

```
Flutter Desktop GUI (Dashboard)
        │
        ├── Discord Sync (read-only bot)
        ├── ML Pipeline (LLM-based via Ollama — qwen3:8b dev / qwen3:14b prod)
        ├── Wiki Generator (MkDocs Material)
        ├── SQLite Database
        └── OpenClaw Agent (Claude API primary, local LLM fallback)
              └── MCP Server (TypeScript, connected to wiki/DB)
```

### Directory Layout

- **gui/**: Flutter Desktop (Dart, Riverpod 2.6, Drift, GoRouter) — GM dashboard. Flutter 3.38.8 installed locally. CI also builds via GitHub Actions. Run `dart run build_runner build --delete-conflicting-outputs` after any schema/DAO change.
- **bot/**: Python Discord bot + HTTP API + Claude agent. `python -m bot --db aurelm.db` starts the bot. 9 tools ported from MCP server, aiohttp HTTP server on :8473, discord.py for Discord gateway, Anthropic SDK for Claude API. 32 tests passing.
- **pipeline/**: Python ML pipeline — ingestion, LLM entity extraction, chunking, summarization, subject tracking (MJ↔PJ). 10-stage pipeline. `--model` and `--extraction-version` CLI args. Reference entities in `pipeline/data/reference_entities.json`.
- **wiki/**: MkDocs Material — auto-generated game wiki
- **mcp-server/**: TypeScript MCP server — exposes tools to OpenClaw. `npm install` done, dependencies ready.
- **openclaw-config/**: OpenClaw skill definitions and config templates
- **database/**: SQLite schema and migrations
- **docs/**: Developer documentation (see `architecture.md` for full data flow)

## Roadmap

### Done
- [x] **Step 1**: Repo scaffolding — structure, all stubs, schema, configs, first commit pushed to GitHub
- [x] **Step 2**: ML Pipeline — markdown loader (Format A + B), LLM-based entity extraction (dual calls: facts+entities and entities-only), versioned extraction strategies (v1-baseline, v2-fewshot with model-specific prompts), enhanced classifier, extractive summarizer fallback, pipeline orchestrator. Entity noise filtering via `entity_filter.py`. Reference entity DB for validation (`pipeline/data/reference_entities.json`, 124 entities). 103 tests passing.

- [x] **Step 3**: Wiki generator — auto-generates 8+ MkDocs Material pages (per-civ overview/turns/entities, global timeline, entity index, pipeline stats) with noise filtering, admonitions for choices/OOC, and dynamic nav update.

- [x] **Step 4**: MCP Server — 9 tools (listCivs, getCivState, searchLore, sanityCheck, timeline, compareCivs, getEntityDetail, getTurnDetail, searchTurnContent). Read-only SQLite via AURELM_DB_PATH, fuzzy civ name matching, structured Markdown output for LLM consumption, sanityCheck with keyword extraction + entity inventory. 24 integration tests passing.

- [x] **Step 5**: OpenClaw specialization — SOUL.md persona, domain-knowledge.md pre-seeded context, SKILL.md with all 9 tools documented (decision trees, error recovery, 9 examples), openclaw.json.template with correct model routing (llama3.1:8b fallback, tool-based routing), SETUP.md deployment checklist.

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

### Next Steps
- [ ] **Step 8g**: Graph redesign — current force-directed graph unusable, needs rethink
- [ ] **Step 9**: Deployment — packaging, Arthur's machine setup, Discord bot invite

## Environment Notes (Dev Machine)

- **OS**: Windows 10/11
- **Node.js**: v25.2.1 (mcp-server ready)
- **Python**: 3.12 (pipeline ready)
- **Flutter**: 3.38.8 installed locally. Drift codegen: `dart run build_runner build --delete-conflicting-outputs` après tout changement table/DAO.
- **Ollama**: v0.15.6 installed, `qwen3:8b` + `llama3.1:8b` pulled. Default dev model: `qwen3:8b`
- **Arthur's machine**: RTX 5070 Ti 16GB VRAM — `ollama pull qwen3:14b` (12GB VRAM, 100% GPU, excellent French)
- **Proxy required** for external HTTPS: `http://127.0.0.1:7897`
- **Git push**: `git -c http.proxy=http://127.0.0.1:7897 push` (pushes to both GitHub and Gitea)
- **GitHub API calls**: Use Python `urllib` with proxy (no `gh` CLI, no `wget`)
- **GitHub user**: AlexisTrouve
- **GitHub repo**: https://github.com/AlexisTrouve/Aurelm
- **Gitea mirror**: https://git.etheryale.com/StillHammer/Aurelm (auto-pushed via dual push URLs on `origin`)
- **Always remove tokens from git remote URLs after push**

## Tech Stack

- **TypeScript** for MCP server (strict mode, ES2022 target)
- **Python 3.11+** for ML pipeline (Ollama client, httpx)
- **Dart/Flutter** for GUI
- **SQLite** as single database (no ORM — raw SQL with prepared statements)
- **Ollama** for local LLM inference (qwen3:8b dev, qwen3:14b prod — fits 8/16GB VRAM)
- **Claude API** as primary agent backend, local LLM as fallback

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
- `cd pipeline && pytest` — Pipeline tests (195 tests: test_chunker, test_classifier, test_loader, test_entity_filter, test_fact_extractor, test_runner, test_incremental_tracking, test_subject_extractor, test_alias_resolver, test_benchmark, test_summarizer)
- `python -m pytest bot/tests/` — Bot tests (32 tests: tools, config, dispatch)
- `cd gui && flutter test` — GUI tests (6 tests: widget tests for EntityTypeBadge/StatCard/EmptyState, model tests for FilterState/GraphData/AppConstants). Requires `dart run build_runner build` first for Drift codegen.
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
