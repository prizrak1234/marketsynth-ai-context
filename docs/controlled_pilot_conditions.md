# Controlled pilot conditions (CONDITIONAL_GO)

Pilot with **remote** users (non-loopback) is allowed only after **all** of the
following are true and owner-acknowledged:

## Cutover (blocking for remote access)

1. **HTTPS** frontend and API edge live (e.g. Caddy in `deploy/caddy/Caddyfile`).
2. `BROWSER_SESSION_COOKIE_SECURE=true`
3. Canonical public origins listed in `BROWSER_ALLOWED_ORIGINS` (exact match; no `*`).
4. CSRF still rejects missing/disallowed Origin for cookie mutations.
5. Manual login matrix re-run on the **public** HTTPS host (not only localhost).

## Accounts & access

6. Unique named accounts for ≤3 users (provision via CPH.3 script on `botfazer_cph1`).
7. No public signup; invites only.
8. Users receive pilot disclaimer + data handling notice.

## Operations

9. Named operator + support contact + incident contact.
10. Daily backup schedule enabled; latest restore drill status known.
11. `/health/live` and `/health/ready` monitored (or polled by operator).
12. Execution/provider feature flags remain **false**.
13. No real ad spend; no provider publishing.

## Already satisfied locally (do not regress)

- Auth session model + owner isolation
- Migration fail-fast guard
- Backup/restore drill evidence
- Login regression fix (no pre-submit invalid_credentials)

## Local-only exception

Owner may exercise **internal** loopback pilots (developer machines) under
HTTP localhost without HTTPS, provided traffic never leaves the trusted host and
users are the operator themselves — still max 1–3 accounts, same execution firewall.
