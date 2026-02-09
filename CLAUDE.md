# CLAUDE.md — Aurelm

## Project Overview

Aurelm is a Game Master toolkit for multiplayer civilization-building tabletop RPGs. It ingests Discord game turns, processes them through a local ML pipeline, generates a wiki, and exposes an MCP-based agent (OpenClaw) for GM queries.

**Primary user**: "Mug" (Arthur), GM running a 3+ civilization game. Has an RTX 5070 Ti (16GB VRAM). Wants zero maintenance and useful answers on complex cross-civilization contexts.

## Architecture

- **gui/**: Flutter Desktop (Dart, Riverpod 3.0) — GM dashboard
- **pipeline/**: Python ML pipeline — ingestion, NER, chunking, summarization
- **wiki/**: MkDocs Material — auto-generated game wiki
- **mcp-server/**: TypeScript MCP server — exposes tools to OpenClaw
- **openclaw-config/**: OpenClaw skill definitions and config templates
- **database/**: SQLite schema and migrations
- **docs/**: Developer documentation

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
- **Entity**: Named thing extracted by NER — person, place, technology, institution
- **Sanity Check**: Cross-referencing a GM statement against established lore for consistency
- **Lore**: The accumulated canonical facts about the game world

## Development Workflow

1. Database schema changes go in `database/migrations/` with sequential numbering
2. MCP tools in `mcp-server/src/tools/` — one file per tool
3. Pipeline modules in `pipeline/pipeline/` — one file per processing stage
4. Wiki templates and generation logic produce markdown in `wiki/docs/`
5. GUI state management via Riverpod providers

## Testing

- `cd mcp-server && npm test` — MCP server tests
- `cd pipeline && pytest` — Pipeline tests
- `cd gui && flutter test` — GUI tests
