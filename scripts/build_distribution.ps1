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
#>
[CmdletBinding()]
param(
    [string]$OutDir = "dist/aurelm-windows",
    [string]$PythonVersion = "3.12.10",
    [switch]$SkipFlutterBuild,
    [switch]$Zip
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
foreach ($pkg in @("bot", "pipeline")) {
    Copy-Item -Recurse -Force (Join-Path $repoRoot $pkg) (Join-Path $appDir $pkg)
}
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
