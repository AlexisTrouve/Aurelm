# CLAUDE.md — Aurelm

## Mindset
Tu es un expert senior. Là pour résoudre, pas pour tourner autour — trancher, clarifier, avancer.

## Configuration
**IMPORTANT** : Toujours lire le fichier `../ProjectTracker/.env` au démarrage pour accéder aux credentials Git/Gitea/GitHub nécessaires pour les opérations sur les repositories.

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
        ├── ML Pipeline (spaCy + GPT-OSS 20B via Ollama)
        ├── Wiki Generator (MkDocs Material)
        ├── SQLite Database
        └── OpenClaw Agent (Claude API primary, GPT-OSS 20B fallback)
              └── MCP Server (TypeScript, connected to wiki/DB)
```

### Directory Layout

- **gui/**: Flutter Desktop (Dart, Riverpod 3.0) — GM dashboard. **Flutter not installed on dev machine** — contains pubspec.yaml placeholder only. Run `flutter create .` when Flutter is available.
- **pipeline/**: Python ML pipeline — ingestion, NER, chunking, summarization
- **wiki/**: MkDocs Material — auto-generated game wiki
- **mcp-server/**: TypeScript MCP server — exposes tools to OpenClaw. `npm install` done, dependencies ready.
- **openclaw-config/**: OpenClaw skill definitions and config templates
- **database/**: SQLite schema and migrations
- **docs/**: Developer documentation (see `architecture.md` for full data flow)

## Roadmap

### Done
- [x] **Step 1**: Repo scaffolding — structure, all stubs, schema, configs, first commit pushed to GitHub

### Next Steps
- [ ] **Step 2**: ML Pipeline — real Discord ingestion + NER + chunking (use civjdr Background/ files as test data)
- [ ] **Step 3**: Wiki generator — auto-produce MkDocs pages from structured DB data
- [ ] **Step 4**: MCP Server — implement real tool logic (currently stubs return placeholder text)
- [ ] **Step 5**: OpenClaw integration — skill wiring, model routing (Claude API + Ollama fallback)
- [ ] **Step 6**: Flutter GUI — dashboard, entity browser, timeline view, agent chat
- [ ] **Step 7**: End-to-end integration — Discord bot live, pipeline auto-runs, wiki auto-refreshes

## Environment Notes (Dev Machine)

- **OS**: Windows 10/11
- **Node.js**: v25.2.1 (mcp-server ready)
- **Python**: 3.12 (pipeline ready)
- **Flutter**: NOT installed — gui/ is placeholder only
- **Ollama**: Not yet configured
- **Proxy required** for external HTTPS: `http://127.0.0.1:7897`
- **Git push**: `git -c http.proxy=http://127.0.0.1:7897 push`
- **GitHub API calls**: Use Python `urllib` with proxy (no `gh` CLI, no `wget`)
- **GitHub user**: AlexisTrouve
- **GitHub repo**: https://github.com/AlexisTrouve/Aurelm
- **Always remove tokens from git remote URLs after push**

## Tech Stack

- **TypeScript** for MCP server (strict mode, ES2022 target)
- **Python 3.11+** for ML pipeline (spaCy, Ollama client)
- **Dart/Flutter** for GUI
- **SQLite** as single database (no ORM — raw SQL with prepared statements)
- **Ollama** for local LLM inference (GPT-OSS 20B)
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

## Key Concepts (Domain)

- **Turn**: A GM post on Discord containing narrative, choices, and consequences
- **Civilization**: A player-controlled entity with its own history, tech, politics
- **Entity**: Named thing extracted by NER — person, place, technology, institution, resource, creature
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

- `cd mcp-server && npm test` — MCP server tests
- `cd pipeline && pytest` — Pipeline tests (2 test files already exist: test_chunker, test_classifier)
- `cd gui && flutter test` — GUI tests (when Flutter available)
- **Test data**: Use `../civjdr/Background/*.md` as real game data for pipeline testing
