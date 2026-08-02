# Handoff — Aurelm (map system: ingestion + LLM tools + Demiurgos integration)

Paste-ready briefing. Everything is on `main` (`195c22c`), pushed to GitHub + Gitea.
Bot suite: **261 passed / 4 skipped** (v2 map migration, fog-aware queries, feature-discover,
cedeTerritory, tool-syntax stripper, chronicle read-back + civ-seat anchor, event aging,
migration-runner hardening). GUI: **76 passed** (+ the full wizard walkthrough, Ollama
auto-install/start, DB picker, resumability). **Delivered as `Aurelm-Setup-0.2.1.exe`,
installed on the dev machine.** See the Dogfood section under Open items for where the
first-run stands.

## Headline: the MAP system is DONE, validated on real data, and CONSUMED IN PROD

The chain is **Theomen (generates a world) → Aurelm (canon store + LLM tools) →
Demiurgos (grounds its GM)**. Aurelm's whole side is built, tested, **migrated to and
validated on the real complete Theomen v2 point-budget export** (v1 feature+deposit is
gone), and **consumed by Demiurgos in prod** — its Scribe writes the chronicle on a turn
connection (commit persists / abort discards, E2E-verified) and reads it back into the GM
prompt. Three consumer-driven requests shipped TDD this session: chronicle read-back,
civ-seat anchor, and in-game-time event aging.

### 1. Ingestion (Theomen `.world` → `map_maps`/`map_cells`)
- `bot/world_reader.py` — pure-stdlib GMVC decoder (no numpy: the bot ships 5 deps).
  Generic over `manifest.fields`; handles the LSB presence mask, **partial edge chunks**,
  sparsity (absent≠0), and the **producer block** (business metadata `manifest["producer"]`).
- `bot/map_ingestion.py` — resolve index fields to names via sidecars, invert the
  log10-per-type resource densities + rank top-K, build the semantic per-cell record into
  `map_cells.metadata`, **crop-on-ingest** (decode the planet, write only the game's window),
  idempotent. CLI: `python -m bot.map_ingestion --db … --world … --map-name … [--window x,y,w,h]`.
- Migrations: 041 (`map_maps.metadata`), 042 (`map_cell_discovery`, fog) — renumbered from
  035/036 to resolve a duplicate-number collision (the runner keyed by number and silently
  skipped the 2nd of a pair; now a SET-based apply + a loud duplicate-number guard).
- **Real-format truths the frozen SPEC got wrong** (caught by the real file, fixed):
  metadata is in `manifest["producer"]` NOT `world.json`; sidecars are **wrapped**
  (`{"biomes":[...]}`, `{"deposits":[...]}`…) not bare lists; a chunk's `coord.x/y` is a
  **chunk INDEX** (origin = coord×chunkDims), not a cell origin. Fixtures now mirror all three.
  **Lesson (2× this session): a spec-faithful fixture hides a real-shape bug — only the real
  file settles it.**

### 2. The LLM tools (`docs/map-tools-design.md`)
Principle (prior art: MapAgent/Spatial-Agent/grid-world/Voyager): **the LLM never touches
(q,r)** — it targets by name / relative direction / proposal id; a Python layer owns all
geometry. The map is a **chronicle**: writes are narrative acts logged to `map_cell_events`,
validated, with echoed local-state feedback.
- **Reads**: `groundCivTerrain` (fog-aware + `maxHiddenLevel` content gating + chronicle
  read-back `eventsPerCell` + age cutoff `sinceGameTime` — the last N events per province
  resurface in the prompt, closing the write→read loop), `findNearest` & `whatIsBetween`
  (both fog-aware, default true), `proposeSpawnPositions`, `getMapOverview` (a semantic
  SUMMARY, not a cell dump), + the pre-existing
  `getMaps`/`getTerritory`/`findEntityOnMap`/`getCell`/`getCellHistory`.
- **Anchors** (`_resolve_anchor`): spawn rank / exact place name (label/element) / **civ
  name → its seat** / entity. Never `(q,r)`.
- **Event aging**: `recordEvent`/`annotate` take an optional `gameTime` (Demiurgos's
  in-game year, migration 043); `groundCivTerrain(sinceGameTime)` drops older events.
  Aurelm stores + filters mechanically — **no aging policy of its own** (Demiurgos owns
  the clock, the decay window, and lore sedimentation).
- **Writes**: `foundSettlement` (the socle), `expandTerritory`, `cedeTerritory` (transfer),
  `moveEntity`, `recordEvent`, `annotate`, `discoverAround`. All in `dispatch_tool`; all defer
  commit inside a turn.
- **Seeding**: `bot/map_seeding.py` — `propose_spawn_positions`, `place_civ`, discovery helpers.

### 3. Fog of war (V2, spatial + content)
`map_cell_discovery` per-civ; founding/expansion seed discovery, `discoverAround` explores,
`groundCivTerrain(fog=true)` reveals only discovered provinces (`fog=false`=GM omniscience).
Now also **content-gated**: `maxHiddenLevel` hides elements above the civ's prospecting depth
(counted "à prospecter"), and findNearest/whatIsBetween are fog-aware too.
**DEBT "feature discover"**: tech-gated knowledge of a province's CONTENTS (no coal in the
neolithic) is a smarter, unresolved mechanic — parked (`map-tools-design.md §6bis`).

### 4. Demiurgos integration — contract sealed
Demiurgos consumes Aurelm **in-process Python** (imports `bot.tools`, calls
`dispatch_tool(conn, name, input)`). Points resolved:
- **Aurelm = single source** for territory/cities (Demiurgos deprecates its local tables).
- **Turn transactionality (option A)**: `begin_turn`/`commit_turn`/`abort_turn` (importable
  callables in `bot.tools`, orchestration-only, absent from `tool_definitions`) bracket a turn;
  map writes accumulate on the passed connection and commit atomically — `_maybe_commit`
  defers inside a turn, `abort_turn` rolls back → no orphan canon. **Invariant**: on the turn
  connection the only writers are the map tools + lifecycle, and NONE auto-commits before
  `commit_turn` (annotate's "note" is a `map_cell_events` row, not the agent notes table).
- Grounding is **facts + labels**, never Theomen's finished prose (the GM owns the voice).
- **Surface**: in-process Python, so no mcp-server TS port needed for Demiurgos.

**FIRST CONSUMER VALIDATED (2026-07-28).** Demiurgos's own integration is wired and
green on the real world: `Demiurgos/seed_game.py::_seed_world` ingests the real
`theomen-worlds/world_v1_seed42.world` via Aurelm's `ingest_world`, places civs
(proposeSpawnPositions → place_civ), and `groundCivTerrain` returns real terrain that
reaches the GM prompt (`server/agents/gm.py::_format_map_for_gm`, with fallback/error
handling). Ran its tests against MY current Aurelm code (via sys.path): 14 green (3
`test_seed_world` on the real world + 11 dispatch/write/grounding). So the real-format
fixes are validated by an EXTERNAL consumer, not just Aurelm's own suite.
- **One gap on Demiurgos's side (message sent, not blocking)**: its
  `server/integrations/aurelm.py::aurelm_dispatch` opens a FRESH connection per call
  (thread-safe for reads, since tools run in `asyncio.to_thread` workers). That is fine
  for the GM READING the map, but BREAKS turn-atomic WRITES — begin/commit/abort_turn +
  the write tools need ONE turn connection routed through the turn's thread. Demiurgos
  wires that when its GM starts writing (founding/expanding mid-turn). The Aurelm side
  is ready; the fix is entirely on the consumer.

### Proof (three levels)
- unit: 231 bot tests (`test_world_reader`, `test_map_ingestion`, `test_map_seeding`,
  `test_map_grounding`, `test_map_queries`, `test_map_writes`, `test_map_events`,
  `test_map_expand`, `test_map_fog`, `test_map_turn`).
- real bytes: `bot/tests/test_real_world_export.py` (opt-in) — the complete **v2** export
  (`theomen/blog/world_aurelm_seed42.world`) decodes + ingests with full semantics, and the
  point-budget invariant `sum(element points)==budget_score` holds on the ingested records.
- live LLM: `bot/tests/live_map_probe.py` — a real model drives grounding + writes on a rich
  world (chose the right tools, GM-quality answers, wove in agent memory).
- cross-repo: Demiurgos's 14 Aurelm-integration tests were green on the real world as of
  2026-07-28 (v1). **STALE since the v2 migration**: its default world file
  `theomen-worlds/world_v1_seed42.world` is now missing (disk-full cleanup) so those real-world
  tests skip; re-point Demiurgos at the v2 export and re-run to re-confirm the first-consumer
  proof (`cd ../Demiurgos && py -3.12 -m pytest tests/test_seed_world.py tests/test_aurelm_*.py
  tests/test_map_grounding_reaches_gm.py`).

## Open items
- **Demiurgos turn-connection wiring for WRITES** — its side. Its `aurelm_dispatch` is
  fresh-conn-per-call (reads OK, breaks turn-atomic writes). It wires the turn connection
  when its GM starts writing to the map. Message relayed; Aurelm side is ready.
- **Theomen SPEC doc is wrong** (code works on the real file, only the doc lies): tell Theomen
  its `SPEC_WORLD_FORMAT.md`/`CONTRAT_EXPORT_AURELM.md` should say metadata is in
  `manifest["producer"]` (not `world.json`) and sidecars are wrapped.
- **Theomen v2 point-budget format — DONE (migrated + validated 2026-07-30, `4696161`+`32c53ef`).**
  Theomen shipped v2 (`export_version 4`, still `theomen.world.v1`) at `theomen/blog/
  world_aurelm_seed42.world`. A cell now carries a **variable-size SET of elements** whose signed
  points sum to `budget_score` (invariant verified on real data). `features.json`+`deposits.json` →
  single `elements.json` (268-entry registry, families deposit/landmark/constraint); chunks carry
  `element_count` (uint8) + `element_0..7` (uint16 ids). **Zero DB migration** (metadata = JSON
  blob). Code: `world_reader` loads elements.json; `map_ingestion._resolve_elements` → `meta[
  "elements"]`; grounding/overview/anchor/find_nearest read the set; `map_seeding` uses family +
  signed budget. All map fixtures migrated v1→v2; 231 bot tests pass; real-v2 test asserts
  sum(points)==budget. `hidden_level` per element is now carried in metadata.
  - **Cross-repo (relay to Demiurgos)**: its `seed_game.py` default world `theomen-worlds/
    world_v1_seed42.world` is MISSING (disk-full cleanup) → its real-world tests skip. Re-point it
    at the v2 export; a v1 world through the v2 code yields no elements (must use the v2 file).
- **Map gaps — CLOSED (2026-07-30, `5729fe0`+`6c017fd`).** The four map cleanups are done +
  tested (253 bot tests): (1) **fog-aware** findNearest/whatIsBetween — a civ no longer finds
  resources / reports barriers in land it never scouted (fog param, default true; fog=false =
  omniscience). (2) **feature-discover** — `groundCivTerrain(maxHiddenLevel=N)` gates element
  content by prospecting depth; deeper elements counted "à prospecter", never named. Aurelm
  models no tech-level — Demiurgos passes the depth. (3) **cedeTerritory** — a civ transfers
  provinces to another (diplomatic event, recipient discovers, ownership-validated). (4) the
  agent no longer **leaks tool-call syntax** — deterministic stripper + prompt directive.
- **Dogfood / first-run wizard — hardened this session, first-run NOT yet completed once.**
  Built + shipped `Aurelm-Setup-0.2.1.exe` and installed it on the dev machine. Wizard fixes,
  all TDD:
  - **Launcher cwd** (`b200bac`): dev `py -m bot` → "No module named bot" when the DB is outside
    the repo — resolve the repo root from the EXE, not the DB dir.
  - **Resumability** (`3e2d9f3`): an interrupted setup burned the single-use activation code;
    the wizard now resumes past activation when a key is already sealed.
  - **DB location picker** (`388c0f7`): native "Save As" to choose folder + filename.
  - **Ollama one-click install** (`8eda69d`): absent → download `OllamaSetup.exe` + silent
    install + pull the recommended model. **⚠️ the `/VERYSILENT` flag is UNVERIFIED** (Ollama is
    already installed on the dev machine) — isolated in `OllamaService.installerArgs`, needs a
    clean-machine run.
  - **Ollama auto-start** (`7461090`): installed-but-stopped (after a reboot) → START it, never
    prompt to reinstall.
  - **Full wizard walkthrough E2E** (`195c22c`): clicks Activation→Base→Discord→Analyse→complete
    with the services faked. This is the automated proof that replaces manual dogfood.
  - **State of the actual first-run**: NOT completed once yet (no secure-storage artifact
    persisted — verified). The wizard is one-time and persists (DPAPI per-user) once finished;
    the repeated re-dos were interrupted attempts + my repeated reinstalls. Everything is teed
    up (Ollama running, Discord bot `CIVJDR-ContextManager` token in `aurelm_config.json`):
    ~3 clicks (Ollama Revérifier → pick model → Terminer) to finish. **Alexi flagged "y'a
    toujours un pb" and deferred — investigate that before/at the next first-run.**
  - **Open (offered, not built)**: a **dev-seed bypass** — pre-fill/skip the wizard from the
    vault + `aurelm_config.json` so a dev/tester never sets up by hand. (A clean feature, not a
    fragile external DPAPI write — which was investigated and rejected.)
  - **Known bug (not fixed)**: `discord_service.dart` `verify()`'s blanket `catch (_)` masks the
    real error as "impossible de joindre Discord" (a 401 reads as network). Map 401→invalid,
    5xx→server, only SocketException→network.
- **Disk-full** (2026-07-28): C: hit 100% (a system issue, not this work — another session is
  clearing it). All map validation this session was in-memory. Watch for disk errors.

## Doctrine that held (keep it)
- **Verify every "done" on the wire.** The real Theomen exports caught 3 real bugs the
  fixtures hid (chunk-index, biomes-wrap, producer-block). Live probes catch what green unit
  suites miss.
- Cross-repo comms = paste-ready prompts Alexi relays (claude-duo was down). Sibling repos:
  `Gamedesigner/theomen`, `Demiurgos`.
- Branch → merge local (`--no-ff`) → push each remote separately (GitHub proxy 7897, Gitea no
  proxy). Commit after each tested change.

## Key files
- `bot/world_reader.py`, `bot/map_ingestion.py`, `bot/map_seeding.py`, the map tools in
  `bot/tools.py` (+ `tool_definitions.py`), migrations 041/042.
- `docs/map-tools-design.md` (the tools design + fog + turn transactionality),
  `docs/map-ingestion-plan.md` (ingestion + the real-format corrections).
- Contract (Theomen repo): `Gamedesigner/theomen/docs/{SPEC_WORLD_FORMAT,CONTRAT_EXPORT_AURELM}.md`.
- Memory: `project_map_ingestion_theomen_contract`.
