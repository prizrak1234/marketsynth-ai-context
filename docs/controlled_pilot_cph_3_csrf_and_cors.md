# CPH.3 — CSRF and CORS

## CSRF

Cookie-authenticated unsafe methods (`POST`/`PUT`/`PATCH`/`DELETE`) require `Origin`/`Referer` in `BROWSER_ALLOWED_ORIGINS` (`BrowserSessionCsrfMiddleware`).

SameSite=Lax alone is **not** claimed sufficient for all deployments; Origin check is the primary app-level control for cookie sessions.

Bearer API-key clients skip cookie CSRF checks.

## CORS (development)

- Origins: `browser_allowed_origins` (localhost/127.0.0.1:3000)
- `allow_credentials=True`
- No wildcard origin with credentials
- Production: CORS middleware off until explicit pilot origins are configured
