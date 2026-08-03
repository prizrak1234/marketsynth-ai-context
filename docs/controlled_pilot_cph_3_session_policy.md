# CPH.3 — Session policy

- Absolute TTL: 8 hours (configurable).
- No remember-me in pilot.
- No refresh-token rotation (optional later).
- Logout / revoke → status `revoked`, cookie cleared.
- Expired sessions marked `expired` on access.
- Disabled users rejected.
- Raw token never in DB, logs, or JSON responses.
- Cookie: HttpOnly, SameSite=Lax, Secure when HTTPS, Path=/ .
