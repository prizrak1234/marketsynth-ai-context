# CPH.5 — start production-like local pilot stack (OPTION B)
# Does NOT run alembic migrate. Does NOT push.
# Usage:
#   .\scripts\cph5_start_pilot.ps1
# Optional: -BuildFrontend

param(
  [switch]$BuildFrontend,
  [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== CPH.5 validate config ==="
uv run python -m scripts.cph5_validate_config

Write-Host "=== CPH.5 revision guard ==="
uv run python scripts/cph1_db_tools.py check-revision

Write-Host "=== CPH.5 wait backend readiness (start uvicorn separately if needed) ==="
# This script assumes operator starts:
#   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
#   cd web; npm run build; npm run start
# Or use companion start for visual check.

if ($BuildFrontend) {
  Write-Host "=== Frontend production build ==="
  Push-Location "$Root\web"
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "frontend_build_failed" }
  Pop-Location
}

$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/ready" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch {
    Start-Sleep -Seconds 2
  }
}
if (-not $ready) {
  Write-Host "backend_not_ready — start uvicorn with DATABASE_URL=botfazer_cph1 then re-run"
  exit 2
}

Write-Host "liveness + readiness OK"

if (-not $SkipSmoke) {
  Write-Host "=== Post-deploy smoke ==="
  uv run python -m scripts.cph5_post_deploy_smoke --base-url http://127.0.0.1:8000
}
