<#
.SYNOPSIS
    Assembles the self-contained Windows distribution of Aurelm.

.DESCRIPTION
    Produces a folder that runs on a machine with NO Python and no repo checkout:

        <out>/
          aurelm_gui.exe, *.dll, data/     <- Flutter release build
          python/                          <- embedded CPython + runtime deps
            python.exe, python312._pth, Lib/site-packages/
          app/
            bot/  pipeline/                <- the Python the app spawns

    WHY the embeddable CPython rather than PyInstaller: the app spawns the bot as a
    real subprocess and the pipeline imports it as a package. An interpreter we own
    keeps that model intact — no freezing, no import hooks, no hidden-import guessing.

    THE ONE NON-OBVIOUS PART — python312._pth:
    When a `._pth` file sits next to python.exe, CPython takes FULL control of
    sys.path: it ignores PYTHONPATH *and* does not add the working directory, even
    for `-m`. Measured, not assumed: without the `..\app` line below, launching the
    bundle fails with "No module named bot" no matter what cwd it is given. The `.`
    entry means "the directory holding python.exe", not the cwd — hence the explicit
    relative hop to the app folder.

.PARAMETER OutDir
    Where to assemble. Wiped and recreated.

.PARAMETER PythonVersion
    CPython version of the embeddable package to download.

.PARAMETER SkipFlutterBuild
    Reuse an existing Flutter release build instead of rebuilding (CI builds it in
    its own step so it can cache and report separately).

.PARAMETER Zip
    Also produce <OutDir>.zip.

.PARAMETER Installer
    Also compile scripts/installer.iss into a single Aurelm-Setup-<version>.exe
    (requires Inno Setup; see Resolve-Iscc).

.PARAMETER AppVersion
    Version stamped on the installer. Defaults to the version in gui/pubspec.yaml.
#>
[CmdletBinding()]
param(
    [string]$OutDir = "dist/aurelm-windows",
    [string]$PythonVersion = "3.12.10",
    [switch]$SkipFlutterBuild,
    [switch]$Zip,
    [switch]$Installer,
    [string]$AppVersion
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Runs a native tool and judges it by its EXIT CODE, not by whether it wrote to
# stderr. WHY: pip reports unrelated dependency conflicts from the build machine's
# global environment on stderr, and flutter streams progress there too. Under
# $ErrorActionPreference = 'Stop' PowerShell turns any native stderr line into a
# terminating NativeCommandError — which aborted this script on a pip run that had
# actually succeeded.
function Invoke-Native {
    param(
        [Parameter(Mandatory)][scriptblock]$Command,
        [Parameter(Mandatory)][string]$What
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Command } finally { $ErrorActionPreference = $previous }
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)" }
}

# Finds the Inno Setup compiler. WHY a search rather than a fixed path: winget
# installs it per-user under LocalAppData, the classic installer puts it in
# Program Files, and GitHub runners ship it somewhere else again — hardcoding any
# one of those makes the build work on exactly one machine.
function Resolve-Iscc {
    $onPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw "Inno Setup (ISCC.exe) not found. Install it (winget install JRSoftware.InnoSetup) or drop -Installer."
}

Write-Host "== Aurelm distribution build ==" -ForegroundColor Cyan
Write-Host "repo:   $repoRoot"
Write-Host "output: $OutDir"

# --- 1. Flutter release build -------------------------------------------------
$flutterRelease = Join-Path $repoRoot "gui/build/windows/x64/runner/Release"
if (-not $SkipFlutterBuild) {
    Write-Host "`n[1/6] Building Flutter release..." -ForegroundColor Yellow
    Push-Location (Join-Path $repoRoot "gui")
    Invoke-Native -What "flutter build windows" -Command { flutter build windows --release }
    Pop-Location
} else {
    Write-Host "`n[1/6] Skipping Flutter build (--SkipFlutterBuild)" -ForegroundColor Yellow
}
if (-not (Test-Path $flutterRelease)) {
    throw "Flutter release output not found at $flutterRelease"
}

# --- 2. Clean output ----------------------------------------------------------
Write-Host "[2/6] Preparing $OutDir..." -ForegroundColor Yellow
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path

# --- 3. Embedded CPython ------------------------------------------------------
Write-Host "[3/6] Fetching embedded CPython $PythonVersion..." -ForegroundColor Yellow
$pyDir = Join-Path $OutDir "python"
New-Item -ItemType Directory -Force -Path $pyDir | Out-Null

# Cache the download between builds — it never changes for a given version.
$cacheDir = Join-Path $env:TEMP "aurelm-build-cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$embedZip = Join-Path $cacheDir "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $embedZip)) {
    $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
    Write-Host "      downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $embedZip
} else {
    Write-Host "      using cached $embedZip"
}
Expand-Archive -Path $embedZip -DestinationPath $pyDir -Force

# --- 4. Runtime dependencies --------------------------------------------------
# Installed with the BUILD machine's pip into the embedded tree. The embeddable
# ships without pip on purpose, and --target keeps the install self-contained.
Write-Host "[4/6] Installing runtime dependencies..." -ForegroundColor Yellow
$sitePackages = Join-Path $pyDir "Lib/site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
$reqFile = Join-Path $repoRoot "requirements-dist.txt"
Invoke-Native -What "pip install -r requirements-dist.txt" -Command {
    python -m pip install --quiet --disable-pip-version-check --target $sitePackages -r $reqFile
}

# Rewrite ._pth so site-packages AND the app folder are on sys.path (see header).
$pthFile = Get-ChildItem -Path $pyDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) { throw "no python*._pth in the embeddable package" }
@"
python$($PythonVersion.Split('.')[0])$($PythonVersion.Split('.')[1]).zip
.
Lib\site-packages
..\app

# `import site` must run for the entries above to be honoured.
import site
"@ | Set-Content -Path $pthFile.FullName -Encoding ascii

# --- 5. Application code ------------------------------------------------------
Write-Host "[5/6] Copying app code + Flutter build..." -ForegroundColor Yellow
$appDir = Join-Path $OutDir "app"
New-Item -ItemType Directory -Force -Path $appDir | Out-Null

# bot/ ships whole. database/ ships WHOLE on purpose: migration 001 does
# `.read ../schema.sql`, which resolves to app/database/schema.sql — copying only
# migrations/ would silently break first-run schema creation (zero tables, and
# /health would still come up, hiding it).
foreach ($pkg in @("bot", "database")) {
    Copy-Item -Recurse -Force (Join-Path $repoRoot $pkg) (Join-Path $appDir $pkg)
}

# pipeline/ is a NAMESPACE package whose only runtime-imported part is
# pipeline/pipeline/ (bot imports `pipeline.pipeline.*`). Ship ONLY that. The rest
# of the tree — archive_db/ (the dev's game DBs), roman_exports/ (a private corpus),
# data/, maps/, benchmark scripts, and a dev pipeline/aurelm_config.json holding real
# Discord IDs — is git-tracked and must NEVER end up in a user's installer. Verified:
# pipeline/pipeline/ loads no file from those dirs at runtime (only OPENROUTER_API_KEY
# from the env we inject).
New-Item -ItemType Directory -Force -Path (Join-Path $appDir "pipeline") | Out-Null
Copy-Item -Recurse -Force (Join-Path $repoRoot "pipeline/pipeline") `
    (Join-Path $appDir "pipeline/pipeline")
# Tests and caches are dead weight in a shipped app.
Get-ChildItem -Path $appDir -Recurse -Directory -Include "__pycache__", "tests", ".pytest_cache" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Copy-Item -Recurse -Force (Join-Path $flutterRelease "*") $OutDir

# --- 6. Smoke test ------------------------------------------------------------
# A bundle that assembles but cannot import is worthless, so prove it here rather
# than discovering it on the user's machine.
Write-Host "[6/6] Smoke-testing the bundle..." -ForegroundColor Yellow
$bundledPython = Join-Path $pyDir "python.exe"
Invoke-Native -What "bundled interpreter importing runtime deps" -Command {
    & $bundledPython -c "import openai, discord, aiohttp, httpx, ollama, sqlite3; print('deps OK')"
}
Invoke-Native -What "bundled interpreter importing app packages (check ._pth)" -Command {
    & $bundledPython -c "import bot, bot.config, bot.agent, pipeline.pipeline.runner; print('app packages OK')"
}

# Migrations against a FRESH DB. WHY this and not just /health: a missing
# database/migrations dir let the bot serve /health while creating zero tables —
# the app would install and die on first real use. This asserts the bundled
# migrations actually build the schema, which is the failure /health hides.
#
# The probe is written to a FILE, not passed via `python -c`: a multi-line script
# handed to a native exe as an argument is quoted differently across PowerShell
# environments — it ran locally and broke on the CI runner with a SyntaxError.
$migrateProbe = Join-Path $env:TEMP "aurelm-migrate-probe.db"
$probeScript = Join-Path $env:TEMP "aurelm-migrate-probe.py"
if (Test-Path $migrateProbe) { Remove-Item $migrateProbe -Force }
@"
import sqlite3, sys
from bot.migrations import apply_migrations
db = sys.argv[1]
apply_migrations(db)
tables = [r[0] for r in sqlite3.connect(db).execute(
    "SELECT name FROM sqlite_master WHERE type='table'")]
core = [t for t in tables if t.startswith(('civ_', 'turn_', 'entity_'))]
assert 'civ_civilizations' in tables, f'no civ table; got {len(tables)} tables'
assert len(core) >= 3, f'schema looks empty: {tables}'
print(f'migrations OK: {len(tables)} tables, core present')
"@ | Set-Content -Path $probeScript -Encoding ascii
Invoke-Native -What "bundled migrations build the schema on a fresh DB" -Command {
    & $bundledPython $probeScript $migrateProbe
}
Remove-Item $migrateProbe, $probeScript -Force -ErrorAction SilentlyContinue

if (-not (Test-Path (Join-Path $OutDir "aurelm_gui.exe"))) { throw "aurelm_gui.exe missing from the bundle" }

$sizeMb = [math]::Round((Get-ChildItem $OutDir -Recurse -File |
    Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "`nBundle OK: $OutDir ($sizeMb MB)" -ForegroundColor Green

if ($Zip) {
    $zipPath = "$OutDir.zip"
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $zipPath
    Write-Host "Zipped: $zipPath" -ForegroundColor Green
}

# --- 7. Installer (optional) --------------------------------------------------
if ($Installer) {
    Write-Host "`n[7/7] Compiling the installer..." -ForegroundColor Yellow

    if (-not $AppVersion) {
        # Single source of truth for the version: the app's own pubspec. Inno wants
        # a plain x.y.z, so drop any "+build" suffix Flutter allows.
        $pubspec = Get-Content (Join-Path $repoRoot "gui/pubspec.yaml") -Raw
        if ($pubspec -match '(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)') {
            $AppVersion = $Matches[1]
        } else {
            throw "could not read a x.y.z version from gui/pubspec.yaml (pass -AppVersion)"
        }
    }

    $iscc = Resolve-Iscc
    $issPath = Join-Path $PSScriptRoot "installer.iss"
    $installerOut = Join-Path $repoRoot "dist"
    Write-Host "      compiler: $iscc"
    Write-Host "      version:  $AppVersion"

    Invoke-Native -What "ISCC installer.iss" -Command {
        & $iscc "/DAppVersion=$AppVersion" "/DBundleDir=$OutDir" "/DOutDir=$installerOut" $issPath
    }

    $setupExe = Join-Path $installerOut "Aurelm-Setup-$AppVersion.exe"
    if (-not (Test-Path $setupExe)) { throw "installer not produced at $setupExe" }
    $setupMb = [math]::Round((Get-Item $setupExe).Length / 1MB, 1)
    Write-Host "Installer OK: $setupExe ($setupMb MB)" -ForegroundColor Green
}
