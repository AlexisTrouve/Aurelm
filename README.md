# Aurelm

**Game Master toolkit for multiplayer civilization-building tabletop RPGs.**

Aurelm ingests game turns from Discord, structures them through a local ML pipeline, generates a self-maintaining wiki, and exposes an intelligent Claude agent that the GM can query in natural language for sanity checks, recaps, and cross-civilization analysis.

## Architecture

```
Flutter Desktop GUI (Dashboard)
        │
        ├── Discord Sync (read-only bot + HTTP API)
        ├── ML Pipeline (LLM-based via Ollama — qwen3:8b dev / qwen3:14b prod)
        ├── Map system (ingest a Theomen world → LLM map tools + fog of war)
        ├── Wiki Generator (MkDocs Material)
        ├── SQLite Database (43 migrations)
        └── Claude Agent (via the etheryale proxy — one OpenAI-compatible backend)
              └── MCP Server (TypeScript, connected to wiki/DB)
```

## Stack

| Component | Technology |
|---|---|
| GUI | Flutter Desktop (Dart), Riverpod 2.6, Drift ORM, GoRouter |
| ML Pipeline | Python 3.12, Ollama client, httpx |
| Local LLM | qwen3:8b (dev, 5.2GB VRAM) / qwen3:14b (prod, 12GB VRAM) |
| Cloud LLM | OpenRouter (dev inference, no proxy needed) |
| Wiki | MkDocs Material (auto-generated markdown) |
| Database | SQLite (single file, 43 migrations) |
| MCP Server | TypeScript (strict, ES2022) |
| Agent | Etheryale proxy (`ai.etheryale.com/v1`, OpenAI-compatible, all Claude + GPT models) via the OpenAI SDK |
| Discord | discord.py (read-only) + aiohttp HTTP API |

## Project Structure

```
Aurelm/
├── gui/                    # Flutter Desktop dashboard (Windows)
├── pipeline/               # ML pipeline — ingestion, extraction, profiling, subjects
├── bot/                    # Python Discord bot + HTTP API + Claude agent
├── wiki/                   # Auto-generated MkDocs wiki
├── mcp-server/             # MCP server (TypeScript)
├── database/               # SQLite schema + migrations
└── docs/                   # Developer documentation
```

## Key Features

- **10-stage ML pipeline** — markdown ingestion → LLM entity extraction (v22.2.2) → summarization → subject tracking (MJ↔PJ) → entity profiling with tags → alias resolution with full entity merge → civ relation profiling
- **Entity system** — canonical names, alias history with naming timeline, semantic tags, hide/disable, mention tracking
- **Subject tracking** — open threads between GM and players (choices awaiting response, player initiatives awaiting GM treatment), confidence-filtered resolution matching, domain tags
- **Civ relations** — LLM-extracted inter-civ relations (diplomacy, trade, conflicts) stored in DB, exposed in Flutter + bot tool `getCivRelations`
- **Favorites** — star entities, subjects, turns; filterable in all browsers; exposed to agent via `getFavorites`
- **Flutter dashboard** — entity browser with tag/favorites filters, turn timeline with Ctrl+F search + fuzzy highlight, entity→turn fast travel, subjects screen, civ relations view, civ alias resolver
- **Map system** — ingest a [Theomen](../Gamedesigner/theomen)-generated world (binary GMVC `.world`, point-budget element sets) into a canon store, then serve it to an LLM through map tools that never touch `(q,r)`: `groundCivTerrain` (fog-aware, chronicle read-back, content gating), `findNearest`/`whatIsBetween` (fog-aware), spawn proposals, and narrative writes (`foundSettlement`/`expandTerritory`/`cedeTerritory`/`moveEntity`/`recordEvent`/`annotate`). Spatial fog of war + tech-gated content discovery + in-game-time event aging. **First consumer: the Demiurgos GM engine, in-process** — see `docs/map-tools-design.md`.
- **Chat system** — NDJSON streaming, thinking blocks display, tool use cards, persistent sessions, lore hyperlinks (entities/civs/turns/subjects), quote stealth display, per-request model picker + reasoning-effort knob (all via the etheryale proxy), leaked tool-call syntax stripped from answers
- **Notes** — CRUD notes attached to entities/subjects/turns, side rail UI with draggable floating windows, pinned notes always shown to agent
- **Agent memory** — the agent keeps its own memory, written from GM feedback and relevance-recalled per request (`editMemory`); reviewable in Settings
- **Discord bot** — syncs channel history, runs pipeline, answers GM queries via the Claude agent over **36 tools** (lore recall + map read/write)

## Quick Start

### Prerequisites

- **Node.js** >= 20 (for MCP server)
- **Python** >= 3.12 (for ML pipeline)
- **Flutter** >= 3.x (for GUI)
- **Ollama** with `qwen3:8b` pulled — `ollama pull qwen3:8b`
- **NVIDIA GPU** with 8GB+ VRAM (16GB recommended for qwen3:14b)

### Setup

```bash
# 1. MCP Server
cd mcp-server && npm install && npm run build

# 2. ML Pipeline
cd pipeline && pip install -r requirements.txt

# 3. Wiki
cd wiki && pip install mkdocs-material && mkdocs serve

# 4. Flutter GUI
cd gui && flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter run -d windows
```

### Run the pipeline

```bash
# On 2-3 turns (dev)
py -3.12 -m pipeline.runner \
  --data-dir /path/to/turns \
  --civ Confluence --player Rubanc \
  --db aurelm.db \
  --extraction-version v22.2.2-pastlevel \
  --llm-provider openrouter \
  --llm-config pipeline_llm_config.json

# Launch GUI (Windows — env var required)
$env:AURELM_DB_PATH = 'C:\path\to\aurelm.db'
Start-Process gui\build\windows\x64\runner\Debug\aurelm_gui.exe
```

### Configuration

On first launch the app runs a **4-step setup wizard** — no manual env vars or config
files needed: (1) an activation code redeemed with the etheryale proxy for an API key,
(2) create + migrate the local DB (folder and filename are yours to pick), (3) your own
Discord bot token + channel↔civ mapping, (4) the ingestion engine (Ollama or OpenRouter).
Every secret is DPAPI-sealed and injected into the bot subprocess. See `docs/deployment.md`.

## Design Principles

- **Zero maintenance**: Once configured, Aurelm runs autonomously
- **Privacy first**: All ML processing is local (no data leaves the machine)
- **GM-centric**: Every feature serves the GM's workflow
- **Competitive fairness**: Cross-civilization data is siloed by default, only the GM sees everything

## License

MIT
