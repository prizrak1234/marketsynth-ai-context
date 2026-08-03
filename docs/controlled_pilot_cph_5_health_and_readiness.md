# CPH.5 — Health and readiness

## Endpoints

| Path | Purpose | Deep deps |
|------|---------|-----------|
| `GET /health/live` | Process alive | None |
| `GET /health/ready` | Safe for traffic | DB, revision, config, firewall flags |
| `GET /health` | Legacy combined | DB + Redis |
| `GET /health/operations` | Rich ops snapshot | DB (public; keep internal in real deploy) |

## Readiness semantics

200 only when `ready=true`.

Includes:

- configuration validation
- PostgreSQL reachability
- Alembic expected vs actual (strict in pilot-like)
- browser session subsystem present
- execution firewall flags disabled for pilot/production
- backup age **warn** (does not alone take liveness down)

Never calls LLM/providers.

Response excludes credentials and stack traces.
