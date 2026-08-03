# CPH.5 — Pilot admin runbook

| Task | Command / action |
|------|------------------|
| Start stack | uvicorn + `next start` (+ optional Caddy) |
| Stop stack | Ctrl+C / stop processes |
| Live | `GET /health/live` |
| Ready | `GET /health/ready` |
| DB revision | `uv run python scripts/cph1_db_tools.py check-revision` |
| Provision user | `uv run python scripts/cph3_provision_pilot_user.py --require-db botfazer_cph1` |
| Revoke sessions | auth revoke API / SQL on disposable only |
| Logs by corr ID | search structlog JSON for `correlation_id` |
| Backup | `uv run python -m scripts.cph4_backup_pilot_db` |
| Restore drill | `uv run python -m scripts.cph4_run_restore_drill` |
| Deploy update | rebuild + restart (no auto-migrate) |
| Rollback | [rollback runbook](controlled_pilot_cph_5_rollback_runbook.md) |
| Smoke | `scripts/cph5_post_deploy_smoke.py` |
| Login failures | check rate limit + auth logs |
| DB outage | ready→503; stop writes; restore |
| Unknown revision | refuse startup; offline recovery plan |

Sanitize all printed URLs.
