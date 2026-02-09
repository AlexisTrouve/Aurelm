# Architecture — Aurelm

## Overview

Aurelm is a local-first, privacy-respecting GM toolkit. All processing happens on the GM's machine. The only external calls are to Discord (read-only) and optionally Claude API (for the agent).

## Data Flow

```
Discord Channels (one per civilization + global)
        │
        ▼
  Discord Sync ─────────────────────► SQLite DB
  (discord.py,                         (raw messages,
   read-only bot)                       structured entities,
        │                               turn metadata)
        ▼                                    │
  ML Pipeline                                │
  ├── Chunker (turn boundary detection)      │
  ├── NER (entity extraction via spaCy)      │
  ├── Classifier (message type)              │
  ├── Summarizer (Ollama GPT-OSS 20B)       │
  └── Exporter (structured JSON → DB)        │
                                             │
        ┌────────────────────────────────────┘
        │
        ▼
  Wiki Generator ──────► MkDocs Site (localhost)
  (markdown templates,     ├── /civilizations/{name}/
   auto-refresh)           ├── /global/timeline
                           └── /meta/entities
        │
        ▼
  MCP Server (TypeScript)
  ├── getCivState    — Current state of a civilization
  ├── searchLore     — Full-text + semantic search across lore
  ├── sanityCheck    — Verify consistency of a statement
  ├── timeline       — Events for a civilization or globally
  └── compareCivs    — Side-by-side analysis of civilizations
        │
        ▼
  OpenClaw Agent
  (Claude API primary, GPT-OSS 20B fallback)
  └── Natural language interface for the GM
```

## Component Details

### Discord Sync

- **Tech**: discord.py (read-only, no write permissions)
- **Function**: Polls configured channels, stores raw messages
- **Triggers**: On new message event OR periodic poll (configurable)
- **Output**: Raw messages in `turn_raw_messages` table

### ML Pipeline

Sequential processing stages, each reading from and writing to SQLite:

1. **Ingestion** (`ingestion.py`): Fetches new messages from DB, normalizes formatting
2. **Chunker** (`chunker.py`): Detects turn boundaries (GM posts that start new turns vs continuations)
3. **NER** (`ner.py`): Custom spaCy model for fantasy NER — extracts people, places, technologies, institutions
4. **Classifier** (`classifier.py`): Classifies message segments — narrative, choice, consequence, OOC
5. **Summarizer** (`summarizer.py`): Uses Ollama to generate turn summaries and entity updates
6. **Exporter** (`exporter.py`): Writes structured data back to DB in canonical format

### Wiki Generator

- **Tech**: MkDocs Material with custom Python generation scripts
- **Structure**: One page per entity/civilization, auto-refreshed when DB changes
- **Serves**: Local HTTP for GM browsing and MCP server reads

### MCP Server

- **Tech**: TypeScript, Model Context Protocol
- **Exposed tools**: 5 tools for querying game state, lore, consistency
- **Data source**: SQLite DB + wiki markdown files
- **Stateless**: Each tool call is independent

### OpenClaw Agent

- **Primary**: Claude API (claude-sonnet-4-5-20250929) — best reasoning for complex queries
- **Fallback**: GPT-OSS 20B via Ollama — offline mode, simpler queries
- **Skill**: Custom `aurelm-gm` skill with GM-specific prompt engineering
- **MCP**: Connects to local MCP server for structured data access

### Database

- **SQLite** with WAL mode for concurrent reads
- **Schema**: Normalized with clear domain boundaries (turns, entities, civilizations, relations)
- **Migrations**: Sequential numbered SQL files

### Flutter GUI

- **Dashboard**: Overview of all civilizations, recent turns, pipeline status
- **Entity browser**: Search and view entities across civilizations
- **Timeline**: Visual timeline of events per civilization
- **Agent chat**: Embedded OpenClaw interface
- **Settings**: Discord channels, pipeline config, model selection

## Security Model

- Discord bot has **read-only** permissions (no message sending)
- Claude API key stored in environment variable, never in code
- Civilization data is siloed — each civ's channel is processed independently
- GM dashboard shows all data; per-player views not yet implemented
- No network exposure: wiki and MCP server bind to localhost only

## Hardware Requirements

- **GPU**: NVIDIA with 16GB+ VRAM (RTX 5070 Ti recommended)
- **RAM**: 32GB+ recommended (LLM + spaCy + Flutter)
- **Storage**: ~10GB for models + DB grows with game history
- **OS**: Windows 10/11 (primary target)
