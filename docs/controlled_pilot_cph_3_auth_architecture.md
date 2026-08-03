# CPH.3 — Auth architecture

**Decision: Option B** — API keys remain for service/CLI clients; browser uses a separate expiring session layer.

## Inventory (pre-CPH.3)

- Bearer API keys (`bfz_…`), hashed in `api_keys`, no expiry, revocable.
- No passwords, login UI, cookies, or sessions.
- CPH.2 E2E injected keys into `localStorage` — not pilot-safe.

## Pilot browser auth

| Concern | Implementation |
|---------|----------------|
| Credential | Email + password (`users.password_hash`, stdlib scrypt) |
| Session | `browser_sessions` table, **token hash only** |
| Transport | HttpOnly cookie `ms_pilot_session` |
| Lifetime | `BROWSER_SESSION_TTL_HOURS` (default 8) |
| Revocation | Logout / `POST /auth/sessions/{id}/revoke` |
| Current user | `GET /auth/me` |
| API keys | Unchanged for Bearer service clients |

## Auth preference

`get_current_user`: cookie session first, else Bearer API key.

## Migration

`20260715_0037` on pilot DB `botfazer_cph1` only.
