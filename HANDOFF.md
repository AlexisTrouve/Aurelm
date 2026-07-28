# Handoff — Aurelm (map system: ingestion + LLM tools + Demiurgos integration)

Paste-ready briefing. Everything is on `main` (`beaff9e`), pushed to GitHub + Gitea.
Bot suite: **231 passed / 4 skipped**. GUI: 61 unit + E2E green on `-d windows`.

## Headline: the MAP system is DONE and proven end-to-end

The chain is **Theomen (generates a world) → Aurelm (canon store + LLM tools) →
Demiurgos (grounds its GM)**. Aurelm's whole side is built, tested, and **validated on
the real complete Theomen v1 export**.

### 1. Ingestion (Theomen `.world` → `map_maps`/`map_cells`)
- `bot/world_reader.py` — pure-stdlib GMVC decoder (no numpy: the bot ships 5 deps).
  Generic over `manifest.fields`; handles the LSB presence mask, **partial edge chunks**,
  sparsity (absent≠0), and the **producer block** (business metadata `manifest["producer"]`).
- `bot/map_ingestion.py` — resolve index fields to names via sidecars, invert the
  log10-per-type resource densities + rank top-K, build the semantic per-cell record into
  `map_cells.metadata`, **crop-on-ingest** (decode the planet, write only the game's window),
  idempotent. CLI: `python -m bot.map_ingestion --db … --world … --map-name … [--window x,y,w,h]`.
- Migrations: 035 (`map_maps.metadata`), 036 (`map_cell_discovery`, fog).
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
- **Reads**: `groundCivTerrain` (fog-aware, relative directions), `findNearest`,
  `whatIsBetween`, `proposeSpawnPositions`, `getMapOverview` (a semantic SUMMARY, not a cell
  dump), + the pre-existing `getMaps`/`getTerritory`/`findEntityOnMap`/`getCell`/`getCellHistory`.
- **Writes**: `foundSettlement` (the socle), `expandTerritory`, `moveEntity`, `recordEvent`,
  `annotate`, `discoverAround`. All in `dispatch_tool`; all defer commit inside a turn.
- **Seeding**: `bot/map_seeding.py` — `propose_spawn_positions`, `place_civ`, discovery helpers.

### 3. Fog of war (V2, spatial)
`map_cell_discovery` per-civ; founding/expansion seed discovery, `discoverAround` explores,
`groundCivTerrain(fog=true)` reveals only discovered provinces (`fog=false`=GM omniscience).
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

### Proof (three levels)
- unit: 231 bot tests (`test_world_reader`, `test_map_ingestion`, `test_map_seeding`,
  `test_map_grounding`, `test_map_queries`, `test_map_writes`, `test_map_events`,
  `test_map_expand`, `test_map_fog`, `test_map_turn`).
- real bytes: `bot/tests/test_real_world_export.py` (opt-in) — the complete v1 export
  (`theomen/blog/world_aurelm_seed42.world`) decodes + ingests with full semantics.
- live LLM: `bot/tests/live_map_probe.py` — a real model drives grounding + writes on a rich
  world (chose the right tools, GM-quality answers, wove in agent memory).

## Open items
- **Demiurgos wiring** — its side: route its `aurelm_dispatch` through one turn connection.
  It will test against real grounding when a world is ingested — **ping it when there's a world
  to ground**.
- **Theomen SPEC doc is wrong** (code works on the real file, only the doc lies): tell Theomen
  its `SPEC_WORLD_FORMAT.md`/`CONTRAT_EXPORT_AURELM.md` should say metadata is in
  `manifest["producer"]` (not `world.json`) and sidecars are wrapped.
- **"feature discover" debt** — tech-gated content knowledge (parked, needs a model).
- **Minor map gaps** (low priority): `cedeTerritory` not built; `findNearest`/`whatIsBetween`
  are omniscient (not fog-aware); the agent occasionally leaks tool-call syntax to the user
  (a prompt-hygiene fix).
- **Parked dogfood** (from before the map cap-change): branch `fix/dev-launcher-cwd` (the
  first-run launcher fix, tested, `4c26ae8`) is **still unmerged**; and the wizard
  activation-resumability bug (interrupted setup burns the single-use code → user locked out)
  is unfixed. The dogfood is the real-signal item whenever it resumes.
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
  `bot/tools.py` (+ `tool_definitions.py`), migrations 035/036.
- `docs/map-tools-design.md` (the tools design + fog + turn transactionality),
  `docs/map-ingestion-plan.md` (ingestion + the real-format corrections).
- Contract (Theomen repo): `Gamedesigner/theomen/docs/{SPEC_WORLD_FORMAT,CONTRAT_EXPORT_AURELM}.md`.
- Memory: `project_map_ingestion_theomen_contract`.
