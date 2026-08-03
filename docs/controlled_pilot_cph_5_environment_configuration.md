# CPH.5 — Environment configuration

## Profiles

| Profile | `APP_ENV` | Notes |
|---------|-----------|--------|
| development | `development` | Soft revision warnings; Secure cookies optional |
| test | `test` | Automated tests |
| pilot | `pilot` | Controlled pilot; fail-fast; execution flags off |
| staging | `staging` | Near-prod rehearsal |
| production | `production` | Strictest; no default DB passwords |

## Required pilot variables (placeholders only)

See `.env.example` CPH.5 block. Critical:

- `DATABASE_URL` → `botfazer_cph1`
- `PILOT_REQUIRE_DATABASE_NAME=botfazer_cph1` (recommended)
- `ALEMBIC_REVISION_FAIL_FAST=true`
- `DEBUG=false`
- Explicit `BROWSER_ALLOWED_ORIGINS`
- `BROWSER_SESSION_COOKIE_SECURE=true` when origins are HTTPS
- Execution/provider workers **false**

## Startup validation

`app.domain.pilot_config_validation` refuses pilot/staging/production when misconfigured. Development may warn.

Never silently repair config.
