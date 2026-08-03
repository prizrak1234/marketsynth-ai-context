# CPH.5 — Deployment runbook

1. Ensure Compose Postgres/Redis up.
2. Confirm `DATABASE_URL` → `botfazer_cph1` @ `20260715_0037`.
3. `uv run python -m scripts.cph5_validate_config`
4. `uv run python scripts/cph1_db_tools.py check-revision`
5. **Do not** auto-migrate.
6. Build frontend: `cd web && npm run build`
7. Start backend: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`
8. Start frontend: `cd web && npm run start`
9. Optional: `caddy run --config deploy/caddy/Caddyfile`
10. Wait for `/health/live` and `/health/ready`
11. `uv run python -m scripts.cph5_post_deploy_smoke`
12. Record commit + revision + smoke JSON

Migrations remain a **separate** operator action.
