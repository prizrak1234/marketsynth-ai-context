# CPH.3 — Migration and rollback

- Revision: `20260715_0037` → revises `20260614_0036`
- Adds `users.password_hash`, `users.last_login_at`, table `browser_sessions`
- Apply only on clean pilot DB (`botfazer_cph1`)
- Do not stamp/repair legacy `botfazer` orphan DB
- Downgrade drops session table + password columns (sessions lost)

```powershell
$env:DATABASE_URL="postgresql+asyncpg://…/botfazer_cph1"
uv run alembic upgrade head
```
