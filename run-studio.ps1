<#
.SYNOPSIS
  Run Terrain Studio locally.

.DESCRIPTION
  A service worker only registers on a SECURE ORIGIN - https, or http on localhost. It never runs
  from file://. So installability, offline mode and the update prompt can only be exercised through
  a served origin, which is what this script provides.

  Modes:
    dev      (default) Vite dev server with HMR. Fast edit loop. The service worker is deliberately
             NOT active here, so what you see is the app, not the cache.
    pwa      Production build + preview server. THIS is the mode to use for anything PWA-related:
             install prompt, offline, update flow, Lighthouse.
    build    Build only, no server.

.EXAMPLE
  .\run-studio.ps1
.EXAMPLE
  .\run-studio.ps1 -Mode pwa
.EXAMPLE
  .\run-studio.ps1 -Mode pwa -Port 8080 -NoOpen
#>
[CmdletBinding()]
param(
  [ValidateSet('dev', 'pwa', 'build')]
  [string]$Mode = 'dev',
  [int]$Port = 0,
  [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$app = Join-Path $repo 'apps/terrain-studio'

if (-not (Test-Path $app)) { throw "Cannot find $app. Run this from the repository root." }

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw 'Node.js not found on PATH. Install Node 20 or newer.' }
$major = ([int](& node -p "process.versions.node.split('.')[0]"))
if ($major -lt 20) { throw "Node $major found; this project needs Node 20 or newer." }

if (-not (Test-Path (Join-Path $repo 'node_modules'))) {
  Write-Host 'Installing dependencies (first run)...' -ForegroundColor Yellow
  Push-Location $repo
  try { & npm install --no-audit --no-fund } finally { Pop-Location }
}

Push-Location $app
try {
  switch ($Mode) {
    'build' {
      & npx vite build
      Write-Host "`nBuilt to $app\dist" -ForegroundColor Green
    }
    'dev' {
      if ($Port -eq 0) { $Port = 5173 }
      $url = "http://127.0.0.1:$Port/index.html"
      Write-Host "`nTerrain Studio (dev)  $url" -ForegroundColor Green
      Write-Host 'Service worker is NOT active in dev - use -Mode pwa to test install/offline.' -ForegroundColor DarkGray
      if (-not $NoOpen) { Start-Process $url }
      & npx vite --port $Port --strictPort
    }
    'pwa' {
      if ($Port -eq 0) { $Port = 4173 }
      Write-Host 'Building production bundle...' -ForegroundColor Yellow
      & npx vite build
      $url = "http://127.0.0.1:$Port/index.html"
      Write-Host "`nTerrain Studio (PWA)  $url" -ForegroundColor Green
      Write-Host 'localhost counts as a secure origin, so the service worker registers here.' -ForegroundColor DarkGray
      Write-Host 'Install: address-bar install icon. Offline: DevTools > Network > Offline, then reload.' -ForegroundColor DarkGray
      if (-not $NoOpen) { Start-Process $url }
      & npx vite preview --port $Port --strictPort
    }
  }
} finally { Pop-Location }
