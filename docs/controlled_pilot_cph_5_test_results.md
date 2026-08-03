# CPH.5 — Test results

## Checkpoint

| Item | Value |
|------|-------|
| CPH.4 commit | `b723fde` `ops: verify pilot backup and restore recovery` |
| Branch | `master` (local; no push) |
| Source DB | `botfazer_cph1` @ `20260715_0037` |

## Deployment target

**OPTION B** — local uvicorn + Next production build + optional Caddy TLS (`deploy/caddy/Caddyfile`). Compose remains for Postgres/Redis.

## Automated tests

```text
uv run pytest tests/test_controlled_pilot_cph_5_observability.py \
  tests/test_health.py \
  tests/test_controlled_pilot_cph_3_browser_sessions.py \
  tests/test_controlled_pilot_cph_4_backup_restore.py -q
→ 33 passed
```

## Production build

`cd web && npm run build` — **passed** after minimal pilot-path TypeScript fixes (`ApiError` re-export, QueryStatus variants, domain mapping class, etc.).

## Live local stack

| Check | Result |
|-------|--------|
| `GET /health/live` | 200 alive |
| `GET /health/ready` | 200 ready; revision `20260715_0037`; DB `botfazer_cph1` |
| Frontend `/login` | 200 |
| Post-deploy smoke | OK (login, projects, write smoke project, logout) |
| Rollback dry-run | OK (`scripts/cph5_rollback_dry_run.py`) |

## Deferred / notes

- Full HTTPS with Secure cookies validated via config tests + Caddyfile; local visual stack uses HTTP origins.
- `/health/operations` remains public (document keep internal behind proxy for real remote pilot).
- No external public deployment.

## Confirmations

- No MarketingPlan approval / Agent Run / Campaign / execution / publication / provider / budget in smoke
- A7 / AI.592 / V2.2 paused
- No remote git ops
- No auto migrate/stamp
