# Handoff — Aurelm (memory + prompt + update distribution + agent-tool hardening)

Paste-ready briefing for the next session. Everything below is on `main` (`174d8b1`),
pushed to GitHub + Gitea. Bot suite: 180 passed / 2 skipped. GUI: 61 unit, E2E green on `-d windows`.

## State: what's done

- **Agent tools hardened + endpoint-probed — DONE** (`16ce0ed`, `3cf2a24`, `c9ecd80`,
  `174d8b1`). Fixed the three real defects a code-read recon had surfaced:
  (1) `deepExplore` no longer discards its research when the token-budget warning fires
  (nudge for a written conclusion, then fall back to the collected findings);
  (2) relation-following is multi-hop again — `getEntityDetail(relationDepth=2..3)`
  routes to `explore_relations` (advertised in schema **and** SOUL), and the relation
  **description** (the *why*) is now shown instead of dropped;
  (3) list tools no longer truncate silently — `searchLore`/`timeline`/
  `searchTurnContent`/`listSubjects` fetch `limit+1` and the notice carries the **real
  COUNT** ("20 affiches sur 41 au total. N'EXTRAPOLE PAS").
  **How they were verified: `bot/tests/live_agent_probe.py`** — boots `python -m bot`,
  POSTs to `/chat`, prints the tools the agent actually chose. It found TWO bugs a green
  unit suite had missed: a `/chat` `UnboundLocalError` (tool_calls used before assign)
  that **masked every upstream error** with a fake one, and the count-invention above.
  Run it: `PYTHONIOENCODING=utf-8 py -3.12 bot/tests/live_agent_probe.py` (needs the
  proxy env, i.e. do NOT clear HTTPS_PROXY — the SDK uses it here).
  Still not fixed (lesser, they degrade rather than lie): `compareCivs` lacks a
  diplomacy/religion aspect; `getStructuredFacts(all)` has no row cap.

- **Update distribution — DONE.** `dist.etheryale.com` (VPS142, nginx static, TLS,
  grey-cloud) serves a `latest.json` manifest + the installer; the app checks it
  **automatically at startup**, from a banner mounted **above the activation gate** (so
  even a wizard-stuck instance is offered fixes), verifies the **sha256** before running
  anything, stops the bot and exits so the upgrade can replace locked files.
  `scripts/publish_release.ps1` builds, hashes, uploads over Tailscale, **fetches the
  manifest back and parses it** before declaring success. Proven end-to-end: real
  0.1.0→0.1.1 in-place upgrade (activation + DB + a file inside `{app}` all survived,
  migrations caught up), the one-click install E2E on `-d windows`, and a hostile
  wrong-hash case. **Doc: `docs/distribution.md`.** Two traps recorded there:
  `.ps1` must be ASCII-only (5.1 reads ANSI); PowerShell 5.1 strips `"` from native-cmd
  args (the manifest travels as a *file*, never a shell argument).

- **Agent memory layer — DONE** (PRs #18-21, + `discoverMemory`, memory→article links). The agent keeps **its own memory**,
  written from Arthur's feedback (`editMemory`: create / update / forget) and
  **recalled per request** with its key and turn anchor surfaced; memories take
  precedence over pipeline data; Arthur reviews them in Settings → *Mémoire de
  l'agent*. It also fixed the agent's biggest structural weakness — the system prompt
  used to be assembled **once at startup**, static and blind to the question.
  **Read `docs/agent-memory.md` first** — it holds the full reference AND the approved
  implementation plan for the two next pieces (`discoverMemory`, memory→DB links).
  **Known gap:** whether a live model actually calls `editMemory` at the right moments
  is *unproven* — machinery is tested, behaviour is not. A live-LLM test / dogfood is
  the recommended next validation.

- **Step 9 — in-app graph: DONE** (PR #16, `00d3cd6`). The "force-directed unusable"
  premise was stale — that version died at `4b79a52` (already a radial ego-graph on
  `main`). This round polished the real rough edges: auto-fit framing (fill the pane /
  never clip, replacing the fixed 220/340px caps), edge-label declutter, larger labels.
  Proof: 6 RED→GREEN pure-layout tests + a new E2E click-through (`EgoPainter` actually
  paints, 9/9 on `-d windows`) + a real-font render. **Lesson: re-verify handoff
  "unusable" claims against a live render before rebuilding.**
- **Pipeline `exclude_entity_types` — DONE** (PR #17, `9bfca5f`). `run_pipeline(...,
  exclude_entity_types=["technology"])` suppresses an entity type at the ontology gate
  (`FactExtractor.allowed_entity_types` → `_coerce_entity_list`), dropped at extraction,
  cascade-free by construction. Default `None` = unchanged. Built for the Aurelm↔Demiurgos
  split (Demiurgos owns curated technology extraction). Full doc + integration contract:
  **`docs/exclude-entity-types.md`**; memory `project_aurelm_demiurgos_technology_split`.

- **Chat agent → etheryale proxy** (PRs #4-6). One OpenAI-compatible client
  (`ai.etheryale.com/v1`, `x-api-key`) fronting all Claude + GPT. No Anthropic SDK,
  no `claude -p`. Per-request model picker + `reasoning_effort` + `include_reasoning`
  toggle. Contract + traps: **`docs/deployment.md`** and the memory
  `reference_etheryale_proxy_llm_contract`.
- **Step 10 — deployment, done + adversarially reviewed** (PRs #7-15). Self-contained
  Windows installer (`Aurelm-Setup.exe`: Flutter EXE + embedded CPython + `bot/` +
  `pipeline/pipeline/` + `database/`). 4-step first-run wizard: activation code →
  DB migrate → Discord bot + channel↔civ mapping → Ollama/OpenRouter + in-app model
  download. All secrets DPAPI-sealed, injected into the bot subprocess env. **Full
  reference: `docs/deployment.md`** (read it first).
- **4-agent adversarial review** ran on the Step 10 code; all real findings fixed
  (privacy leak — installer no longer ships dev DBs/corpora; Settings no longer
  writes secrets to config; Ollama detection; Discord/activation error handling; bot
  re-entrancy; claude_proxy x-api-key; launcher tests). See PR #13.
- **Thinking thread — closed.** opus-4-8/sonnet-5 reason *adaptively* (visible only on
  hard questions, 0 on trivial — correct); haiku-4-5 always shows. sonnet-5 was
  genuinely broken proxy-side (treated as classic budget) → fixed proxy-side +
  verified. Aurelm needed no wiring change; only an honest empty-state note (PR #15).

## Open items

- **Dogfood — THE one open item that matters.** Everything is built, tested, endpoint-
  probed and now auto-updatable — and **nobody has ever used it**. Arthur has never run
  the installer. Every further feature is guesswork until he does; the next real signal
  comes from him, not from another test I write. Blocker: he needs an **activation
  code**, which only Alexi can mint (via the etheryale proxy enrollment).
- Small, evidenced, left undone (they degrade, they don't lie): `compareCivs` has no
  diplomacy/religion aspect though the tag vocabulary defines them; `getStructuredFacts
  (factType="all")` has no row cap and can flood context.
- Agent behaviours not yet seen live: memory `links` and `forget=true` (`discoverMemory`,
  `editMemory`, multi-hop, relation-detail, truncation-count all confirmed via the probe
  / live-LLM tests). See `docs/agent-memory.md` → "What is still unverified".
- `chat_screen.dart` is a **2114-line monolith** — rewrite candidate (self-flagged).
- `claude_proxy` pipeline provider is fixed but **dormant** (not exposed in the
  wizard; Arthur uses ollama/openrouter).
- **Remaining is user-side** (the wizard guides + verifies it): Arthur creates his
  Discord app + enables Message Content, installs Ollama if he picks it.

## Doctrine that held all session (keep it)

- **Low-trust: verify every "done" on the wire yourself.** It caught the sparse
  `tool_calls` crash, the migrations-not-shipped bug, the installer privacy leak, and
  two proxy "deployed" claims that hadn't (once mine was wrong too — opus wasn't
  broken, my test prompt was too easy). Test key: `eai_ESu-8usnN17_6I09zZ2F5A15rGnrZVfQ`
  (dev-only, direct use authorised per CLAUDE.md).
- Branch first, PR, verify CI before merge. Commit after each tested change.

## Ops gotchas (these bite; all in memory `reference_aurelm_dual_push_network_regime`)

- **Dual-push, opposite regimes**: GitHub needs the proxy
  (`git -c http.proxy=http://127.0.0.1:7897 push https://github.com/AlexisTrouve/Aurelm.git`),
  Gitea (`git.etheryale.com`, the VPS) must **NOT** use the proxy. Push each remote
  separately; both flake on TLS EOF — retry. The CLAUDE.md line saying one push does
  both is stale.
- **Flutter version skew**: dev 3.38, **CI builds on 3.27.4**. Local analyze/debug can
  pass on newer-SDK APIs the CI release rejects (`DropdownButtonFormField.value` not
  `initialValue`). CI is authoritative.
- **sqlite3 native-asset DLL**: `flutter build/test -d windows` downloads
  `sqlite3.x64.windows.dll` from GitHub; Dart ignores `HTTPS_PROXY` so it fails
  locally. Seed the verified DLL into
  `gui/.dart_tool/hooks_runner/shared/sqlite3/build/download-*/` (hook accepts by
  sha256). CI is fine.
- **`Test GUI` CI is red** since 2026-07-12 on pre-existing analyzer warnings (~86) in
  files unrelated to recent work; it also skips its test step. **Build + E2E are the
  real gates.** Before merging, confirm your branch's files add 0 analyze issues.
- **Vault-daemon (VPS142) is intermittent/down.** It scopes the GitHub API token
  (`run-secure.py -e Git/GITHUB_TOKEN`) used for PR create/merge, and secret injection.
  When it's down: `git push` still works (Git Credential Manager, local), so you can
  **merge locally** (`git checkout main; git merge --no-ff <branch>; push both remotes`)
  instead of the API. There is NO GitHub token in the local `.env` fallback.

## The proxy relationship

`EtheryaleProxytator` is a sibling repo, worked by another Claude. Cross-project comms
= **paste-ready prompts/reports Alexi relays** (worked 4× this session), or claude-duo.
The proxy queues (never 429) → 300s client timeout, no retry. `x-api-key` not Bearer.
`GET /help` = live runtime contract (currently v1.9). Thinking is adaptive on the newest
models — test with a HARD prompt if verifying.

## Key files

- `docs/agent-memory.md` — the agent memory layer + the approved plan for the next two pieces.
- `docs/distribution.md` — how updates reach Arthur (dist.etheryale.com, publish script, integrity rules).
- `docs/deployment.md` — the whole Step 10 system (read first).
- `docs/exclude-entity-types.md` — the pipeline type-exclusion feature + Demiurgos contract.
- `docs/enrollment-api-handoff.md` + `enrollment-client-design.md` — the activation flow.
- `bot/`, `gui/lib/services/{key_store,enrollment_service,discord_service,ollama_service}.dart`,
  `gui/lib/screens/onboarding/setup_wizard.dart`, `scripts/build_distribution.ps1`,
  `scripts/installer.iss`.
- `bot/tests/live_agent_probe.py` — manual endpoint probe (drives `/chat` on a real bot).
- Memories: `reference_etheryale_proxy_llm_contract`, `reference_aurelm_dual_push_network_regime`.

## Test surface

- `python -m pytest bot/tests/` — **180 / 2 skipped** (the 2 skipped are opt-in live-LLM,
  `AURELM_LIVE_LLM=1`). `cd pipeline && pytest -k "not _real"` — ~274 / 5 skipped.
  `cd gui && flutter test test/` — **61 unit**.
  `flutter test integration_test/app_boot_test.dart -d windows` — 11;
  `... integration_test/update_flow_test.dart -d windows` — 3 (one-click update).
- Opt-in live checks (real network/LLM, not in the default run): `AURELM_LIVE_LLM=1`
  (memory behaviour), `AURELM_LIVE_DIST=1` (real dist host), and the probe above.

## Ops gotchas learned THIS session (add to the standing list)

- **`.ps1` must be ASCII-only** — Windows PowerShell 5.1 reads them as ANSI with no BOM,
  so a UTF-8 em-dash in a `"…"` string terminates it early and the file won't parse.
- **PS 5.1 strips `"` from native-command arguments** — pipe JSON through `ssh "printf…"`
  and the quotes vanish (looked fine, unparseable on arrival). Transfer as a file.
- **Local shell has `HTTPS_PROXY=…:17898`** which httpx (the OpenAI SDK) honours; a bot
  turn from here fails `Connection error` if that points nowhere. The etheryale proxy
  itself is reached fine via it — do NOT blanket-clear it when probing the agent.
- **A masking error hides its cause** — bind loop-scoped vars before the loop; the
  `/chat` UnboundLocalError replaced every real proxy error with a fake one.
