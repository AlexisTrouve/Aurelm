# Handoff — Chat agent → Etheryale proxy (branch `feat/chat-etheryale-proxy`)

> Paste-ready briefing for the next worker. The GM chat agent was migrated from a
> three-backend setup to a **single OpenAI-compatible client** pointed at the
> **etheryale proxy**. Done in 2 phases, **fully validated end-to-end (UI included)**,
> **not yet merged to main**.

## What this is

The bot's chat agent used to have **three** LLM backends: the Anthropic SDK
(`claude-sonnet-4-6`), Ollama (local), and a `claude -p` CLI fallback. This rework
**collapses all three into ONE**: the etheryale proxy at
`https://ai.etheryale.com/v1` — an **OpenAI-compatible** surface fronting *every*
model (Claude **and** GPT). Because the proxy only speaks OpenAI Chat Completions
(even to reach a Claude model), the agent switched from the **Anthropic SDK to the
OpenAI SDK**.

Result: the GM can pick any proxy model from a Flutter dropdown; answers stream
token-by-token; extended thinking is used on Claude models; `claude -p` and Ollama
are gone from the agent.

## Status

- Branch `feat/chat-etheryale-proxy`, **2 commits, NOT merged**:
  - `84a43fa` — Phase 1 (backend)
  - `78974c5` — Phase 2 (Flutter + a backend leftover fix)
- Merge was intentionally **deferred** (Alexi asked for this handoff instead). Next
  step is a PR → merge; the CI E2E (`app_boot`) will re-build the whole app.

## Read first

- **`C:\Users\alexi\Documents\projects\EtheryaleProxytator\LeCodeurFou\docs\INTEGRATION.md`**
  — the proxy contract (auth, models, thinking ext, rate-limit behaviour). Source
  of truth. `GET /help` on the proxy is the live runtime reference.
- `bot/agent.py` — the reworked agent (the whole thing; ~350 lines, was ~905).
- `CLAUDE.md` — the etheryale test key lives there (dev-only, see Prod below).

## Hard rules / key facts

1. **OpenAI SDK, not Anthropic.** The proxy is OpenAI-compatible; use
   `openai.AsyncOpenAI` / `OpenAI`. Do NOT reintroduce the `anthropic` SDK for the
   agent (still a `bot/requirements.txt` — no: it was replaced by `openai`).
2. **Auth is `x-api-key`, NOT `Authorization: Bearer`.** The client sets
   `default_headers={"x-api-key": key}` (the SDK still sends Bearer too; the proxy
   reads x-api-key).
3. **The proxy QUEUES, never 429.** Client timeout is **300s** and
   `max_retries=0` — do not add aggressive client-side retries.
4. **Thinking is Claude-only**, sent as `extra_body={"thinking": {"type":
   "enabled", "budget_tokens": N}}`, gated by `_is_claude(model)`. The proxy
   translates it (opus-4-8 doesn't 400). Note: on opus-4-8 the thinking *text* is
   omitted (runs, but not displayed); sonnet-4-6 / opus-4-6 would display it.
5. **Session history is already OpenAI-shaped** — `sessions.build_llm_history()`
   returns plain `{role, content}` text messages (no Anthropic blocks). Only the
   intra-turn tool loop uses OpenAI tool messages (`role:"tool"` + assistant
   `tool_calls`). There is **no client-side compression** anymore (the proxy caches
   server-side); `raw_tokens == compressed_tokens`.
6. **`gpt-image-2` is deliberately NOT wired** (image generation). The agent only
   drives *chat* models (claude-\* + gpt-5.6-\*). Don't select it as the agent model.

## What's delivered

### Phase 1 — backend (`bot/`)

- **`agent.py`** rewritten: `AsyncOpenAI` for the streaming main loop
  (`answer_streaming`, yields `text_delta` events), `OpenAI` (sync) for `deepExplore`
  (runs in a worker thread). `answer()` kept for the Discord path. `list_models()`
  for the picker. `summarize_for_compress` on the proxy. Removed the
  anthropic/ollama/claude-p paths, `answer_in_conversation`, `OLLAMA_SYSTEM_PROMPT`.
- **`config.py`**: `proxy_base_url` / `proxy_api_key` (env `ETHERYALE_API_KEY`) /
  `model` (default `claude-opus-4-8`) / `thinking_budget` (4000) / `request_timeout`
  (300) + `has_llm`. The old `anthropic_*` / `ollama_model` fields **stay** — they're
  used by the **pipeline ingestion path**, not the agent.
- **`tools.py`**: `deepExplore` sub-agent rewritten to OpenAI/proxy;
  `dispatch_tool` param `anthropic_client` → `llm_client` + `model`.
- **`server.py`**: `GET /chat/models` (picker source); `POST /chat` accepts a
  `model` override.
- **`main.py`**: agent created only when `has_llm`. **`requirements.txt`**: −anthropic
  +openai.

### Phase 2 — Flutter (`gui/`)

- **`chat_service.dart`**: parse `text_delta` (live tokens before the final `text`);
  `sendMessageStream(..., model)`; timeout 300s; `fetchModels()`; dropped
  `FallbackEvent`.
- **`chat_provider.dart`**: `TextDeltaEvent` appends + re-renders the bubble;
  `chatModelsProvider` + `selectedModelProvider`; `ChatNotifier.setModel`; removed
  `usedFallback` + the fallback case.
- **`chat_screen.dart`**: `_ModelPicker` app-bar dropdown (from `/chat/models`);
  removed the claude-p toast.

## Validated (real, not "should work")

- **Backend, real proxy traffic**: `claude-opus-4-8` (with & without thinking) and
  `gpt-5.6-luna` (cross-provider) — tool loop, token streaming, `/v1/models` all green.
- **Bot contract**: `GET /chat/models` → 9 models + default; `POST /chat` (with a
  model override) streams `tool_start/tool_result/text_delta/text/done`, **0 error**.
- **Full UI E2E (headless)**: booted the Flutter app against a live bot on `:8473`,
  navigated to `/chat`, and screenshotted a real turn — the model picker shows
  `claude-opus-4-8`, the user bubble + `listCivs` tool card + a **streamed Markdown
  table** answer all render. Screenshot: `gui/integration_test/fixtures/chat_after.png`
  (gitignored).
- **116 bot tests pass**; `dart analyze` clean on the 3 changed Flutter files.

## How to run / validate (from `Aurelm/`)

```bash
# Start the bot on the app's default port with the etheryale key + a real DB:
ETHERYALE_API_KEY="<eai_ key>" py -3.12 -m bot --db aurelm_clean.db --port 8473
# Sanity:
curl -s http://127.0.0.1:8473/chat/models
curl -s -X POST http://127.0.0.1:8473/chat -H "Content-Type: application/json" \
  -d '{"message":"Combien de civilisations ?","model":"claude-opus-4-8"}'
```

A standalone agent harness (drives `answer_streaming` directly, prints events) is
in the session scratchpad as `validate_agent.py` (test key inline).

## Gotchas

- The **chat E2E cannot be committed as a CI test** — it needs a live bot + the
  proxy. The committed `app_boot` E2E suite covers the other screens; it re-builds
  the whole app (so it *will* catch a chat compile break) but does not exercise chat.
- The Windows Flutter build has a known **first-build-after-clean race** — retry.
- `chat_screen.dart` is still a **2114-line monolith** (rewrite-candidate, self-flagged
  TODO at its top). This rework touched it surgically; a real decomposition is future work.

## Still open (don't build without asking)

- **Merge** `feat/chat-etheryale-proxy` → main (PR → merge; CI validates the build).
- **Prod key flow for Arthur**: the `eai_` test key in CLAUDE.md is **dev-only**. Prod
  needs the proxy's `login → POST /api/keys` flow (or a per-agent key, cf.
  INTEGRATION §3) wired into config (`ETHERYALE_API_KEY` env or `proxy_api_key` in
  `aurelm_config.json`). This is Step 10 (deployment) territory.
- **Thinking display**: opus-4-8 runs thinking but omits the text. If visible
  reasoning is wanted in the UI, use a model that displays it, or check whether the
  proxy can expose `display: "summarized"`.
- **Multi-agent keys** (INTEGRATION §3): 1 key per agent for sticky routing — not
  wired (single key today). `deepExplore` shares the main key.
