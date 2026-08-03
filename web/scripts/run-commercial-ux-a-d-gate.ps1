# PRODUCT-01.4-COMMERCIAL-UX-A-D-VERIFICATION-01 - production browser gate.
# Prerequisites: backend on :8000 with BIV_E2E_DETERMINISTIC_ENABLED=true and BIV_RUN_DISPATCHER_ENABLED=true.

$ErrorActionPreference = "Stop"
$WebRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $WebRoot
$Port = "3000"
$BaseUrl = "http://localhost:$Port"
$env:CPH2_PRODUCTION_PORT = $Port
$env:CPH2_PRODUCTION_FRONTEND_URL = $BaseUrl
$env:CPH2_FRONTEND_URL = $BaseUrl

Write-Host "==> backend E2E preconditions..."
if (-not $env:BIV_E2E_DETERMINISTIC_ENABLED) { $env:BIV_E2E_DETERMINISTIC_ENABLED = "true" }
if (-not $env:APP_ENV) { $env:APP_ENV = "development" }
Push-Location $RepoRoot
try {
  $det = uv run python -c "from app.core.config import get_settings; s=get_settings(); print('ok' if s.biv_e2e_deterministic_allowed else 'off')" 2>&1
  if ($det -ne "ok") {
    throw "BIV_E2E_DETERMINISTIC_ENABLED must be true on the running backend (restart uvicorn with APP_ENV=development/test). Got: $det"
  }
  try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($health.StatusCode -ne 200) { throw "backend /health not 200" }
  } catch {
    throw "Backend not reachable on :8000 - start uvicorn before running this gate."
  }
} finally {
  Pop-Location
}

Write-Host "==> Stopping listeners on port $Port..."
$listeners = netstat -ano | Select-String "LISTENING" | Select-String ":$Port "
foreach ($line in $listeners) {
  $listenerPid = ($line -split "\s+")[-1]
  if ($listenerPid -match "^\d+$") {
    Write-Host "    Stopping PID $listenerPid"
    Stop-Process -Id ([int]$listenerPid) -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep -Seconds 2

Push-Location $WebRoot
try {
  Write-Host "==> typecheck..."
  npm run typecheck
  if ($LASTEXITCODE -ne 0) { throw "typecheck failed" }

  Write-Host "==> unit tests..."
  npm run test:unit
  if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }

  Write-Host "==> production build..."
  if (Test-Path .next) { Remove-Item -Recurse -Force .next }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "build failed" }

  Write-Host "==> starting production server..."
  New-Item -ItemType Directory -Force -Path "$WebRoot/test-results/commercial-ux-a-d-verification" | Out-Null
  $prod = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "npx next start -p $Port") `
    -WorkingDirectory $WebRoot -PassThru `
    -RedirectStandardOutput "$WebRoot/test-results/prod-server-ux-ad.out.log" `
    -RedirectStandardError "$WebRoot/test-results/prod-server-ux-ad.err.log"

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
    throw "Production server not ready at $BaseUrl"
  }

  $env:CPH2_PRODUCTION_REUSE_SERVER = "true"
  Write-Host "==> commercial UX A-D Playwright verification..."
  npx playwright test -c playwright.commercial-ux-verification.config.ts
  $exit = $LASTEXITCODE

  Write-Host "==> recovery E2E regression (production frontend on $BaseUrl)..."
  $env:CPH2_FRONTEND_URL = $BaseUrl
  npm run test:e2e:biv-result-delivery-recovery
  if ($LASTEXITCODE -ne 0) { $exit = $LASTEXITCODE }

  Stop-Process -Id $prod.Id -Force -ErrorAction SilentlyContinue
  exit $exit
} finally {
  Pop-Location
}
