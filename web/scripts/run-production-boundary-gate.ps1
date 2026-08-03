# PRODUCT-01.3B-FINAL-GATE — production-boundary E2E orchestration.
# Root causes addressed:
#   1. Port 3000 conflict with `next dev` (Playwright webServer reuseExistingServer=false).
#   2. Alternate ports (3010) fail CORS — backend allowlist is :3000 only.
#
# Prerequisites: backend on :8000 with BIV_E2E_DETERMINISTIC_ENABLED=false (.env defaults).

$ErrorActionPreference = "Stop"
$WebRoot = Split-Path -Parent $PSScriptRoot
# Must match backend browser_allowed_origins (default :3000 only).
if ($env:CPH2_PRODUCTION_PORT -and $env:CPH2_PRODUCTION_PORT -ne "3000") {
  Write-Warning "CPH2_PRODUCTION_PORT=$($env:CPH2_PRODUCTION_PORT) may fail CORS; resetting to 3000"
}
$Port = "3000"
$BaseUrl = "http://localhost:$Port"
$env:CPH2_PRODUCTION_PORT = $Port
$env:CPH2_PRODUCTION_FRONTEND_URL = $BaseUrl

Write-Host "==> Stopping next dev on port $Port if present..."
$listeners = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
foreach ($line in $listeners) {
  $listenerPid = ($line -split "\s+")[-1]
  if ($listenerPid -match "^\d+$") {
    Write-Host "    Stopping PID $listenerPid"
    Stop-Process -Id ([int]$listenerPid) -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep -Seconds 2

Write-Host "==> Clean production build..."
Push-Location $WebRoot
try {
  if (Test-Path .next) { Remove-Item -Recurse -Force .next }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }

  Write-Host "==> Starting production server on $BaseUrl ..."
  New-Item -ItemType Directory -Force -Path "$WebRoot/test-results" | Out-Null
  $prod = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "npx next start -p $Port") `
    -WorkingDirectory $WebRoot -PassThru `
    -RedirectStandardOutput "$WebRoot/test-results/prod-server.out.log" `
    -RedirectStandardError "$WebRoot/test-results/prod-server.err.log"

  Write-Host "==> Waiting for HTTP readiness..."
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 5
      if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) {
    Stop-Process -Id $prod.Id -Force -ErrorAction SilentlyContinue
    throw "Production server not ready at $BaseUrl within 120s"
  }
  Write-Host "    Ready: $BaseUrl -> 200"

  Write-Host "==> Running production-boundary Playwright suite..."
  $env:CPH2_PRODUCTION_PORT = $Port
  $env:CPH2_PRODUCTION_FRONTEND_URL = $BaseUrl
  $env:CPH2_PRODUCTION_REUSE_SERVER = "true"
  npm run test:e2e:production-boundary
  $exit = $LASTEXITCODE

  Write-Host "==> Stopping production server (PID $($prod.Id))..."
  Stop-Process -Id $prod.Id -Force -ErrorAction SilentlyContinue
  exit $exit
} finally {
  Pop-Location
}
