# Aurelm - Startup Guide

## Quick Start (Two Steps)

### 1. Start the Bot (Terminal 1)
```bash
start-bot.bat
```

Or manually:
```bash
py -3.12 -m bot --db pipeline/aurelm_v22_2_2.db --port 8473
```

**Requirements:**
- `--db` parameter is **mandatory** (bot will not start without it)
- Database file must exist
- Port 8473 must be available

**Expected output:**
```
2026-03-11 ... INFO: Applying database migrations...
2026-03-11 ... INFO: Migration 1 applied successfully
...
2026-03-11 ... INFO: HTTP server listening on http://127.0.0.1:8473
```

### 2. Start the Flutter App (Terminal 2)
```bash
start-app.bat
```

Or manually:
```bash
cd gui
flutter run -d windows
```

**Requirements:**
- Bot must be running first (see step 1)
- Flutter 3.38.8+ installed
- Windows platform ready

## Database Files

- **Development:** `pipeline/aurelm_t01t08_fresh.db` (empty, 264K)
- **Production:** `pipeline/aurelm_v22_2_2.db` (real data, 2.7M) ← **USE THIS**

## Troubleshooting

### Port 8473 already in use
```bash
# Kill old process
taskkill /F /IM python.exe

# Then restart bot
start-bot.bat
```

### Database migrations fail
Auto-migration runs on startup. If it fails:
1. Check the database file exists
2. Check file permissions (must be readable/writable)
3. Check logs in `pipeline/bot.log`

### Flutter build fails
```bash
cd gui
flutter clean
flutter pub get
flutter run -d windows
```

## Architecture

```
Bot (Python) ← HTTP → Flutter App (Dart)
   ↓
SQLite DB (with auto-migrations)
```

Bot exports:
- `/health` - Health check
- `/chat/sessions` - Session management
- `/chat` - Chat endpoint (NDJSON streaming)
- 9 tools for game lore queries

## Keyboard Shortcuts

In the Flutter app:
- **Escape** - Cancel pending LLM response or queued message
- **Ctrl+F** - Search in turn details

## Sessions

Each chat session:
- Stores persistent message history
- Has tags for filtering
- Can be archived/renamed/deleted
- Visible in left drawer (click ☰)

---

**Note:** The app auto-applies all database migrations on startup. No manual schema setup needed.
