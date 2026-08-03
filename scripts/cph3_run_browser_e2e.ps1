# CPH.3 orchestration — cookie session E2E on pilot PostgreSQL
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
# CPH.3 — do not inject permanent API keys into the browser
Remove-Item Env:NEXT_PUBLIC_BOTFAZER_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:CPH2_API_KEY -ErrorAction SilentlyContinue

if ($DatabaseUrl -match "/botfazer$" -and $DatabaseUrl -notmatch "botfazer_cph") {
  Write-Error "Refusing legacy database botfazer"
  exit 3
}

Write-Host "=== Migrate pilot DB ==="
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Provision pilot users A/B ==="
$passA = if ($env:CPH3_E2E_PASSWORD) { $env:CPH3_E2E_PASSWORD } else { "cph3-pilot-a-pass" }
$passB = if ($env:CPH3_E2E_PASSWORD_B) { $env:CPH3_E2E_PASSWORD_B } else { "cph3-pilot-b-pass" }
$env:CPH3_E2E_EMAIL = if ($env:CPH3_E2E_EMAIL) { $env:CPH3_E2E_EMAIL } else { "cph3.pilot.a@marketsynth.local" }
$env:CPH3_E2E_EMAIL_B = if ($env:CPH3_E2E_EMAIL_B) { $env:CPH3_E2E_EMAIL_B } else { "cph3.pilot.b@marketsynth.local" }
$env:CPH3_E2E_PASSWORD = $passA
$env:CPH3_E2E_PASSWORD_B = $passB
$env:CPH3_PILOT_PASSWORD = $passA
uv run python scripts/cph3_provision_pilot_user.py --email $env:CPH3_E2E_EMAIL --update --require-db botfazer_cph1 --telegram-id 9100501 | Out-Null
$env:CPH3_PILOT_PASSWORD = $passB
uv run python scripts/cph3_provision_pilot_user.py --email $env:CPH3_E2E_EMAIL_B --update --require-db botfazer_cph1 --telegram-id 9100502 | Out-Null
Write-Host "Provisioned (passwords not printed)"

# Frontend env: backend mode, NO API key
$envLocal = Join-Path $Root "web\.env.local"
@(
  "NEXT_PUBLIC_BOTFAZER_API_BASE_URL=$BackendUrl"
  "NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE=backend"
) | Set-Content -Path $envLocal -Encoding utf8

Write-Host "=== Ensure backend up ==="
try {
  Invoke-WebRequest -Uri "$BackendUrl/docs" -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
  Write-Host "Starting uvicorn…"
  Start-Process -FilePath "uv" -ArgumentList "run","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $Root -WindowStyle Minimized
  Start-Sleep -Seconds 6
}

Write-Host "=== Ensure frontend up ==="
try {
  Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 3 | Out-Null
} catch {
  Write-Host "Starting next dev…"
  Start-Process -FilePath "npm" -ArgumentList "run","dev","--","-p","3000" -WorkingDirectory (Join-Path $Root "web") -WindowStyle Minimized
  Start-Sleep -Seconds 10
}

$env:CPH2_RUN_ID = "r" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$env:CPH3_RUN_ID = $env:CPH2_RUN_ID
Set-Location (Join-Path $Root "web")
if ($Headed) {
  npx playwright test e2e/auth.spec.ts e2e/commercial-happy-path.spec.ts e2e/routing-guards.spec.ts e2e/hybrid-smoke.spec.ts --reporter=list --headed
} else {
  npx playwright test e2e/auth.spec.ts e2e/commercial-happy-path.spec.ts e2e/routing-guards.spec.ts e2e/hybrid-smoke.spec.ts --reporter=list
}
exit $LASTEXITCODE
