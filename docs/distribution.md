# Distribution and updates

How a new Aurelm reaches Arthur's machine. Server on VPS142, client in the app,
one script to publish.

Live since 2026-07-23: **https://dist.etheryale.com/aurelm/**

---

## Why an update path at all

Step 10 shipped an installer, not a lifecycle: there was no way to get a fix to Arthur
short of telling him to re-download something that lived nowhere. Everything needed for
an in-place upgrade was already true, though — it just had no trigger:

- the installer has a **stable AppId** and installs **per-user** under `LocalAppData`,
  so re-running a newer one upgrades in place with **no UAC prompt**;
- **activation survives**: the enrollment key, Discord token and `setupComplete` flag
  live in the Windows credential store (`flutter_secure_storage`), *outside* the install
  directory. An upgrade cannot force a re-enrollment — which matters because the
  activation code is single-use and Arthur would be locked out;
- the **DB is a user-chosen path**, not inside `{app}`, so the file copy never touches it;
- **migrations catch up by themselves** (auto-applied on bot start + the Drift
  `_ensureMigrations` self-heal), so an older DB is upgraded on first launch.

## Server (VPS142)

Plain static files behind nginx — no backend, nothing to keep running.

| | |
|---|---|
| DNS | `dist.etheryale.com` → `142.44.139.223`, **grey cloud** (proxied=false), matching `artifact.etheryale.com` |
| vhost | `/etc/nginx/sites-available/dist.etheryale.com`, root `/var/www/aurelm-dist` |
| TLS | Certbot (Let's Encrypt), HTTP→HTTPS redirect |
| files | `/var/www/aurelm-dist/aurelm/{latest.json, Aurelm-Setup-X.Y.Z.exe}` |

Cache policy is deliberate: `latest.json` is `no-cache, must-revalidate` (announcing a
new build is the entire point), installers are `immutable, max-age=1y` (a given version
never changes). `X-Content-Type-Options: nosniff`, `server_tokens off`.

Grey cloud means **no Cloudflare in front**, so the ~90 MB installer is served straight
from nginx — no proxy size or caching limits to worry about.

### Manifest format

```json
{"version":"0.2.0",
 "url":"https://dist.etheryale.com/aurelm/Aurelm-Setup-0.2.0.exe",
 "sha256":"<64 hex>",
 "notes":"one-line changelog shown in the app",
 "published":"2026-07-23T10:00:00Z"}
```

## Publishing

```powershell
pwsh scripts/publish_release.ps1 -Notes "Mémoire de l'agent + liens"
pwsh scripts/publish_release.ps1 -DryRun          # build + hash, publish nothing
```

It builds, hashes, uploads over **Tailscale** (`debian@100.85.89.83` — the public IP is
not reachable from every network), re-hashes the **remote copy** before announcing it,
then writes the manifest.

**Order is not cosmetic**: binary first, manifest last, written atomically
(`tmp` + `mv`). A manifest naming a binary that is still uploading would make every
client download a truncated file and fail its hash check, for as long as the upload runs.

## Client

`gui/lib/services/update_service.dart` (transport + integrity),
`gui/lib/providers/update_provider.dart` (the flow), and two views over it:
a slim **banner in the app shell** and the "Mises à jour" card in Settings. The
download/verify/install flow exists **once**, in the controller.

**The check is automatic, at startup.** Mounting the banner in the shell is what
starts it (providers are lazy, the shell is built once at launch) — deliberately
fire-and-forget, so a slow or dead update host can never delay or break the launch.
The banner appears only when there is something to install and is dismissible for the
session; dismissing it hides the banner but Settings still offers the update.

Two rules the class exists to enforce:

1. **Never block the app.** The check has a short timeout and swallows every failure —
   offline, DNS down, VPS hiccup, malformed JSON all return "no update". The update host
   is allowed to be down (VPS142 does flake); that is not an application error.
2. **Never execute an unverified binary.** The download is checked against the
   manifest's sha256 and **deleted** on mismatch. HTTPS protects transport; the hash
   also catches truncation and is a second gate before running code on Arthur's machine.
   A manifest with no `sha256` is treated as "no update" rather than half-trusted.

Installing stops the bot first (`onBeforeExit`) then launches the installer and exits:
the embedded `python.exe` holds handles inside `{app}\python`, and without releasing
them the upgrade half-applies.

Version comparison is **numeric**, not lexical — `"0.10.0" < "0.9.0"` as strings would
silently stop offering updates after the 9th minor.

### Version single-sourcing

`gui/pubspec.yaml` is the source of truth. `build_distribution.ps1` reads it for the
installer **and fails the build** if `AppConstants.appVersion` disagrees. The app
compares its own reported version against the manifest, so a drifted constant would mean
comparing against a lie — re-offering an update it already installed, or never offering
one.

## Tests

- `gui/test/providers/update_provider_test.dart` — 5, offline: the startup check
  surfaces a newer version on its own, stays **silent** when up to date, **a dead
  update host cannot break startup** (socket error / 500 / garbage all leave no error
  state), dismiss hides the banner without forgetting the update, and a manual check
  reports its outcome unlike the silent one.
- `gui/test/widgets/update_banner_test.dart` — 3: the banner actually **renders** the
  version and notes after the startup check, occupies no space when up to date, and
  "Plus tard" hides it for the session.
- `gui/test/services/update_service_test.dart` — 12, offline: numeric version compare,
  hashless manifest refused, every outage shape returns null, a slow server does not
  hang, a matching hash is accepted, **a tampered binary is rejected and deleted**, the
  bot is stopped **before** the installer launches (the ordering the upgrade depends
  on), a stuck bot does not block the update, and a failed launch does **not** quit the
  app (quitting without starting an installer would look like a crash).
- `gui/test/services/update_service_live_test.dart` — 4, **against the real host**
  (`AURELM_LIVE_DIST=1`): the deployed manifest parses, the current version is not
  offered an update, a real file downloads and verifies, and a **hostile** wrong hash is
  rejected with nothing left on disk.

## Verified end to end (2026-07-23)

The upgrade was actually run, not reasoned about: installed **0.1.0**, planted state,
installed **0.1.1** over it silently, and checked.

| claim | observed |
|---|---|
| in-place upgrade, not a second install | registered version 0.1.0 -> 0.1.1, **one** entry |
| activation survives | Credential Manager entry intact after the upgrade |
| DB outside `{app}` preserved | intact |
| a user file *inside* `{app}pp` | also preserved (only *uninstall* wipes it) |
| migrations catch up | a DB with **no** `agent_memory*` tables, run through the **installed** bundle's `python -m bot --migrate-only`, came back with `agent_memory` + `agent_memory_links` and its rows untouched |
| nginx `.exe` rules | real installer served 200, `application/octet-stream`, `immutable` |

`publish_release.ps1` then published 0.1.1 for real, and the four live client tests pass
against it.

## Traps this cost us

- **PowerShell 5.1 strips double quotes from native-command arguments.** The first
  publish shipped `{version:0.1.1,...}` -- unparseable JSON -- because the manifest was
  piped through `ssh "printf ... '$json'"`. It *looked* fine in the script output and
  was only visible by fetching it back. The manifest now travels as a **file** (scp +
  `mv`), and the script **fetches it back and parses it** before declaring success.
- **Keep .ps1 files ASCII-only.** Windows PowerShell 5.1 reads them as ANSI when there
  is no BOM, so a UTF-8 em-dash inside a double-quoted string terminates the string
  early and the file no longer parses — this actually happened here and was caught only
  by an explicit parse check.
- No rollback. If a release is bad, publish a corrected higher version.
- No signing of the installer (Windows SmartScreen will warn on first run).
