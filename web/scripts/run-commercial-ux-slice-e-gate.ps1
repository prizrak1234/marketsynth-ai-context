# PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01E-FINALIZATION
# Canonical composite gate — self-orchestrated backend + production frontend + E2E matrix.
# One command: npm run test:e2e:commercial-ux-slice-e-gate

$ErrorActionPreference = "Stop"
$WebRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $WebRoot
$BackendPort = "8000"
$FrontendPort = "3000"
$BackendUrl = "http://127.0.0.1:$BackendPort"
$BaseUrl = "http://localhost:$FrontendPort"
$GateRunId = "slice-e-gate-$(Get-Date -Format 'yyyyMMddHHmmss')"
$ArtifactRoot = Join-Path $WebRoot "e2e-artifacts/commercial-ux-slice-e-verification"
$GateLogDir = Join-Path $WebRoot "e2e-artifacts/commercial-ux-slice-e-gate/$GateRunId"
New-Item -ItemType Directory -Force -Path $ArtifactRoot, $GateLogDir | Out-Null

$BackendProc = $null
$FrontendProc = $null
$ExitCode = 0

function Write-GateLog([string]$Message) {
  $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
  Write-Host $line
  Add-Content -Path (Join-Path $GateLogDir "gate.log") -Value $line
}

function Get-PortListenerPids([string]$Port) {
  $pids = @()
  netstat -ano | Select-String "LISTENING" | Select-String ":$Port " | ForEach-Object {
    $procId = ($_.Line -split "\s+")[-1]
    if ($procId -match "^\d+$") { $pids += [int]$procId }
  }
  return ($pids | Sort-Object -Unique)
}

function Stop-GatePort([string]$Port, [string]$Label) {
  $pids = Get-PortListenerPids $Port
  foreach ($procId in $pids) {
    Write-GateLog "Stopping $Label listener PID $procId on port $Port"
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
}

function Stop-NextDevProcesses([string]$WebRootPath) {
  $normalized = (Resolve-Path $WebRootPath).Path.ToLower()
  Get-CimInstance Win32_Process -Filter "name='node.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = $_.CommandLine
    if ($null -ne $cmd -and $cmd -match "next\s+dev" -and $cmd.ToLower().Contains($normalized)) {
      Write-GateLog "Stopping next dev PID $($_.ProcessId) bound to web root"
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
  }
}

function Wait-HttpOk([string]$Url, [int]$MaxSeconds, [string]$Label) {
  for ($i = 0; $i -lt $MaxSeconds; $i += 2) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
        Write-GateLog "$Label ready: $Url -> $($resp.StatusCode)"
        return $true
      }
    } catch { }
    Start-Sleep -Seconds 2
  }
  return $false
}

function Invoke-GateStep([string]$Name, [scriptblock]$Block) {
  Write-GateLog "==> $Name"
  & $Block
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed (exit $LASTEXITCODE)"
  }
}

function Remove-NextBuildDirectory([string]$NextPath) {
  $parent = Split-Path -Parent $NextPath
  Get-ChildItem -LiteralPath $parent -Directory -Filter ".next*" -ErrorAction SilentlyContinue | ForEach-Object {
    $target = $_.FullName
    for ($attempt = 1; $attempt -le 3; $attempt++) {
      try {
        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
        break
      } catch {
        Write-GateLog "Remove-Item $target attempt $attempt failed: $($_.Exception.Message)"
        Start-Sleep -Seconds 2
        cmd.exe /c "rmdir /s /q `"$target`"" 2>$null | Out-Null
      }
    }
    if (Test-Path $target) {
      $trash = "$target.gate-trash-$(Get-Date -Format 'yyyyMMddHHmmss')"
      try {
        Rename-Item -LiteralPath $target -NewName (Split-Path -Leaf $trash) -ErrorAction Stop
        Write-GateLog "Renamed locked $target to $(Split-Path -Leaf $trash)"
      } catch {
        throw "Unable to clean or rename ${target}: $($_.Exception.Message)"
      }
    }
  }
  if (-not (Test-Path $NextPath)) {
    Write-GateLog "Removed stale .next build directories under $parent"
  }
}

function Assert-ProductionFrontendChunks([string]$BaseUrl) {
  $probeUrl = "$BaseUrl/workspace/projects/gate-chunk-probe/verdict"
  $html = (Invoke-WebRequest -Uri $probeUrl -UseBasicParsing -TimeoutSec 30).Content
  if ($html -match 'src="/_next/static/chunks/main-app\.js"') {
    throw "Production frontend serves dev-mode chunks (main-app.js). Clean .next and rebuild before E2E."
  }
  if ($html -notmatch 'main-app-[a-f0-9]+\.js') {
    throw "Production frontend missing hashed main-app chunk on dynamic route probe."
  }
  Write-GateLog "Production chunk probe ok: $probeUrl"
}

function Assert-BackendReady([string]$Label) {
  if (-not (Wait-HttpOk "$BackendUrl/health" 15 "Backend /health ($Label)")) {
    throw "Backend unavailable before $Label"
  }
  if (-not (Wait-HttpOk "$BackendUrl/health/ready" 15 "Backend /health/ready ($Label)")) {
    throw "Backend not ready before $Label"
  }
}

try {
  # --- Environment defaults (gate-owned) ---
  $env:APP_ENV = "development"
  $env:BIV_E2E_DETERMINISTIC_ENABLED = "true"
  $env:BIV_RUN_DISPATCHER_ENABLED = "true"
  $env:CPH2_PRODUCTION_PORT = $FrontendPort
  $env:CPH2_PRODUCTION_FRONTEND_URL = $BaseUrl
  $env:CPH2_FRONTEND_URL = $BaseUrl
  $env:CPH2_COMMERCIAL_UX_ARTIFACT_DIR = $ArtifactRoot
  $env:SLICE_E_VERIFICATION_RUN_ID = $GateRunId

  Write-GateLog "Gate run id: $GateRunId"
  Write-GateLog "Artifacts: $ArtifactRoot"
  Write-GateLog "Logs: $GateLogDir"

  # --- Stop prior gate listeners on canonical ports ---
  Stop-GatePort $BackendPort "backend"
  Stop-GatePort $FrontendPort "frontend"
  Stop-NextDevProcesses $WebRoot
  Start-Sleep -Seconds 2

  # --- Start backend ---
  Write-GateLog "Starting backend on $BackendUrl"
  $backendOut = Join-Path $GateLogDir "backend.out.log"
  $backendErr = Join-Path $GateLogDir "backend.err.log"
  $BackendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "uv run uvicorn app.main:app --host 127.0.0.1 --port $BackendPort") `
    -WorkingDirectory $RepoRoot -PassThru `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr

  Push-Location $RepoRoot
  try {
    if (-not (Wait-HttpOk "$BackendUrl/health" 60 "Backend /health")) {
      throw "Backend /health not ready on $BackendUrl"
    }
    if (-not (Wait-HttpOk "$BackendUrl/health/ready" 60 "Backend /health/ready")) {
      throw "Backend /health/ready not ready on $BackendUrl"
    }

    $det = uv run python -c "from app.core.config import get_settings; s=get_settings(); print('ok' if s.biv_e2e_deterministic_allowed else 'off')" 2>&1
    if ($det -ne "ok") { throw "BIV_E2E_DETERMINISTIC_ENABLED not allowed in settings. Got: $det" }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $alembicHead = (uv run alembic heads 2>&1 | Out-String).Trim()
    $alembicCurrent = (uv run alembic current 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $prevEap
    Write-GateLog "Alembic head: $($alembicHead -replace '\s+', ' ')"
    Write-GateLog "Alembic current: $($alembicCurrent -replace '\s+', ' ')"

    Write-GateLog "Backend preflight: pid=$($BackendProc.Id); APP_ENV=$env:APP_ENV; deterministic=true; dispatcher=true"

    # --- E2E provision smoke (fail fast) ---
    $preflightRunId = "gate-preflight-$GateRunId"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $provisionRaw = uv run python scripts/e2e_biv_isolation.py provision --run-id $preflightRunId 2>&1 | Out-String
    $provisionExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($provisionExit -ne 0) { throw "E2E provision failed: $provisionRaw" }
    $provision = $provisionRaw.Trim() | ConvertFrom-Json
    if (-not $provision.email -or -not $provision.password) {
      throw "E2E provision missing email/password"
    }
    $masked = if ($provision.email.Length -gt 3) { "$($provision.email.Substring(0, 3))***" } else { "***" }
    Write-GateLog "E2E provision ok: email=$masked run_id=$preflightRunId"
    uv run python scripts/e2e_biv_isolation.py cleanup --run-id $preflightRunId | Out-Null

    # --- Backend regression (before browser) ---
    Invoke-GateStep "Backend pytest (intake / PRODUCT-01.4 / specificity / recovery)" {
      uv run pytest `
        tests/test_product_01_3a_biv_intake_gate.py `
        tests/test_product_01_4_commercial_foundation.py `
        tests/test_product_01_3a_3_specificity_gate_ux.py `
        tests/test_biv_result_delivery_recovery.py `
        tests/test_runtime_01g_concurrent_run_failure_recovery.py `
        -q --tb=short
    }
  } finally {
    Pop-Location
  }

  Push-Location $WebRoot
  try {
    $env:NODE_ENV = "production"
    Invoke-GateStep "Frontend typecheck" { npm run typecheck }
    Invoke-GateStep "Frontend unit tests" { npm run test:unit }

    Write-GateLog "Production build (clean .next)"
    Stop-NextDevProcesses $WebRoot
    Remove-NextBuildDirectory (Join-Path $WebRoot ".next")
    Invoke-GateStep "Frontend production build" { npm run build }

    Write-GateLog "Starting production frontend on $BaseUrl"
    $frontendOut = Join-Path $GateLogDir "frontend.out.log"
    $frontendErr = Join-Path $GateLogDir "frontend.err.log"
    $FrontendProc = Start-Process -FilePath "cmd.exe" `
      -ArgumentList @("/c", "set NODE_ENV=production&& npx next start -p $FrontendPort") `
      -WorkingDirectory $WebRoot -PassThru `
      -RedirectStandardOutput $frontendOut `
      -RedirectStandardError $frontendErr

    if (-not (Wait-HttpOk $BaseUrl 90 "Frontend root")) {
      throw "Frontend not ready at $BaseUrl"
    }
    if (-not (Wait-HttpOk "$BaseUrl/login" 30 "Frontend /login")) {
      throw "Frontend /login not ready at $BaseUrl/login"
    }
    Assert-ProductionFrontendChunks $BaseUrl
    Write-GateLog "Frontend preflight: pid=$($FrontendProc.Id); mode=production; baseURL=$BaseUrl"

    $env:CPH2_PRODUCTION_REUSE_SERVER = "true"

    Assert-BackendReady "Slice E"
    Invoke-GateStep "Slice E browser suite (16 scenarios)" {
      npx playwright test -c playwright.commercial-ux-slice-e.config.ts
    }
    Assert-BackendReady "RUNTIME-01F"
    Invoke-GateStep "RUNTIME-01F golden path" { npm run test:e2e:runtime-01f }
    Assert-BackendReady "RUNTIME-01G"
    Invoke-GateStep "RUNTIME-01G concurrent/failure recovery" { npm run test:e2e:runtime-01g-concurrent-run-failure-recovery }
    Assert-BackendReady "BIV result-delivery"
    Invoke-GateStep "BIV result-delivery recovery" { npm run test:e2e:biv-result-delivery-recovery }
    Assert-BackendReady "production-boundary"
    Invoke-GateStep "Production-boundary gate" { npm run test:e2e:production-boundary }
    Assert-BackendReady "Commercial UX A-D"
    Invoke-GateStep "Commercial UX A-D regression" {
      npx playwright test -c playwright.commercial-ux-verification.config.ts
    }

    Push-Location $RepoRoot
    try {
      Invoke-GateStep "Verification layer hygiene (git diff --check)" {
        git diff --check -- `
          web/scripts/run-commercial-ux-slice-e-gate.ps1 `
          web/e2e/runtime-01e-production-boundary.spec.ts `
          web/e2e/helpers/cph2.ts `
          web/e2e/helpers/commercial-intake-verification.ts `
          web/e2e/commercial-ux-slice-e-verification.spec.ts `
          web/e2e/runtime-01g-concurrent-run-failure-recovery.spec.ts
      }
    } finally {
      Pop-Location
    }

    $shots = Get-ChildItem $ArtifactRoot -Filter "*.png" -ErrorAction SilentlyContinue
    Write-GateLog "Screenshot artifacts: $($shots.Count) files in $ArtifactRoot"
    foreach ($required in @(
        "step1-desktop", "step1-mobile", "market-desktop", "audience-desktop",
        "economics-desktop", "materials-desktop", "validation-error", "autosave-error",
        "review-desktop", "review-mobile", "review-production-no-diagnostics"
      )) {
      $match = $shots | Where-Object { $_.BaseName -eq $required }
      if (-not $match) { throw "Missing required screenshot artifact: $required.png" }
    }

    Write-GateLog "COMPOSITE GATE PASS"
  } finally {
    Pop-Location
  }
} catch {
  Write-GateLog "COMPOSITE GATE FAIL: $($_.Exception.Message)"
  $ExitCode = 1
} finally {
  if ($FrontendProc -and -not $FrontendProc.HasExited) {
    Write-GateLog "Stopping frontend PID $($FrontendProc.Id)"
    Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
  }
  if ($BackendProc -and -not $BackendProc.HasExited) {
    Write-GateLog "Stopping backend PID $($BackendProc.Id)"
    Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
  }
}

exit $ExitCode
