# SETUP.md — Aurelm OpenClaw Deployment

## Prerequisites

### 1. MCP Server built
```bash
cd mcp-server
npm install
npm run build
# Verify: dist/index.js exists
```

### 2. Database populated
```bash
cd pipeline
python -m pipeline.runner --data-dir ../civjdr/Background --wiki-dir ../wiki/docs
# Verify: aurelm.db exists at project root with turns and entities
```

### 3. Environment variables
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...       # Claude API key (primary model)
AURELM_DB_PATH=C:/Users/alexi/Documents/projects/Aurelm/aurelm.db

# Optional
DISCORD_BOT_TOKEN=...              # For Discord sync (Step 7)
```

### 4. Ollama (fallback model)
```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.1:8b
# Verify: ollama list shows llama3.1:8b
# Note: requires ~8GB VRAM (RTX 5070 Ti has 16GB -- fine)
```

### 5. Proxy
The dev machine requires a proxy for external HTTPS (Anthropic API):
- Proxy address: `http://127.0.0.1:7897`
- Already configured in `openclaw.json.template` under `models.primary.proxy`

## Configuration

### 1. Copy and fill the config template
```bash
cp openclaw-config/openclaw.json.template openclaw-config/openclaw.json
```

Edit `openclaw.json`:
- Replace `CHANNEL_ID_CONFLUENCE`, `CHANNEL_ID_CDS`, `CHANNEL_ID_NANZA`, `CHANNEL_ID_GLOBAL` with actual Discord channel IDs
- Update `AURELM_DB_PATH` if the database is not at the default location
- Adjust `models.primary.proxy` if your proxy is different

### 2. Verify file structure
```
openclaw-config/
  openclaw.json          <- Your filled config (not committed)
  openclaw.json.template <- Template (committed)
  SOUL.md                <- Agent persona
  SETUP.md               <- This file
  skills/
    aurelm-gm/
      SKILL.md           <- Skill definition (9 tools)
      domain-knowledge.md <- Pre-seeded game context
```

## Validation

### Test 1: MCP Server starts
```bash
AURELM_DB_PATH=./aurelm.db node mcp-server/dist/index.js
# Expected: "Aurelm MCP server running on stdio (9 tools registered)" on stderr
# Ctrl+C to stop
```

### Test 2: MCP Server tests pass
```bash
cd mcp-server && npm test
# Expected: 24 tests passing
```

### Test 3: Ollama responds
```bash
ollama run llama3.1:8b "Dis bonjour en francais"
# Expected: A French greeting
```

### Test 4: Config JSON is valid
```bash
python -c "import json; json.load(open('openclaw-config/openclaw.json')); print('OK')"
# Expected: OK
```

### Test 5: All referenced files exist
```bash
python -c "
import os
files = [
    'openclaw-config/SOUL.md',
    'openclaw-config/skills/aurelm-gm/SKILL.md',
    'openclaw-config/skills/aurelm-gm/domain-knowledge.md',
    'mcp-server/dist/index.js',
]
for f in files:
    status = 'OK' if os.path.exists(f) else 'MISSING'
    print(f'{status}: {f}')
"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| MCP server fails to start | Check `AURELM_DB_PATH` points to an existing `.db` file |
| "No civilizations found" | Run the pipeline first to populate the database |
| Anthropic API timeout | Verify proxy at `127.0.0.1:7897` is running |
| Ollama not found | Install from https://ollama.ai, then `ollama pull llama3.1:8b` |
| JSON parse error in config | Run the Test 4 command above to find syntax errors |
