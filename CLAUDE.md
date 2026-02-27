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

- **gui/**: Flutter Desktop (Dart, Riverpod 2.6, Drift, GoRouter) — GM dashboard. 68 source files, 6 tests. **Flutter not installed on dev machine** — CI builds via GitHub Actions. Run `flutter create --platforms=windows .` in gui/ when Flutter is available locally.
- **bot/**: Python Discord bot + HTTP API + Claude agent. `python -m bot --db aurelm.db` starts the bot. 9 tools ported from MCP server, aiohttp HTTP server on :8473, discord.py for Discord gateway, Anthropic SDK for Claude API. 32 tests passing.
- **pipeline/**: Python ML pipeline — ingestion, LLM entity extraction, chunking, summarization. `--model` and `--extraction-version` CLI args. Reference entities in `pipeline/data/reference_entities.json`.
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

### Next Steps
- [ ] **Step 9**: Deployment — packaging, Arthur's machine setup, Discord bot invite

## Environment Notes (Dev Machine)

- **OS**: Windows 10/11
- **Node.js**: v25.2.1 (mcp-server ready)
- **Python**: 3.12 (pipeline ready)
- **Flutter**: NOT installed — gui/ is placeholder only
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
- `cd pipeline && pytest` — Pipeline tests (103 tests: test_chunker, test_classifier, test_loader, test_entity_filter, test_fact_extractor, test_runner, test_incremental_tracking)
- `python -m pytest bot/tests/` — Bot tests (32 tests: tools, config, dispatch)
- `cd gui && flutter test` — GUI tests (6 tests: widget tests for EntityTypeBadge/StatCard/EmptyState, model tests for FilterState/GraphData/AppConstants). Requires `dart run build_runner build` first for Drift codegen.
- **Test data**: Use `../civjdr/Background/*.md` as real game data for pipeline testing
