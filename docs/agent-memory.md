# Agent memory layer

The agent keeps **its own memory**, written from Arthur's feedback and recalled
automatically when relevant. This is the reference for what shipped (increments 1–3
+ the tool unification) and the plan for what's next.

Shipped: PRs #18, #19, #20, #21 (`main` at `0df2b8c`, 2026-07-22).

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
| `bot/tools.py` | `save_memory` / `forget_memory` + the `editMemory` dispatch |
| `bot/tool_definitions.py` | `editMemory` schema |
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

## Known gap (honest)

The **machinery** is proven end-to-end. What is **not** proven: that a live model,
given SOUL.md, actually calls `editMemory` at the right moments when Arthur corrects
it. That is behaviour, not mechanism — it needs a **live-LLM test or dogfood**. Treat
"the agent remembers Arthur's feedback" as *unverified* until then.

---

# Planned — implementation plan

~~**A. `discoverMemory`**~~ — **SHIPPED** (see "Read" above). One extension left.

## B. Links from a memory to database articles

**Why.** Anchoring a memory to the entities/turns/subjects it concerns grounds it in
the knowledge base: the agent can drill down (`getEntityDetail`) and Arthur can click
through in the UI.

**⚠️ The trap: entity ids are not stable.** `alias_resolver` **merges** entities —
it redirects mentions, relations, aliases and subjects from the secondary to the
primary and deactivates the secondary. A memory link stored as `entity_id=42` would
dangle onto a deactivated entity once 42 is merged into 7. **Memory links must be
added to that redirect list in the same change** — three lines now, a silent rot
otherwise.

**Shape**

```sql
-- migration 040
agent_memory_links(id, memory_id → agent_memory ON DELETE CASCADE,
                   entity_id?, subject_id?, turn_id?)   -- exactly one target set
```

The agent passes **names**, dispatch resolves them:
`editMemory(..., links: ["entity:Argile Vivante", "turn:12", "subject:18"])`.

**Steps**
1. `database/migrations/040_agent_memory_links.sql` — the table + indexes, FKs with
   `ON DELETE CASCADE`. *(No semicolons inside SQL comments — the migration runner
   splits on `;` before stripping comments.)*
2. `gui/lib/data/database.dart` `_ensureMigrations` — add the `CREATE TABLE IF NOT
   EXISTS` (Drift does not run SQL migrations).
3. `bot/tools.py` — `editMemory` gains `links`; resolve `entity:` by name/alias
   (fuzzy, like `getEntityDetail`), `turn:` by (civ, number), `subject:` by id.
   Links are **replaced** on upsert. Cap the count to bound recall cost.
4. `bot/agent.py` `_recall_memories` — join the links and render them inline
   (`→ liens : Argile Vivante (entity), T12`) so the agent knows what to drill into.
5. **`pipeline/pipeline/alias_resolver.py`** — add `agent_memory_links.entity_id` to
   the secondary→primary redirect, next to mentions/relations/aliases/subjects. **This
   is the mandatory step**, not an optimisation.
6. Flutter — repo loads links, the card shows them as chips (clickable navigation to
   the entity/turn/subject is a nice-to-have, not required for the first cut).
7. Tests — name→id resolution; recall renders links; **an alias-merge test proving a
   memory link follows the merge**; a gui E2E asserting a link chip renders.

**Cost**: moderate — migration + write path + recall + resolver fix + UI. The resolver
fix (step 5) ships **with** it, not after.
