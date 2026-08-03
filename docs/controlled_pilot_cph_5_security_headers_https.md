# CPH.5 — Security headers and HTTPS

## API (`SecurityHeadersMiddleware`)

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: DENY`
- `Permissions-Policy` (camera/mic/geo/payment disabled)
- Restrictive CSP for API JSON
- `Strict-Transport-Security` only when `BROWSER_SESSION_COOKIE_SECURE=true` and env is pilot-like

## Frontend (`web/next.config.ts`)

Production headers for UI pages including CSP compatible with Next.js (temporary `'unsafe-inline'` / `'unsafe-eval'` for App Router — document exception).

## HTTPS

OPTION B: Caddy terminates TLS (`deploy/caddy/Caddyfile`).

Under HTTPS:

- Secure cookies required
- HttpOnly + SameSite explicit
- No session tokens in URLs
- Frontend API base must not mix content unsafely

Local HTTP pilot may keep `BROWSER_SESSION_COOKIE_SECURE=false` with `http://` origins only.
