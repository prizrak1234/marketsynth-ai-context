# CPH.4 restore drill (Windows)

$ErrorActionPreference = "Stop"
$env:CPH4_CONFIRM_RESTORE = "1"
$Out = Join-Path $env:USERPROFILE "botfazer_backups\cph4"
$RunId = if ($args.Count -ge 1) { $args[0] } else { (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ").ToLower() }

Write-Host "CPH4 restore drill run_id=$RunId out=$Out"
uv run python -m scripts.cph4_run_restore_drill --out $Out --run-id $RunId @args[1..($args.Length)]
