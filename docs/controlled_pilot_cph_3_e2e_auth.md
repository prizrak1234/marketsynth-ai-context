# CPH.3 — E2E auth

Orchestrator: `scripts/cph3_run_browser_e2e.ps1`

Env (no API keys):

- `CPH3_E2E_EMAIL` / `CPH3_E2E_PASSWORD`
- `CPH3_E2E_EMAIL_B` / `CPH3_E2E_PASSWORD_B` (isolation)

Specs: `web/e2e/auth.spec.ts`, updated `commercial-happy-path.spec.ts`.

Login uses real `/login` UI; cookies authenticate API; localStorage API-key shortcut removed.
