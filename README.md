# Aurelm

**Game Master toolkit for multiplayer civilization-building tabletop RPGs.**

Aurelm ingests game turns from Discord, structures them through a local ML pipeline, generates a self-maintaining wiki, and exposes an intelligent agent (OpenClaw) that the GM can query in natural language for sanity checks, recaps, and cross-civilization analysis.

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

## Stack

| Component | Technology |
|---|---|
| GUI | Flutter Desktop (Dart), Riverpod 3.0 |
| ML Pipeline | Python (spaCy, custom NER) |
| Local LLM | GPT-OSS 20B via Ollama |
| Wiki | MkDocs Material (auto-generated markdown) |
| Database | SQLite |
| MCP Server | TypeScript |
| Agent | OpenClaw + Claude API (primary) + local fallback |
| Discord | discord.py (read-only) |

## Project Structure

```
Aurelm/
├── gui/                    # Flutter Desktop dashboard
├── pipeline/               # ML preprocessing pipeline (Python)
├── wiki/                   # Auto-generated MkDocs wiki
├── mcp-server/             # MCP server for OpenClaw (TypeScript)
├── openclaw-config/        # OpenClaw skill + config templates
├── database/               # SQLite schema + migrations
└── docs/                   # Developer documentation
```

## Quick Start

### Prerequisites

- **Node.js** >= 20 (for MCP server)
- **Python** >= 3.11 (for ML pipeline)
- **Flutter** >= 3.x (for GUI)
- **Ollama** with GPT-OSS 20B model pulled
- **NVIDIA GPU** with 16GB+ VRAM (recommended: RTX 5070 Ti)

### Setup

```bash
# 1. MCP Server
cd mcp-server
npm install
npm run build

# 2. ML Pipeline
cd pipeline
pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# 3. Wiki
cd wiki
pip install mkdocs-material
mkdocs serve

# 4. Flutter GUI
cd gui
flutter pub get
flutter run -d windows
```

### Configuration

1. Copy `openclaw-config/openclaw.json.template` to your OpenClaw config directory
2. Set your Claude API key and Discord bot token in environment variables
3. Configure channel IDs in the dashboard

## Design Principles

- **Zero maintenance**: Once configured, Aurelm runs autonomously
- **Privacy first**: All ML processing is local (no data leaves the machine)
- **GM-centric**: Every feature serves the GM's workflow
- **Competitive fairness**: Cross-civilization data is siloed by default, only the GM sees everything

## License

MIT
