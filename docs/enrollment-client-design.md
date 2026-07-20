# Enrollment — Aurelm client design

> **Status**: design, not yet implemented. Companion to
> [`enrollment-api-handoff.md`](enrollment-api-handoff.md) (the proxy-side contract,
> **live + verified** on `ai.etheryale.com`). This doc covers the **Aurelm client**
> half: how Arthur activates the app on first run and how the key is stored and fed
> to the bot. Part of **Step 10 (deployment)**.

## Problem

Arthur runs a packaged Aurelm on his own machine. The chat agent needs an etheryale
proxy key (`eai_…`). We must get that key onto his machine **without shipping it inside
the installer** (a shared/re-hosted installer would leak the key everywhere it travels)
and **without storing it in plaintext** on disk.

## Decisions (locked)

1. **One-time enrollment code, not a bundled key.** Alexi (admin, PAT) mints a **code**;
   Arthur pastes it once at first run; the app redeems it for the real key. The key is
   born at redeem time (mint-on-redeem) — it never exists before Arthur activates.
2. **Storage = `flutter_secure_storage`** → Windows DPAPI. The ciphertext is sealed to
   Arthur's Windows login; the app carries **no** decryption key. Not a hand-rolled
   `auth.bin` (that would embed a recoverable key = obfuscation, not encryption).
3. **Generic installer, zero secret inside.** The code travels out-of-band (Alexi sends
   it once), never in the distributed artifact.
4. **Dedicated, revocable key per Arthur.** Revocation is immediate on the data-plane
   (verified: a revoked key → `403` on `/v1`). Optionally scoped to his own `group_id`
   for isolated bulk revocation.
5. **First-run wizard, run once.** A multi-step first-run wizard collects everything
   Arthur's instance needs — **(1)** activation code, **(2)** Discord token + channel↔civ
   mapping, **(3)** pipeline LLM choice (Ollama / OpenRouter). Activation is step 1. Once
   the wizard completes it never runs again.
6. **Internet is required exactly once, and the app never re-validates.** The wizard (the
   redeem + any one-time token/key test) is the *only* moment the app needs the network to
   set itself up. See "Behavioral rules" below — this is a hard requirement, not a nicety.

## Behavioral rules — internet once, no recurring validation

Hard requirement (Alexi): **the app requires the network exactly once — during the
first-run wizard — and never performs a recurring online validation of the key.**

- **First launch** → wizard runs (network required for the redeem + any one-time test).
- **Every later launch** → a **purely local** check: a `setup_complete` flag *and* a
  sealed key present in secure_storage. If both are true, the app goes straight in — **no
  call to the proxy to "check" the key, ever**, even offline.
- **The key is trusted once sealed.** If it is later revoked, Arthur finds out only when a
  chat request actually fails (`403`), shown as a friendly message with a "réactive avec un
  nouveau code" path — **not** via a startup gate.
- **Use-time internet ≠ validation.** Sending a chat message or syncing Discord needs the
  network *at the moment of use* (the proxy and Discord are remote) — that's the feature
  working, and it fails gracefully offline. It must **never** block opening or browsing the
  app: the existing DB / wiki / entities stay fully usable with no connection.

The gate condition is therefore **local state only** (`setup_complete` + key present), not
"is the key valid online". This is what keeps a launch offline-tolerant and instant.

## Architecture — Flutter owns the secret, the bot stays dumb

The pivotal point: **the Flutter app owns the key, the Python bot never touches secure
storage.**

```
Launch
   │
   ├─ setup_complete flag false? (local check, no network)
   │        │
   │        ▼  Wizard step 1 — activation: "Colle ton code d'activation"
   │     Dart POST /api/enrollment/redeem { code }        (one-time, Dart-side)
   │        │
   │        ▼  receives eai_… → secure_storage.write (DPAPI)   ← plaintext never hits disk
   │     ( → wizard steps 2 Discord, 3 pipeline → set setup_complete )
   │
   └─ setup_complete true → read sealed key locally, spawn the bot subprocess with
                            environment: { ETHERYALE_API_KEY: <key> }   (no online check)
```

Why this shape:

- **The bot stays trivial.** `bot/config.py` already reads `ETHERYALE_API_KEY` from the
  environment first (`os.environ.get("ETHERYALE_API_KEY") or data.get("proxy_api_key")`).
  So Flutter just injects it into the subprocess env — **no DPAPI binding needed in
  Python**, no key file for the bot to read.
- **The redeem is a Dart call**, done once at setup, before the bot even starts.
- **The key lives only in** `secure_storage` (sealed) **and** the bot subprocess env
  (in-memory, at runtime). Never in a plaintext file, never in `aurelm_config.json`,
  never committed.

## Proxy contract (reference — see the handoff for full detail)

Base `https://ai.etheryale.com`. Two endpoints, both live + verified:

- **Mint (admin, `Authorization: Bearer <JWT|PAT>`)** — *Alexi only, not the app*
  `POST /api/enrollment { name, ttl_hours?, group_id? }` → `{ code, expires_at, id }`.
  `ttl_hours` default 72.
- **Redeem (public, no auth — the code is the bearer)** — *the app*
  `POST /api/enrollment/redeem { code }` → `{ apiKey, key_id }`. **Single-use**: the
  `apiKey` is returned exactly once; a second redeem of the same code → `400`.

**Code format** (verified): ~41 chars, `LABEL-XXXX-…-XX`, ~129 bits entropy, alphabet
without ambiguous chars. **The client must NOT validate with a fixed-length regex** —
accept `^[A-Z0-9]+(-[A-Z0-9]+)+$` or don't validate at all; the server normalizes
trim + uppercase.

**Redeem errors are deliberately indistinguishable** (anti-enumeration): unknown /
expired / already-consumed all return the same `400 "Code invalide ou déjà utilisé"`.
Rate-limited to 10/min per IP (`429`). → **One UX message** for any failure: *"Code
invalide ou déjà utilisé — demande un nouveau code."* Never build logic on the
expired-vs-consumed distinction; it doesn't exist in the response.

## Components to build

| Piece | File(s) | What |
|---|---|---|
| Dependency | `gui/pubspec.yaml` | add `flutter_secure_storage` |
| Key store | `gui/lib/services/key_store.dart` (new) | thin wrapper over secure_storage: `readKey()`, `writeKey()`, `hasKey()`, `clear()` (DPAPI-backed on Windows) |
| Enrollment | `gui/lib/services/enrollment_service.dart` (new) | `redeem(code)` → `POST /api/enrollment/redeem`, returns key or a typed failure |
| Wizard shell | `gui/lib/screens/onboarding/setup_wizard.dart` (new) | multi-step first-run: **(1)** activation → **(2)** Discord token + channel↔civ mapping → **(3)** pipeline LLM choice → finish writes config + a local `setup_complete` flag |
| Activation step | `gui/lib/screens/onboarding/activation_step.dart` (new) | paste-friendly single field, redeem, single generic error, on success → seal key |
| Setup flag | `gui/lib/services/key_store.dart` (or a small prefs entry) | `setupComplete` — local only; the wizard sets it, the router reads it |
| Router wiring | `gui/lib/core/router/app_router.dart` | redirect to the wizard when `setup_complete` is false; otherwise straight to the app. **Never** an online check — local state only |
| Env injection | `gui/lib/services/bot_service.dart:25` | add `environment: { 'ETHERYALE_API_KEY': key }` to `Process.start` (Dart merges with the parent env by default) |
| Pipeline key seam | `bot/config.py` (`pipeline_llm_key`), `bot/main.py`, `bot/server.py` | ✅ done. **Corrected from an earlier draft**: do NOT collapse the pipeline key into the agent's. The proxy routes per key and spreads load across upstream accounts ("one key per agent", INTEGRATION §3), so a distinct pipeline key is deliberate. The duplicated per-provider expression (it existed in *two* places) is now one property, which prefers a dedicated key and falls back to the agent's only when unset |
| Re-enroll (opt.) | Settings | a "re-activer / changer la clé" action for the key-lost / rotation case — reuses the same redeem flow |

## Edge cases / UX

- **Key lost or reinstall**: there is **no re-redeem** (the code is consumed). The gate
  must say *"demande un nouveau code à l'admin"*, never a silent retry loop. Alexi mints
  a fresh code.
- **Redeem network failure vs bad code**: `429` → "réessaie dans une minute"; any other
  non-200 → the single generic "code invalide" message.
- **Paste UX**: one field, not four boxes. Tolerate spaces/case (server normalizes).
- **Offline first-run**: redeem needs the network. If offline, the gate says so and lets
  Arthur retry — the app can't start without a key anyway.

## Security properties

- Key at rest: DPAPI-sealed, bound to Arthur's Windows account → an `auth`-file lifted to
  another machine is useless.
- Key in transit onto the machine: only ever as a one-time, expiring, non-sensitive
  **code** (not the key itself); over an out-of-band channel, not the installer.
- Key at runtime: secure_storage + subprocess env only. No plaintext file, nothing in the
  repo, nothing in `aurelm_config.json`.
- Blast radius of a leak: one dedicated, revocable key → `DELETE /api/keys/:id` (or
  disable the group) kills it in isolation, effective immediately (`403` on `/v1`).

## Out of scope (for now)

- **Enrollment status endpoint** (`GET /api/enrollment/:id`) — the proxy offered it; not
  needed for a single user (we know Arthur activated when the chat works). Revisit for a
  real multi-client onboarding.
- **One-time enrollment on the pipeline's OpenRouter key** — if Arthur picks OpenRouter
  for ingestion, that's a separate key with its own (simpler, manual) setup; not folded
  into this flow yet.

## Testing plan

- **Unit**: `key_store` round-trip; `enrollment_service.redeem` against mocked 200/400/429.
- **E2E (real)**: mint a throwaway code with the vault PAT
  (`run-secure.py -e APIs/ETHERYALE_PAT`), drive the gate in an integration_test, assert
  the key lands in secure_storage and the bot starts with it — then revoke the test key.
  (The full mint→redeem→`/v1` 200→single-use→revoke loop is already proven at the API
  level; this extends it through the Flutter gate.)
