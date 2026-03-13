# Architecture — Aurelm

## Overview

Aurelm is a local-first, privacy-respecting GM toolkit. All processing happens on the GM's machine. The only external calls are to Discord (read-only) and optionally Claude API (for the agent).

## Data Flow

```
Discord Channels (one per civilization + global)
        |
        v
  Discord Sync ----------------------> SQLite DB
  (discord.py,                         (raw messages,
   read-only bot)                       structured entities,
        |                               turn metadata)
        v                                    |
  ML Pipeline (10 stages)                    |
  [1] Ingestion (normalize raw messages)     |
  [2] Chunker (turn boundary detection)      |
  [3] Classifier (segment types)             |
  [4-6] LLM Extraction + Summarization       |
      (facts, entities, validate via Ollama)  |
  [7] Subject Extraction (MJ/PJ threads)     |
  [8] Entity Profiling (incremental)         |
  [9] Alias Resolution (merge duplicates)    |
  [10] Wiki Generation                       |
                                             |
        .------------------------------------'
        |
        v
  Wiki Generator -------> MkDocs Site (localhost)
  (markdown templates,     /civilizations/{name}/
   auto-refresh)           /global/timeline
                           /meta/entities
        |
        v
  Bot + Agent (Python, 14 tools)
  -- listCivs          - List all civilizations with stats
  -- getCivState       - Current state of a civilization
  -- searchLore        - Full-text search across entities and lore
  -- sanityCheck       - Verify consistency of a statement
  -- timeline          - Events for a civilization or globally
  -- compareCivs       - Side-by-side analysis of civilizations
  -- getEntityDetail   - Deep dive on an entity (mentions, relations)
  -- getTurnDetail     - Full turn content with segments and entities
  -- searchTurnContent - Full-text search on turn segment content
  -- getStructuredFacts- Structured facts for an entity
  -- listSubjects      - List subjects (MJ/PJ threads) with filters
  -- getSubjectDetail  - Subject detail with options/resolutions
  -- getNotes          - GM notes for entity/subject/turn
  -- deepExplore       - Sub-agent for autonomous DB exploration
        |
        v
  Flutter Desktop GUI
  (Dashboard, Entities, Timeline, Subjects, Chat, Notes, Settings)
  -- NDJSON streaming from bot
  -- Persistent chat sessions with tags
  -- Notes side rail with draggable windows
```

## Component Details

### Discord Sync

- **Tech**: discord.py (read-only, no write permissions)
- **Function**: Polls configured channels, stores raw messages
- **Triggers**: On new message event OR periodic poll (configurable)
- **Output**: Raw messages in `turn_raw_messages` table

### ML Pipeline

10-stage sequential processing, each reading from and writing to SQLite:

1. **Ingestion** (`ingestion.py`): Fetches new messages from DB, normalizes formatting
2. **Chunker** (`chunker.py`): Detects turn boundaries (GM posts that start new turns vs continuations)
3. **Classifier** (`classifier.py`): Classifies message segments — narrative, choice, consequence, ooc, description
4. **LLM Extraction** (`fact_extractor.py`): LLM-based entity extraction via Ollama (qwen3:8b dev / qwen3:14b prod) — dual calls (facts+entities, entities-only), validation pass, PJ extraction
5. **Summarizer** (`summarizer.py`): LLM-generated turn summaries with extractive fallback
6. **Entity Filter** (`entity_filter.py`): Noise filtering (generic French words, URLs, markdown artifacts)
7. **Subject Extraction** (`subject_extractor.py`): 4 LLM calls/turn — MJ choices, PJ initiatives, resolution matching, consequence detection
8. **Entity Profiling** (`entity_profiler.py`): Incremental profiling — merges new turn summaries into existing entity descriptions
9. **Alias Resolution** (`alias_resolver.py`): Redirect mentions + relations, union tags, deactivate secondary entities, orphan chain resolution
10. **Wiki Generation** (`wiki/generate.py`): Auto-generates MkDocs Material pages per civilization

### Wiki Generator

- **Tech**: MkDocs Material with custom Python generation scripts
- **Structure**: One page per entity/civilization, auto-refreshed when DB changes
- **Serves**: Local HTTP for GM browsing and MCP server reads

### MCP Server (Legacy)

- **Tech**: TypeScript, Model Context Protocol
- **Exposed tools**: 9 original tools — superceded by Python bot with 14 tools
- **Data source**: SQLite DB (read-only, via AURELM_DB_PATH env var)
- **Stateless**: Each tool call is independent

### Bot + Agent (Primary)

- **Tech**: Python (discord.py + aiohttp + Anthropic SDK)
- **14 tools**: All original MCP tools + getStructuredFacts, listSubjects, getSubjectDetail, getNotes, deepExplore
- **NDJSON streaming**: Real-time streaming to Flutter GUI with thinking blocks and tool results
- **Persistent sessions**: Chat sessions with tags, auto-tag by civilization, resume support
- **SOUL.md persona**: Archiviste expert, French, GM-only perspective, subject/tag awareness
- **Auto-migrations**: Database migrations applied on bot startup

### Database

- **SQLite** with WAL mode for concurrent reads
- **Schema**: Normalized with clear domain boundaries (turns, entities, civilizations, relations)
- **Migrations**: Sequential numbered SQL files

### Flutter GUI

- **Tech**: Dart/Flutter Desktop, Riverpod 2.6, Drift ORM, GoRouter — 99 source files, 7 test files
- **Dashboard**: Overview of all civilizations, recent turns, pipeline status
- **Entity browser**: Search and view entities across civilizations with tags, aliases, naming history
- **Timeline**: Visual timeline of events per civilization with type filters
- **Subjects**: MJ/PJ thread tracking with domain tags and resolution status
- **Agent chat**: NDJSON streaming with thinking blocks, tool use display (expandable cards), message queue, persistent sessions with tags, sessions drawer
- **Notes**: Side rail on detail screens with hover-expanding tags, draggable floating windows for view/edit/add, inline NotesPanel alternative
- **Settings**: DB path picker, theme toggle
- **Navigation**: NavigationRail shell with 6 destinations (Dashboard, Entities, Timeline, Graph, Subjects, Settings)

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
