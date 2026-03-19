# Aurelm

**Game Master toolkit for multiplayer civilization-building tabletop RPGs.**

Aurelm ingests game turns from Discord, structures them through a local ML pipeline, generates a self-maintaining wiki, and exposes an intelligent agent (OpenClaw) that the GM can query in natural language for sanity checks, recaps, and cross-civilization analysis.

## Architecture

```
Flutter Desktop GUI (Dashboard)
        │
        ├── Discord Sync (read-only bot + HTTP API)
        ├── ML Pipeline (LLM-based via Ollama — qwen3:8b dev / qwen3:14b prod)
        ├── Wiki Generator (MkDocs Material)
        ├── SQLite Database (28 migrations)
        └── Claude Agent (Claude API primary, claude -p CLI fallback)
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
| Database | SQLite (single file, 28 migrations) |
| MCP Server | TypeScript (strict, ES2022) |
| Agent | Claude API (primary) + `claude -p` CLI fallback |
| Discord | discord.py (read-only) + aiohttp HTTP API |

## Project Structure

```
Aurelm/
├── gui/                    # Flutter Desktop dashboard (Windows)
├── pipeline/               # ML pipeline — ingestion, extraction, profiling, subjects
├── bot/                    # Python Discord bot + HTTP API + Claude agent
├── wiki/                   # Auto-generated MkDocs wiki
├── mcp-server/             # MCP server for OpenClaw (TypeScript)
├── openclaw-config/        # OpenClaw skill + config templates
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
- **Chat system** — NDJSON streaming, thinking blocks display, tool use cards, persistent sessions, lore hyperlinks (entities/civs/turns/subjects), quote stealth display, graceful `claude -p` fallback on API error
- **Notes** — CRUD notes attached to entities/subjects/turns, side rail UI with draggable floating windows, pinned notes always shown to agent
- **Discord bot** — syncs channel history, runs pipeline, 16 tools, answers GM queries via Claude agent

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

1. Copy `openclaw-config/openclaw.json.template` to your OpenClaw config directory
2. Set `DISCORD_BOT_TOKEN` and `ANTHROPIC_API_KEY` environment variables
3. Create `aurelm_config.json` next to your DB with channel IDs

## Design Principles

- **Zero maintenance**: Once configured, Aurelm runs autonomously
- **Privacy first**: All ML processing is local (no data leaves the machine)
- **GM-centric**: Every feature serves the GM's workflow
- **Competitive fairness**: Cross-civilization data is siloed by default, only the GM sees everything

## License

MIT
