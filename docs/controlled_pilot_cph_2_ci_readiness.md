# CPH.2 — CI readiness notes

## Ready

- Playwright in `web/` with Chromium
- Env-driven URLs/mode/API key
- Disposable DB name checks
- Artifacts gitignored (`web/test-results`, `web/playwright-report`)
- Timed-out serial suite (180s/test)

## Not in CPH.2

- Full GitHub Actions / deploy pipeline
- Containerized Postgres service matrix
- Visual snapshot baseline CI

## Suggested later CI sketch

1. Start Postgres service → create `botfazer_cph1` → `alembic upgrade head`
2. Seed CPH2 user → export API key to env
3. Start uvicorn + `next start` (build first)
4. `npx playwright test`
5. Upload traces/screenshots on failure

Use service accounts only — never personal keys.
