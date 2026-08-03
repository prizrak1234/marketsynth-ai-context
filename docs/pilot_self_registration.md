# Pilot self-registration v1

**Status:** implemented locally (2026-07-16)

## Flag

`PUBLIC_SIGNUP_ENABLED`:

- unset → enabled only for `development` / `test`
- `production` / `staging` / `pilot` → default **false** unless explicitly set
- Server gate: `settings.signup_enabled`
- UI reads `GET /auth/signup-status`

## Flow

`/register` → `POST /auth/register` → **member** only → HttpOnly session → `/workspace`

Invite `/activate-invite` remains optional.

## Owner

Self-registration cannot create owner/admin. Existing
`joker.sam90@gmail.com` must use
`scripts/reset_pilot_user_password.py` (interactive) — no duplicate user.

## Password change

`POST /auth/change-password` (authenticated) revokes other sessions.
