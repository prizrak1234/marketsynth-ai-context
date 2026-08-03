# CPH.5 — Deployment architecture

## Decision: OPTION B

**Selected:** isolated local services behind an optional reverse proxy (Caddy).

| Layer | Mechanism |
|-------|-----------|
| PostgreSQL / Redis | Existing `docker-compose.yml` |
| Backend | `uvicorn app.main:app` on `127.0.0.1:8000` |
| Frontend | `next build` + `next start` on `127.0.0.1:3000` |
| HTTPS edge | Optional `deploy/caddy/Caddyfile` (`pilot.localhost`) |

Not selected: full app Docker Compose (no Dockerfiles yet); Kubernetes.

## Why B

Cookie sessions + CSRF need explicit origins (or same-origin via proxy). Existing Compose already covers data services. Adding a thin TLS proxy is enough for production-like validation without inventing an orchestration platform.

## Guarantees

- No automatic Alembic migrate/stamp
- Fail-fast config + revision guards in `pilot` / `staging` / `production`
- Separate liveness vs readiness
- Security headers on API and Next
- CPH.4 backup/restore remain the data recovery path

## Scripts

- `scripts/cph5_validate_config.py`
- `scripts/cph5_start_pilot.ps1`
- `scripts/cph5_post_deploy_smoke.py`
- `scripts/cph5_rollback_dry_run.py`
