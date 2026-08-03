# CPH.2 — Test environment contract

## Required

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `…/botfazer_cph1` (never `botfazer`) |
| Alembic | `20260614_0036` (`current`) |
| `CPH2_BACKEND_URL` | `http://127.0.0.1:8000` |
| `CPH2_FRONTEND_URL` | `http://127.0.0.1:3000` |
| `NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE` | `backend` (happy path) or `hybrid` (smoke) |
| `CPH2_API_KEY` / `NEXT_PUBLIC_BOTFAZER_API_KEY` | pilot E2E user key from seed |
| Execution flags | leave default **off** (`REAL_EXECUTION_EXPANSION_ENABLED=false`, n8n off, Telegram publishing off) |

## Diagnostic

```bash
uv run python scripts/cph2_e2e_diag.py
```

Prints frontend/backend URLs, DB name, Alembic state, sanitized key, mode.  
**Fails** if mode=`mock`, DB=`botfazer`, or revision ≠ head.

## Seed auth

```bash
$env:DATABASE_URL="postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"
uv run python scripts/cph2_seed_pilot_user.py --write-env --refresh-api-key
```

Uses telegram_id `9100042` / email `cph2.pilot@marketsynth.local`. No UI login (product has API-key auth only). No production bypass routes.

## Auth approach

**C — Seeded API user + browser env Bearer key** (`NEXT_PUBLIC_BOTFAZER_API_KEY`). Session is the API key; no shared personal account. Owner isolation still enforced by backend.
