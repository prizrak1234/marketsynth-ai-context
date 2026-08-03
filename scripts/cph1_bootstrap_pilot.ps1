# CPH.1 PowerShell bootstrap for disposable PostgreSQL.
# 1) Superuser creates DB (botfazer app user cannot CREATEDB):
#    CREATE DATABASE botfazer_cph1 OWNER botfazer;
# 2) Point DATABASE_URL at disposable DB and run this script.

param(
  [string]$DatabaseUrl = $env:DATABASE_URL
)

if (-not $DatabaseUrl) {
  Write-Error "DATABASE_URL is required"
  exit 2
}

if ($DatabaseUrl -match "/botfazer$" -and $DatabaseUrl -notmatch "botfazer_cph") {
  Write-Error "Refusing to bootstrap non-disposable database 'botfazer'. Create botfazer_cph1 first."
  exit 3
}

$env:DATABASE_URL = $DatabaseUrl
Write-Host "DATABASE_URL set (password redacted in logs by alembic tooling)"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python scripts/cph1_db_tools.py check-revision
uv run python scripts/cph1_db_tools.py schema-parity
Write-Host "bootstrap_ok"
