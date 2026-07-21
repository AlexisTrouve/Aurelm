# Aurelm — Deployment (Step 10)

How Aurelm is packaged, installed, and configured on the Game Master's machine.
This is the complete reference for **Step 10**: the self-contained Windows
distribution, the installer, the secret model, and the first-run wizard.

Companion docs: [`enrollment-api-handoff.md`](enrollment-api-handoff.md) (the proxy's
mint/redeem contract) and [`enrollment-client-design.md`](enrollment-client-design.md)
(the design rationale for the activation flow).

---

## 1. What ships

A single **`Aurelm-Setup-<version>.exe`** (~27 MB compressed, ~112 MB installed).
It contains everything Aurelm needs to run on a machine with **no Python** and **no
repo checkout**:

```
<install dir>/                     (%LOCALAPPDATA%\Programs\Aurelm)
  aurelm_gui.exe                   Flutter desktop app (the UI)
  *.dll, data/                     Flutter runtime + plugins (incl. DPAPI, sqlite3)
  python/                          embedded CPython 3.12 + the bot's runtime deps
    python.exe
    python312._pth                 sys.path control (see §4)
    Lib/site-packages/             discord.py, openai, aiohttp, httpx, ollama
  app/
    bot/                           the Discord bot + HTTP API + Claude agent
    pipeline/                      the ML ingestion pipeline
    database/migrations/           the SQL migrations that build the schema
  unins000.exe                     uninstaller
```

**The app is two processes.** The Flutter GUI (`aurelm_gui.exe`) is the front end;
it **spawns the Python bot** as a subprocess (`python -m bot`) which serves the HTTP
API on `:8473`, connects to Discord, and runs the agent + pipeline. The GUI owns all
secrets and hands them to the bot through its environment (§6).

---

## 2. Architecture at a glance

```
  aurelm_gui.exe  (Flutter, Riverpod)
    │  owns: the DPAPI-sealed secrets, the DB path, the config
    │
    ├── spawns ──►  python/python.exe -m bot --db <DB> --port 8473
    │                 env: ETHERYALE_API_KEY, DISCORD_BOT_TOKEN, OPENROUTER_API_KEY
    │                 │
    │                 ├── HTTP API (aiohttp) :8473  ── the GUI talks to this
    │                 ├── Discord gateway (discord.py)
    │                 ├── Claude agent → etheryale proxy (OpenAI-compatible)
    │                 └── pipeline (Ollama local / OpenRouter cloud)
    │
    └── reads/writes:
          <DB dir>/aurelm.db              SQLite (schema owned by bot migrations)
          <DB dir>/aurelm_config.json     non-secret config (llm_provider, model, …)
          Windows Credential Store (DPAPI) the secrets — never a file
```

Default data location: **`Documents\Aurelm\`** (DB + config). Secrets live in the
Windows Credential Store via `flutter_secure_storage`, never on disk in plaintext.

---

## 3. Building the distribution

`scripts/build_distribution.ps1` assembles and self-tests the bundle.

```powershell
# Full build (Flutter release + bundle + installer):
./scripts/build_distribution.ps1 -Installer

# Reuse an existing Flutter release build (CI does this):
./scripts/build_distribution.ps1 -SkipFlutterBuild -Installer

# Also emit a portable ZIP instead of / alongside the installer:
./scripts/build_distribution.ps1 -Zip
```

Steps: build Flutter release → download the embedded CPython → `pip install` the
runtime deps (`requirements-dist.txt`) into it → rewrite `python312._pth` → copy
`bot/`, `pipeline/`, `database/` and the Flutter build → **smoke-test** (the embedded
interpreter must import the deps *and* the app packages *and* build a fresh DB schema)
→ optionally compile the installer.

**`requirements-dist.txt`** is the runtime dep set, deliberately separate from
`bot/requirements.txt` and `pipeline/requirements.txt`: the pipeline requirements
still list `spacy` + `fr_core_news_lg` (~550 MB) and `pydantic`, none of which the
code imports any more. The shipped set is the 5 packages actually imported:
`discord.py`, `openai`, `aiohttp`, `httpx`, `ollama`.

**Why the embeddable CPython and not PyInstaller:** the app spawns the bot as a real
subprocess and the pipeline imports it as a package. An interpreter we own keeps that
model intact — no freezing, no import hooks, no hidden-import guessing.

### The installer (`scripts/installer.iss`, Inno Setup)

- **Per-user** (`PrivilegesRequired=lowest`, under `%LOCALAPPDATA%`): no UAC prompt
  on install or upgrade. Nothing needs machine-wide scope.
- **Stable `AppId`** → upgrades replace instead of stacking.
- **Uninstall removes only app files.** The DB (`Documents\Aurelm`) and the
  DPAPI-sealed secrets live outside the install dir, so uninstalling **never destroys
  a campaign**. `[UninstallDelete]` also clears `app/` + `python/` because the
  embedded interpreter writes `__pycache__` after install (Inno doesn't track those).

### CI (`.github/workflows/build-gui-windows.yml`)

Triggers on `gui/`, `bot/`, `pipeline/`, the build script, or `requirements-dist.txt`.
It builds the Flutter release, **assembles the bundle + installer**, then **validates
both for real**: it launches the bot from the *bundled* interpreter and requires a
`200` on `/health`, then silently installs the setup.exe to a throwaway dir, runs the
*installed* bot's `/health`, and uninstalls — catching a broken `._pth`, a missing
dep, or app code that never made it into the bundle. Artifacts: `aurelm-installer`,
`aurelm-windows-distribution`, `aurelm-gui-windows`.

---

## 4. The embedded interpreter — `python312._pth`

The one non-obvious packaging detail. When a `._pth` file sits next to `python.exe`,
CPython takes **full control of `sys.path`**: it ignores `PYTHONPATH` **and does not
add the working directory**, even for `-m`. So the bundle's `._pth` explicitly adds
the app folder:

```
python312.zip
.
Lib\site-packages
..\app            # ← so `-m bot` and `import pipeline` resolve, whatever the cwd
import site
```

Without the `..\app` line the bundle fails with `No module named bot` no matter what
cwd it's given (measured, not assumed). The `.` entry means "the dir holding
python.exe", not the cwd.

---

## 5. The first-run wizard

Runs once, gated **above the router** (`app.dart`): until setup is complete the app
shows the wizard, not the shell — so the user never lands on a dead backend, and the
bot is never auto-started without a key. The gate check is a **local** secure-storage
read (`setupCompleteProvider`), never a network call, so a normal launch is
offline-tolerant. Each step owns its own forward action (it has a real side effect);
the last step marks `setup_complete`, which flips the app to the real UI.

| Step | What it does | Persists to |
|---|---|---|
| **1. Activation** | Paste a one-time code → redeem it for the etheryale API key | key → DPAPI |
| **2. Base** | Create + migrate the local DB (default `Documents\Aurelm\aurelm.db`) | DB file + `dbPath` pref |
| **3. Discord** | Paste the bot token → verify (token, intent, servers, channels) → map channels to civilizations | token → DPAPI; civs → DB |
| **4. Analyse** | Pick the ingestion engine: Ollama (local) or OpenRouter (cloud); for Ollama, pick + download a model | `llm_provider`/`ollama_model` → config; OpenRouter key → DPAPI |

**Internet is required exactly once — the wizard.** After it, launch is a local check
and the app works offline for anything already ingested; a revoked key surfaces at use
time (a `403`), never as a startup gate.

### Step 1 — Activation
`enrollment_service.redeem(code)` → `POST /api/enrollment/redeem` on the proxy. The
code is single-use, ~41 chars; the client does **not** length/regex-validate it (the
server normalizes case/whitespace, and a client rule would reject a good code the day
the format changes). On success the key is sealed **before anything else** — the code
is spent, so losing it would strand the user. All redeem failures (unknown / expired /
consumed) return one generic message: *"Code invalide ou déjà utilisé — demande un
nouveau code."*

### Step 2 — Database
`DbSetupNotifier.prepare()`: `mkdir` the DB dir → run `bot --migrate-only` (which
applies the SQL migrations and exits) → **only then** `setPath`. Order matters:
Flutter's Drift layer only creates a few of its own tables; the ~35 core tables are
owned by the bot's migrations, so pointing the app at the DB before the schema exists
would fail every query.

### Step 3 — Discord (Arthur's own bot)
`discord_service.verify(token)` hits `/users/@me` (token valid?),
`/applications/@me` (Message Content intent — checked on **both** flag bits `1<<18`
and `1<<19`/"LIMITED", because an unverified app under 100 servers only has LIMITED),
`/users/@me/guilds` + `/guilds/:id/channels` (the mapping source), and builds a
read-only invite URL (`permissions=66560` = View Channels + Read Message History).
The user maps channels → civ names/players; civs are written via
`CivilizationDao.createCiv` (upsert by name + channel binding), so the bot's sync —
`civ_civilizations WHERE discord_channel_id IS NOT NULL` — picks them up unchanged.
Optional proxy (`discordProxyProvider`, null by default) for a blocked network.

**Why his own bot:** it reads his server's private messages — that access must be his,
and a rotation of anyone else's token must not break him. The manual part (create the
app, flip the intent, copy the token, authorize the invite) is four browser clicks
Discord gives no API for; the wizard's value is that every step is **verified**.

### Step 4 — Ingestion engine
Ollama (default; free, private, needs the model pulled — the user's GPU handles it) or
OpenRouter (cloud, needs a key, costs per run). The recommended-model registry lives
in `gui/lib/models/ollama_models.dart` (the single source, read by the wizard and —
later — Settings): `qwen3:14b` recommended for a 16 GB card, with `qwen3:8b` and
`llama3.1:8b` as lighter alternatives. The wizard can **download** the chosen model
in-app (`POST /api/pull`, streamed progress) but does **not** install Ollama itself.
`llm_provider`/`ollama_model` go to `aurelm_config.json`; an OpenRouter key is sealed
in DPAPI and injected as `OPENROUTER_API_KEY`.

---

## 6. Secrets & config — where everything lives

| Thing | Storage | How the bot gets it |
|---|---|---|
| etheryale API key | DPAPI (Credential Store) | env `ETHERYALE_API_KEY` |
| Discord bot token | DPAPI | env `DISCORD_BOT_TOKEN` |
| OpenRouter key (if used) | DPAPI | env `OPENROUTER_API_KEY` |
| llm_provider, ollama_model, proxy | `aurelm_config.json` (plaintext, next to DB) | read by `config.py` |
| civ↔channel mapping | the SQLite DB (`civ_civilizations`) | read by the sync |
| DB path, setup_complete flag | SharedPreferences / DPAPI | — |

**The GUI owns every secret; the bot stays dumb.** `config.py` reads each secret from
the environment first, so Flutter reads the DPAPI-sealed value and injects it into the
bot subprocess env at launch (`bot_service.start`, which merges with the parent env so
`PATH` etc. are preserved). A secret therefore only ever exists **sealed at rest** or
**in the subprocess's memory** — never in a plaintext file, never in the config json,
never in the repo. `aurelm_config.json` is git-ignored.

---

## 7. Runtime — launching the bot

`bot_service._resolveLauncher()` picks how to run the bot:
- **Packaged**: `<exe dir>/python/python.exe` + cwd `<exe dir>/app` (detected by those
  paths existing).
- **Dev checkout**: `py -3.12` + cwd = the repo root (nearest ancestor with a `bot/`).

The same resolution serves `migrate()` (the wizard's `--migrate-only` call). Migrations
are found by `bot/migrations._find_migrations_dir`: DB-relative first (dev, where the
DB is inside the repo), then package-relative (`<bot>/../database/migrations`, i.e.
`app/database/migrations` in the bundle). A genuinely missing dir now **raises** rather
than silently skipping — silent skip is how a "zero tables" install once shipped.

---

## 8. For Alexi — provisioning a user (Arthur)

1. **Mint an activation code** (admin, with your PAT):
   ```
   POST https://ai.etheryale.com/api/enrollment
   Authorization: Bearer <PAT>
   { "name": "arthur-aurelm", "ttl_hours": 72 }
   → { "code": "…41 chars…", "expires_at": … }
   ```
   (The PAT lives in the vault: `run-secure.py -e APIs/ETHERYALE_PAT`.)
2. **Send Arthur** the installer + the code, over two channels (the installer is
   generic and carries no secret; the code travels separately, once).
3. Arthur creates his Discord app + bot, enables Message Content, invites it (the
   wizard links + verifies each). If you run his machine, you can do this with him.
4. If the code is lost/expired, mint a new one — a code is single-use.

**Revocation** (if a key leaks): `DELETE /api/keys/:id` or
`PATCH /api/keys/:id {active:false}` — immediate (`403` on `/v1`).

---

## 9. For Arthur — first run

1. Run `Aurelm-Setup.exe` (no admin prompt) → launch Aurelm.
2. **Activation**: paste the code you were sent → Activer.
3. **Base**: click *Créer la base*.
4. **Discord**: create your bot in the dev portal (button provided), enable *Message
   Content*, paste the token → *Vérifier*; invite the bot to your server (button
   provided); map your channels to civilizations.
5. **Analyse**: keep *Ollama* and download *Qwen3 14B* (recommended), or pick
   *OpenRouter* and paste a key. → *Terminer*.

The app then opens. Sync fetches your Discord turns and builds the wiki/DB.

---

## 10. Maintenance & gotchas

- **Flutter version skew**: dev is 3.38.x, CI builds on **3.27.4**. Local
  `analyze`/debug can pass on newer-SDK APIs the CI release build rejects (e.g.
  `DropdownButtonFormField(initialValue:)` is 3.38-only; on 3.27.4 it's `value:`).
  Prefer the older-SDK API; **CI is authoritative**.
- **Dual-remote push**: GitHub needs the proxy (`git -c http.proxy=…:7897`), Gitea
  (`git.etheryale.com`, the VPS) must **not** use it. Push each remote separately;
  both hit intermittent TLS EOF — retry.
- **sqlite3 native-asset DLL**: `flutter build windows --release` downloads
  `sqlite3.x64.windows.dll` from GitHub and Dart ignores `HTTPS_PROXY`, so it fails
  locally on a blocked network. Seed the verified DLL into
  `.dart_tool/hooks_runner/shared/sqlite3/build/download-*/` (the hook accepts it by
  sha256). CI (direct internet) is fine.
- **`Test GUI` (analyze) is red on `main`** since 2026-07-12 on pre-existing warnings
  in files unrelated to this work (~86 issues), which also skips its test step.
  **Build + E2E are the real gates.** Before merging, confirm your branch adds no new
  analyzer issues (the failing lines don't name your files).
- **Ollama**: the wizard downloads a model but never installs Ollama — that's the
  user's job. On a machine where port `11434` is blocked at the socket, Ollama can't
  serve at all (an environment issue, not Aurelm).

---

## Test surface for this work

- `bot/tests/` — 135 tests (incl. `test_config.py::TestPipelineLlmKey`,
  `test_migrations.py`, `test_agent.py` model/effort filters).
- `gui/test/services/ollama_service_test.dart` — the `/api/pull` stream parse.
- `gui/integration_test/app_boot_test.dart` — 8 tests incl. the setup-gate test
  (un-activated → wizard; activated → shell).
- The wizard steps + enrollment + Discord + pipeline + Ollama download were each
  proven with throwaway integration_tests driving the real widgets against real
  services (redeem, migrate subprocess, live Discord API, config write) — not
  committable (they need live credentials/servers), but run during development.
