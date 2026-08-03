# CPH.3 — Pilot user provisioning

```powershell
$env:DATABASE_URL="postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"
$env:CPH3_PILOT_PASSWORD="…"
uv run python scripts/cph3_provision_pilot_user.py --email user@example.com --update --require-db botfazer_cph1
```

- Refuses wrong DB name (default require `botfazer_cph1`).
- Never prints password.
- Sets `role=owner`, `beta_access_status=approved`, scrypt `password_hash`.
- No public signup in CPH.3.
