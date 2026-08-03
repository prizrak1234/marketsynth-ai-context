# PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01F — Commercial Landing verification gate
# One command: npm run test:e2e:commercial-ux-slice-f-gate

$ErrorActionPreference = "Stop"
$WebRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $WebRoot
$BackendPort = "8000"
$FrontendPort = "3000"
$BackendUrl = "http://127.0.0.1:$BackendPort"
$BaseUrl = "http://localhost:$FrontendPort"
$GateRunId = "slice-f-gate-$(Get-Date -Format 'yyyyMMddHHmmss')"
$GateLogDir = Join-Path $WebRoot "e2e-artifacts/commercial-ux-slice-f-gate/$GateRunId"
New-Item -ItemType Directory -Force -Path $GateLogDir | Out-Null

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
  foreach ($procId in (Get-PortListenerPids $Port)) {
    Write-GateLog "Stopping $Label listener PID $procId on port $Port"
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
}

function Stop-NextDevProcesses([string]$WebRootPath) {
  $normalized = (Resolve-Path $WebRootPath).Path.ToLower()
  Get-CimInstance Win32_Process -Filter "name='node.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = $_.CommandLine
    if ($null -ne $cmd -and $cmd -match "next\s+dev" -and $cmd.ToLower().Contains($normalized)) {
      Write-GateLog "Stopping next dev PID $($_.ProcessId)"
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
        Start-Sleep -Seconds 2
        cmd.exe /c "rmdir /s /q `"$target`"" 2>$null | Out-Null
      }
    }
  }
}

function Assert-ProductionFrontendChunks([string]$Url) {
  $html = (Invoke-WebRequest -Uri "$Url/" -UseBasicParsing -TimeoutSec 30).Content
  if ($html -match 'src="/_next/static/chunks/main-app\.js"') {
    throw "Production frontend serves dev-mode chunks (main-app.js)"
  }
  Write-GateLog "Production chunk probe ok"
}

function Assert-BackendReady([string]$Label) {
  if (-not (Wait-HttpOk "$BackendUrl/health" 15 "Backend /health ($Label)")) {
    throw "Backend /health unavailable before $Label"
  }
  if (-not (Wait-HttpOk "$BackendUrl/health/ready" 15 "Backend /health/ready ($Label)")) {
    throw "Backend /health/ready unavailable before $Label"
  }
}

function Assert-NoPreviewCredentials() {
  Push-Location $RepoRoot
  try {
    $pwdHits = git grep -n "Owner-SliceE-Preview1" 2>$null
    if ($LASTEXITCODE -eq 0 -and $pwdHits) {
      throw "Preview password still present in repo: $pwdHits"
    }
    Write-GateLog "Credential cleanup grep: PASS"
  } finally {
    Pop-Location
  }
}

try {
  $env:APP_ENV = "development"
  $env:BIV_E2E_DETERMINISTIC_ENABLED = "true"
  Assert-NoPreviewCredentials
  Stop-GatePort $BackendPort "backend"
  Stop-GatePort $FrontendPort "frontend"
  Stop-NextDevProcesses $WebRoot
  Start-Sleep -Seconds 2
  Remove-NextBuildDirectory (Join-Path $WebRoot ".next")

  Push-Location $WebRoot
  try {
    Write-GateLog "Gate run id: $GateRunId"
    Write-GateLog "Logs: $GateLogDir"

    Write-GateLog "Starting backend on $BackendUrl"
    $BackendProc = Start-Process -FilePath "cmd.exe" `
      -ArgumentList @("/c", "cd /d `"$RepoRoot`" && uv run uvicorn app.main:app --host 127.0.0.1 --port $BackendPort") `
      -WorkingDirectory $RepoRoot -PassThru `
      -RedirectStandardOutput (Join-Path $GateLogDir "backend.out.log") `
      -RedirectStandardError (Join-Path $GateLogDir "backend.err.log")

    if (-not (Wait-HttpOk "$BackendUrl/health" 90 "Backend /health")) { throw "Backend not ready" }
    if (-not (Wait-HttpOk "$BackendUrl/health/ready" 90 "Backend /health/ready")) { throw "Backend not ready" }

    Invoke-GateStep "Frontend typecheck" { npm run typecheck }
    Invoke-GateStep "Frontend unit tests (incl. landing)" { npm run test:unit }

    $env:NODE_ENV = "production"
    Invoke-GateStep "Frontend production build" { npm run build }

    Write-GateLog "Starting production frontend on $BaseUrl"
    $FrontendProc = Start-Process -FilePath "cmd.exe" `
      -ArgumentList @("/c", "set NODE_ENV=production&& npx next start -p $FrontendPort") `
      -WorkingDirectory $WebRoot -PassThru `
      -RedirectStandardOutput (Join-Path $GateLogDir "frontend.out.log") `
      -RedirectStandardError (Join-Path $GateLogDir "frontend.err.log")

    if (-not (Wait-HttpOk $BaseUrl 90 "Frontend root")) { throw "Frontend not ready" }
    Assert-ProductionFrontendChunks $BaseUrl

    $env:SLICE_F_REUSE_SERVER = "true"
    $env:SLICE_F_PRODUCTION_BUILD = "true"
    $env:CAP_REGISTRY_REUSE_SERVER = "true"
    $env:CAP_REGISTRY_PRODUCTION_BUILD = "true"
    $env:CPH2_PRODUCTION_REUSE_SERVER = "true"

    Assert-BackendReady "Slice F landing"
    Invoke-GateStep "Commercial UX Slice F landing E2E (A-Q)" {
      npx playwright test -c playwright.commercial-ux-slice-f.config.ts
    }

    Assert-BackendReady "capability-registry production"
    Invoke-GateStep "Capability registry E2E production phase" {
      npx playwright test -c playwright.capability-registry.config.ts --grep-invert "D developer"
    }

    Assert-BackendReady "production-boundary"
    Invoke-GateStep "Production-boundary E2E" { npm run test:e2e:production-boundary }

    Assert-BackendReady "Slice E browser regression"
    Invoke-GateStep "Commercial UX Slice E (16 scenarios)" {
      npx playwright test -c playwright.commercial-ux-slice-e.config.ts
    }

    Assert-BackendReady "Commercial UX A-D regression"
    Invoke-GateStep "Commercial UX A-D (12 scenarios)" {
      npx playwright test -c playwright.commercial-ux-verification.config.ts
    }

    Assert-BackendReady "RUNTIME-01F"
    Invoke-GateStep "RUNTIME-01F golden path" { npm run test:e2e:runtime-01f }

    Assert-BackendReady "RUNTIME-01G"
    Invoke-GateStep "RUNTIME-01G concurrent recovery" { npm run test:e2e:runtime-01g-concurrent-run-failure-recovery }

    Assert-BackendReady "BIV result-delivery recovery"
    Invoke-GateStep "BIV result-delivery recovery" { npm run test:e2e:biv-result-delivery-recovery }

    Write-GateLog "SLICE F COMMERCIAL LANDING GATE PASS"
  } finally {
    Pop-Location
  }
} catch {
  Write-GateLog "SLICE F COMMERCIAL LANDING GATE FAIL: $($_.Exception.Message)"
  $ExitCode = 1
} finally {
  if ($FrontendProc -and -not $FrontendProc.HasExited) {
    Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
  }
  if ($BackendProc -and -not $BackendProc.HasExited) {
    Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
  }
  Stop-GatePort $FrontendPort "frontend"
  Stop-GatePort $BackendPort "backend"
  Stop-NextDevProcesses $WebRoot
}

exit $ExitCode
