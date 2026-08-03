# Password recovery v1 (local pilot)

Browser flow:

1. `/login` → **Забыли пароль?** → `/forgot-password`
2. `POST /auth/password-reset/request` (always generic response)
3. Operator: `uv run python scripts/create_password_reset_link.py --email … --require-db botfazer_cph1 [--open-browser]`
4. `/reset-password?token=…` → new password → sessions revoked → `/login?passwordReset=success`

Design boundary: `PasswordResetService` is independent of email delivery. Local pilot uses the operator script; email provider is out of scope for this phase.

Security: hash-only tokens, one-time use, revoke prior pending, rate limits, no raw token/password in API or logs.
