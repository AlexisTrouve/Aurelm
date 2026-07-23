<#
.SYNOPSIS
    Build an Aurelm installer and publish it to the distribution server.

.DESCRIPTION
    Chains: build_distribution.ps1 -Installer  ->  sha256  ->  upload to VPS142  ->
    publish latest.json. The desktop app polls that manifest and offers the update.

    ORDER MATTERS: the binary is uploaded FIRST and the manifest LAST, written
    atomically (temp file + mv). A manifest that names a binary which is not fully
    uploaded yet would make every client download a truncated file and fail its hash
    check — visible to the user as a broken update for as long as the upload runs.

    The host is reached over Tailscale: the public IP is not reachable from every
    network, the Tailscale address always is.

.PARAMETER Notes
    One-line changelog shown to the user in the update banner.

.PARAMETER DryRun
    Build and hash, print what would be published, but do not touch the server.

.EXAMPLE
    pwsh scripts/publish_release.ps1 -Notes "Mémoire de l'agent + liens"
#>
[CmdletBinding()]
param(
    [string]$Notes = "",
    [switch]$DryRun,
    [string]$SshTarget = "debian@100.85.89.83",
    [string]$RemoteDir = "/var/www/aurelm-dist/aurelm"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

# --- 1. Build (this also enforces pubspec == AppConstants version) ------------
Write-Host "[1/5] Building the installer..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "build_distribution.ps1") -Installer
if ($LASTEXITCODE -ne 0) { throw "build_distribution.ps1 failed" }

# --- 2. Locate the artefact and read the version -----------------------------
$pubspec = Get-Content (Join-Path $repoRoot "gui/pubspec.yaml") -Raw
if ($pubspec -notmatch '(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+)') {
    throw "could not read a x.y.z version from gui/pubspec.yaml"
}
$version = $Matches[1]
$installer = Join-Path $repoRoot "dist/Aurelm-Setup-$version.exe"
if (-not (Test-Path $installer)) { throw "installer not found: $installer" }

$sizeMb = [math]::Round((Get-Item $installer).Length / 1MB, 1)
Write-Host "[2/5] Artefact: Aurelm-Setup-$version.exe ($sizeMb MB)" -ForegroundColor Yellow

# --- 3. Hash — this is what the client verifies before executing the binary ---
Write-Host "[3/5] Computing sha256..." -ForegroundColor Yellow
$sha = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLower()
Write-Host "      $sha"

$published = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$manifest = [ordered]@{
    version   = $version
    url       = "https://dist.etheryale.com/aurelm/Aurelm-Setup-$version.exe"
    sha256    = $sha
    notes     = $Notes
    published = $published
} | ConvertTo-Json -Compress

if ($DryRun) {
    Write-Host "`n[dry-run] would publish:" -ForegroundColor Cyan
    Write-Host $manifest
    return
}

# --- 4. Upload the binary FIRST ----------------------------------------------
Write-Host "[4/5] Uploading to $SshTarget..." -ForegroundColor Yellow
& scp -o ConnectTimeout=20 $installer "${SshTarget}:$RemoteDir/"
if ($LASTEXITCODE -ne 0) { throw "scp failed — is Tailscale up?" }

# Verify the remote copy matches before announcing it. A silent truncation here
# would ship a binary every client rejects.
$remoteSha = (& ssh -o ConnectTimeout=20 $SshTarget "sha256sum '$RemoteDir/Aurelm-Setup-$version.exe' | cut -d' ' -f1").Trim()
if ($remoteSha -ne $sha) {
    throw "remote hash mismatch after upload (local $sha, remote $remoteSha) — NOT publishing"
}
Write-Host "      remote hash verified"

# --- 5. Publish the manifest LAST, atomically --------------------------------
Write-Host "[5/5] Publishing manifest..." -ForegroundColor Yellow
$escaped = $manifest.Replace("'", "'\''")
& ssh -o ConnectTimeout=20 $SshTarget "printf '%s' '$escaped' > $RemoteDir/.latest.json.tmp && mv -f $RemoteDir/.latest.json.tmp $RemoteDir/latest.json && chmod 644 $RemoteDir/latest.json"
if ($LASTEXITCODE -ne 0) { throw "publishing the manifest failed" }

Write-Host "`nPublished $version -> https://dist.etheryale.com/aurelm/latest.json" -ForegroundColor Green
Write-Host $manifest
