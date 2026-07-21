# Handoff — Aurelm (Step 10 done + reviewed, chat on the proxy)

Paste-ready briefing for the next session. Everything below is on `main` (`ec05e89`),
pushed to GitHub + Gitea.

## State: what's done

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

- **Step 9 — in-app Flutter force-directed graph is still unusable.** The only
  substantive open feature. (The headless `exporters graph` ego-graph is a separate,
  usable render, not a GUI fix.)
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

- `docs/deployment.md` — the whole Step 10 system (read first).
- `docs/enrollment-api-handoff.md` + `enrollment-client-design.md` — the activation flow.
- `bot/`, `gui/lib/services/{key_store,enrollment_service,discord_service,ollama_service}.dart`,
  `gui/lib/screens/onboarding/setup_wizard.dart`, `scripts/build_distribution.ps1`,
  `scripts/installer.iss`.
- Memories: `reference_etheryale_proxy_llm_contract`, `reference_aurelm_dual_push_network_regime`.

## Test surface

- `python -m pytest bot/tests/` — 135. `cd pipeline && pytest` — full suite incl.
  `test_llm_provider_auth`. `cd gui && flutter test test/` — unit incl. ollama parse +
  launcher resolution. `flutter test integration_test/app_boot_test.dart -d windows` — 8.
