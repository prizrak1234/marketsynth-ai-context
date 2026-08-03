# CPH.5 — Rollback runbook

## Principles

- Retain `botfazer_cph1` unless restore is intentional
- Schema is forward-only; incompatible app downgrade may require CPH.4 restore
- No remote git operations in controlled hardening

## Steps

1. Identify bad release (commit SHA)
2. Stop uvicorn / Next / Caddy (stop traffic)
3. Keep database
4. Decide: app-only rollback vs DB restore
5. Restore previous local application tree
6. `check-revision` + `/health/ready`
7. Auth smoke
8. Incident note (times, cause, outcome)

Dry-run: `uv run python -m scripts.cph5_rollback_dry_run`
