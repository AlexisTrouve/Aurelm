# Agent memory layer

The agent keeps **its own memory**, written from Arthur's feedback and recalled
automatically when relevant — it can also read it back (`discoverMemory`) and tie a
memory to the database articles it concerns.

Shipped: PRs #18-21 (increments 1–3 + the tool unification), then `discoverMemory` and
memory→article links. 2026-07-22.

---

## Why it exists

Two problems it solves.

**1. The agent's context was static and blind.** The system prompt was assembled
**once at process start** (`Agent.__init__`): agent notes were frozen (a new note
needed a restart) and every note was injected regardless of the question. The model
burned a round on `listCivs`/`getCivState` just to orient. The lever on agent quality
was never "more tools" — it was *the right context at the right moment*.

**2. Extraction noise can't be fixed by prompting.** Pipeline entity extraction runs
~50–70 % precision on some types. A memory sourced from **Arthur** (a correction, a
ruling) is reliable by construction — and patches wrong pipeline data *at the point of
use*. That is why the memory is written from **GM feedback**, never auto-extracted:
auto-filling it from qwen would anchor the agent on noise, which is worse than nothing.

---

## Architecture

```
Arthur's feedback in chat
        │
        ▼
  editMemory  (agent calls it)  ──►  agent_memory table  (migration 039)
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
        _recall_memories (per request)                  Flutter review screen
        injects the RELEVANT ones into                  Settings → Mémoire de l'agent
        the system prompt, with key + anchor            (edit / forget / restore / delete)
```

### Storage — `agent_memory` (migration 039)

| column | meaning |
|---|---|
| `mem_key` | stable slug; **(mem_key, civ_id) is the upsert identity** |
| `description` | one-line summary, shown as the memory's title at recall |
| `content` | the fact / rule / preference |
| `civ_id` | scope; `NULL` = global |
| `mem_type` | `fact` (world ruling, recalled by relevance) or `preference` (how to answer, always injected) |
| `source_turn` | optional turn_id anchor — "as of T*n*" |
| `active` | `0` = forgotten (kept for the review trail, not recalled) |

Flutter opens the DB through Drift, which does **not** run the SQL migrations, so the
table is also created idempotently in `gui/lib/data/database.dart` `_ensureMigrations`.
Any new memory table must be added there too or `customSelect` throws "no such table".

### Write — `editMemory` (one tool does everything)

```
editMemory(key, content?, description?, type?, civName?, turnNumber?, forget?)
```

- **create / update** (default): upsert by `key` — re-calling with the **same key
  UPDATES**, so the agent *maintains* a memory instead of stacking duplicates.
- **forget** (`forget=true`): deactivates it (`active=0`), reversible.
- `turnNumber` is a turn **number**; dispatch resolves it to a `turn_id` for that civ
  (turn numbers are per-civ).

Hard delete is deliberately **not** exposed to the agent — that is Arthur's, in the UI.

### Read — `discoverMemory` (the pull counterpart)

```
discoverMemory(keys?, civName?, type?, includeInactive?)
```

Recall is **push-only**: it surfaces only what relevance pushes at the agent, so a
memory it doesn't surface is invisible — the agent could neither answer "what do I
already know?" nor look up the key of a memory it wants to correct. `discoverMemory`
is the pull side:

- **without `keys`** → a **compact inventory**: key, description, kind, scope, anchor —
  **no content**, so listing everything stays cheap in tokens.
- **with `keys: [...]`** → the **full entries** for exactly those keys. Keys that don't
  exist are reported explicitly (`Introuvable(s) : ...`) rather than silently dropped.
- `civName` / `type` filter; `includeInactive` also returns forgotten ones (marked).

SOUL.md tells the agent to use it when Arthur asks what it remembers, **before creating
a memory on a topic** (so it updates instead of duplicating under a new key), and to
find a key the recall didn't show.

### Links to database articles (migration 040)

A memory can point at the articles it concerns. The agent passes **names**, dispatch
resolves them to ids:

```
editMemory(..., links: ["entity:Argile Vivante", "turn:12", "subject:18"])
```

- `entity:` resolves by canonical name, then by alias (fuzzy) — the model knows names,
  not ids. `turn:` resolves by (civ, turn number), since turn numbers are per-civ.
  `subject:` is already a numeric id in the GM's vocabulary.
- Unresolvable specs are **skipped**, never stored as dangling rows. Capped at 8 links
  per memory so recall stays cheap.
- Links are **replaced** on every upsert (they describe the memory as it now stands).
- At recall they render under the memory: `→ liens : Argile Vivante, T12` — the agent's
  entry point to drill in (`getEntityDetail`, `getTurnDetail`, `getSubjectDetail`)
  instead of searching blind. The review screen shows them as 🔗 chips.

**⚠️ Entity ids are not stable — and that is handled.** `alias_resolver` merges entities
and deactivates the secondary, so a link stored as `entity_id=42` would rot onto a dead
article once 42 is merged into 7. `_redirect_memory_links` (in `alias_resolver.py`) is
called from **all three** redirect sites — the main merge, the orphan-pointer pass, and
`runner.py`'s dedup merge — right next to where mentions and relations are redirected.
It is tolerant of DBs predating migration 040. Tested in
`pipeline/tests/test_alias_resolver.py` (a link follows a merge; a missing table never
crashes a merge).

### Recall — `_recall_memories` (per request)

Runs on every request, before the model call, and appends to the system prompt:

```
## Mémoire de l'agent (rulings et préférences du MJ — font foi)

**Bronze de la Confluence** [confluence-bronze · dès T2]: Les Confluents n'ont pas de bronze.
```

Selection:
- `preference` → **always** injected (behavioural, applies to every answer).
- `fact` → injected only when **its civ is named** in the query or a **query keyword
  overlaps** the memory (a world ruling is topical, not always-on).
- inactive → never.

Two things are deliberately surfaced in the block:
- **the key** — so the agent can reuse it to correct or forget. Without it the agent
  cannot know a memory's key and would mint a new one on every correction, producing
  duplicates: the edit loop was mechanically present but unusable before this.
- **the anchor** (`dès T2`) — so it reasons about supersession (below).

The same pass also recalls **agent-type notes** (`_recall_agent_notes`, increment 1):
pinned or global notes always, civ-scoped ones only when relevant.

### Precedence and anchoring (SOUL.md)

- A memory **takes precedence over pipeline data** on conflict — the GM is right —
  but the agent must **flag the conflict** ("d'après ton ruling X ; la base disait Y").
- An **anchored** memory holds *from* T*n*. If pipeline data past T*n* diverges, the
  agent asks whether it evolved rather than asserting a stale snapshot. An anchored
  memory is an instantaneous truth, not an eternal one.
- An **unanchored** memory (preference, world rule) applies without reserve.

### Review — Flutter (`Settings → Mémoire de l'agent`)

`AgentMemoryScreen` lists every memory (active + inactive) with type/scope/anchor
chips; Arthur can **edit**, **toggle off** (same effect as the agent's forget),
**restore**, or **delete for good**. Backed by `AgentMemoryRepository` (raw SQL via
Drift `customSelect`/`customStatement`, no codegen) + `agentMemoryProvider`
(FutureProvider; raw-SQL tables aren't Drift-streamed, so writes call
`ref.invalidate`).

---

## Files

| path | role |
|---|---|
| `database/migrations/039_agent_memory.sql` | the table |
| `database/migrations/040_agent_memory_links.sql` | links to entities / turns / subjects |
| `bot/tools.py` | `save_memory` / `forget_memory` / `discover_memory` / `_set_memory_links` + dispatch |
| `bot/tool_definitions.py` | `editMemory` + `discoverMemory` schemas |
| `pipeline/pipeline/alias_resolver.py` | `_redirect_memory_links` — keeps entity links alive across merges (called from all 3 redirect sites, incl. `runner.py`'s) |
| `bot/agent.py` | `_recall_agent_notes`, `_recall_memories`, injection into both answer paths |
| `bot/prompts/SOUL.md` | when to memorise, key reuse, precedence + anchoring |
| `gui/lib/data/repositories/agent_memory_repository.dart` | raw-SQL repo |
| `gui/lib/providers/agent_memory_provider.dart` | providers |
| `gui/lib/screens/settings/agent_memory_screen.dart` | the review screen |
| `gui/lib/data/database.dart` | `_ensureMigrations` self-heal entry |

## Tests

- `bot/tests/test_agent_memory.py` — write/upsert/forget, per-civ key scoping, recall
  gating (preference always / fact relevance), anchoring, key surfacing, dispatch wiring.
- `bot/tests/test_note_recall.py` — note recall incl. an end-to-end wiring lock (the
  recalled note reaches the real system message sent to the proxy).
- `gui/integration_test/app_boot_test.dart` — the review screen renders the fixture's
  memories (incl. the `dès T2` anchor chip) and a real delete removes the row.

Totals at time of writing: **156 bot**, **11 gui E2E** (`-d windows`), **41 gui unit**.

## Behaviour — verified live

`bot/tests/test_agent_memory_live.py` drives **real turns through the proxy** (opt-in:
`AURELM_LIVE_LLM=1`, skipped by default so the suite stays fast and offline). Two cases,
both green on `claude-opus-4-8`:

| case | result |
|---|---|
| Explicit ("… le bronze exige de l'étain. **Retiens-le**.") | called `editMemory` and only that; wrote `regle-bronze-etain` as a `fact` with a description; the recall block then surfaced it with its key |
| **Implicit** ("Non, tu te trompes : les Confluents n'ont jamais eu de bronze…") | also called `editMemory`; wrote `confluence-metallurgie-cuivre` as a `fact` **scoped to civ 1** — it resolved "les Confluents" on its own |

So the model does act on GM feedback, including without being told to remember, and
picks sane keys/types/scopes.

### What is still unverified

- **The other tools in situ**: `discoverMemory`, `links`, and `forget=true` are
  mechanically tested but no live turn has been observed choosing them.
- **Behaviour over time**: whether it re-uses a key on a second correction (rather than
  minting a new one) across a long session, and whether it over-memorises.
- Only one model, low effort, single-turn. Treat those as sampled, not proven.

*(Ops note: the proxy flaked twice with transient `Connection error` during this run —
VPS142 was intermittent. A failing live test may be infrastructure, not logic. Re-run
before concluding.)*

---

# Planned

Nothing outstanding on the memory layer itself — increments 1-3, `discoverMemory` and
memory→article links have all shipped, and the write path is now verified live (see
"Behaviour — verified live").

The remaining unverified items are narrower now: live use of `discoverMemory` / `links`
/ `forget`, and behaviour over a long session. Listed under "What is still unverified".
