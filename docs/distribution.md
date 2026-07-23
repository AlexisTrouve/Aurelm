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

`gui/lib/services/update_service.dart` + the "Mises à jour" card in Settings.

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

- `gui/test/services/update_service_test.dart` — 9, offline: numeric version compare,
  hashless manifest refused, every outage shape returns null, a slow server does not
  hang, a matching hash is accepted, **a tampered binary is rejected and deleted**.
- `gui/test/services/update_service_live_test.dart` — 4, **against the real host**
  (`AURELM_LIVE_DIST=1`): the deployed manifest parses, the current version is not
  offered an update, a real file downloads and verifies, and a **hostile** wrong hash is
  rejected with nothing left on disk.

## Not done yet

- No automatic check on startup — the user presses "Vérifier". Deliberate for now:
  a background check that surfaces a banner is easy to add once the manual path has
  been used in anger.
- No rollback. If a release is bad, publish a corrected higher version.
- No signing of the installer (Windows SmartScreen will warn on first run).
