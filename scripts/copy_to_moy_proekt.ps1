# Copy botfazer from Cursor workspace cache to C:\Users\Сарбаст\Мой проект\botfazer
# Run this script logged in as user Сарбаст (owner of the profile folder).

$ErrorActionPreference = "Stop"
$Source = Join-Path $PSScriptRoot ".."
$Source = (Resolve-Path $Source).Path
$Dest = "C:\Users\Сарбаст\Мой проект\botfazer"

Write-Host "Source: $Source"
Write-Host "Dest:   $Dest"

if (-not (Test-Path (Split-Path $Dest -Parent))) {
    Write-Error "Parent folder not found. Create: C:\Users\Сарбаст\Мой проект"
}

New-Item -ItemType Directory -Path $Dest -Force | Out-Null
robocopy $Source $Dest /E /XD .venv .pytest_cache .mypy_cache .ruff_cache __pycache__ /NFL /NDL /NJH /NJS
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }
Write-Host "Done. Open: $Dest"
