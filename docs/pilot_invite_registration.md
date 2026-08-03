# Pilot invite registration

**Status:** implemented locally (2026-07-15)  
**Goal:** controlled account activation via one-time invitation — not public signup.

## Flow

Operator/admin creates invite for a specific email → one-time URL → user sets
display name + password → account + session → `/workspace`.

Login page secondary action: **Активировать приглашение** (not free registration).

## Schema

- Table `pilot_invites` (Alembic `20260715_0038`)
- Users gain `email_verified_at` on accept
- Pilot enablement uses existing `beta_access_status=approved` + `is_active`

## Operator

```bash
$env:DATABASE_URL='postgresql+asyncpg://botfazer:botfazer@localhost:5432/botfazer_cph1'
uv run python scripts/create_pilot_invite.py --email you@example.com --ttl-hours 48 --replace --clipboard --open-browser --require-db botfazer_cph1
```

- Prints metadata only (no raw token).
- Writes full URL once to `%TEMP%\ms_pilot_invite.url`.
- Copies URL to clipboard; optional `--open-browser`.
- First owner bootstrap: add `--grant-owner`.

Bare `/activate-invite` shows paste form for code or full link (not “invalid”).

Compromised invites: `--revoke-pending-only` or `--replace`.

## API

- `POST /auth/invitations` (OWNER/ADMIN)
- `GET /auth/invitations/{token}/status`
- `POST /auth/invitations/{token}/accept`
- `POST /auth/invitations/{invite_id}/revoke` (OWNER/ADMIN)

## Frontend

- `/activate-invite?token=...`
- `/login` → link to activation
