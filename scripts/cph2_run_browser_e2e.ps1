# CPH.2 orchestration — pilot PostgreSQL + backend + frontend + Playwright
# Refuses legacy DB `botfazer`. No push. No secrets printed.

param(
  [switch]$Headed,
  [string]$DatabaseUrl = $env:DATABASE_URL,
  [string]$BackendUrl = "http://localhost:8000",
  [string]$FrontendUrl = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $DatabaseUrl) {
  $DatabaseUrl = "postgresql+asyncpg://botfazer:botfazer@localhost:5432/botfazer_cph1"
}
$env:DATABASE_URL = $DatabaseUrl
$env:CPH2_BACKEND_URL = $BackendUrl
$env:CPH2_FRONTEND_URL = $FrontendUrl
$env:NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE = "backend"
$env:CPH2_INTEGRATION_MODE = "backend"

if ($DatabaseUrl -match "/botfazer$" -and $DatabaseUrl -notmatch "botfazer_cph") {
  Write-Error "Refusing legacy database botfazer"
  exit 3
}

Write-Host "=== CPH.2 diagnose ==="
uv run python scripts/cph2_e2e_diag.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Seed pilot API user ==="
$seedOut = uv run python scripts/cph2_seed_pilot_user.py --write-env --refresh-api-key 2>&1 | Out-String
Write-Host ($seedOut -replace "NEXT_PUBLIC_BOTFAZER_API_KEY=\S+", "NEXT_PUBLIC_BOTFAZER_API_KEY=***")
$keyLine = ($seedOut -split "`n" | Where-Object { $_ -match "^NEXT_PUBLIC_BOTFAZER_API_KEY=" } | Select-Object -First 1)
if (-not $keyLine) { Write-Error "No API key from seed"; exit 4 }
$env:CPH2_API_KEY = ($keyLine -replace "^NEXT_PUBLIC_BOTFAZER_API_KEY=", "").Trim()
$env:NEXT_PUBLIC_BOTFAZER_API_KEY = $env:CPH2_API_KEY

# Copy e2e env into web/.env.local for Next (backend mode)
$envLocal = Join-Path $Root "web\.env.local"
@(
  "NEXT_PUBLIC_BOTFAZER_API_BASE_URL=$BackendUrl"
  "NEXT_PUBLIC_BOTFAZER_API_KEY=$($env:CPH2_API_KEY)"
  "NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE=backend"
) | Set-Content -Path $envLocal -Encoding utf8

Write-Host "=== Ensure backend up ==="
try {
  Invoke-WebRequest -Uri "$BackendUrl/docs" -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
  Write-Host "Starting uvicorn…"
  Start-Process -FilePath "uv" -ArgumentList "run","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $Root -WindowStyle Minimized
  Start-Sleep -Seconds 5
}

Write-Host "=== Ensure frontend up ==="
try {
  Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
  Write-Host "Starting next dev…"
  Start-Process -FilePath "npm" -ArgumentList "run","dev","--","-p","3000" -WorkingDirectory (Join-Path $Root "web") -WindowStyle Minimized
  Start-Sleep -Seconds 8
}

uv run python scripts/cph2_e2e_diag.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:CPH2_RUN_ID = "r" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Set-Location (Join-Path $Root "web")
if ($Headed) {
  npx playwright test e2e/commercial-happy-path.spec.ts e2e/routing-guards.spec.ts e2e/hybrid-smoke.spec.ts --reporter=list --headed
} else {
  npx playwright test e2e/commercial-happy-path.spec.ts e2e/routing-guards.spec.ts e2e/hybrid-smoke.spec.ts --reporter=list
}
exit $LASTEXITCODE
