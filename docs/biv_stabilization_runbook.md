# BIV Stabilization — Dev Smoke Runbook

Status: **owner_accepted** (2026-07-28). See [BIV-GOLDEN-PATH-STABILIZATION-OWNER-ACCEPTANCE.md](product/BIV-GOLDEN-PATH-STABILIZATION-OWNER-ACCEPTANCE.md).

## 1. Provision dev-smoke user (idempotent)

```powershell
cd C:\Users\User\.cursor\projects\c-Users\botfazer
$env:BIV_SMOKE_EMAIL = "biv-smoke@marketsynth.local"
$env:BIV_SMOKE_PASSWORD = "ChangeMeSmoke123!"
uv run python scripts/biv_provision_dev_smoke_user.py --update
$env:CPH3_E2E_EMAIL = $env:BIV_SMOKE_EMAIL
$env:CPH3_E2E_PASSWORD = $env:BIV_SMOKE_PASSWORD
```

## 2. Backend

```powershell
uv sync --extra dev
cp .env.example .env   # if needed
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. Frontend

```powershell
cd web
npm install
npm run dev
```

## 4. Backend tests

```powershell
cd ..
uv run pytest tests/test_cwf1_report_export.py tests/test_cwf1_evidence_validation.py tests/test_biv_stabilization.py -q
```

## 5. Playwright E2E (8 scenarios)

```powershell
cd web
$env:CPH3_E2E_EMAIL = "biv-smoke@marketsynth.local"
$env:CPH3_E2E_PASSWORD = "ChangeMeSmoke123!"
$env:CPH2_BACKEND_URL = "http://localhost:8000"
$env:CPH2_FRONTEND_URL = "http://localhost:3000"
npx playwright test e2e/biv-stabilization.spec.ts --trace on
```

Artifacts: `web/test-results/biv-stabilization/<run_id>/`

## 6. Legacy batch backfill

```powershell
uv run python scripts/biv_legacy_backfill.py --dry-run
uv run python scripts/biv_legacy_backfill.py --batch-size 50
```

## 7. Real-case smoke (API)

Three cases via `scripts/biv_real_case_smoke.py` (SaaS / weak brief / weak commercial).

## DoD checklist

- [ ] Backend progress replaces local ticker
- [ ] EvidenceItem / Finding contracts in output
- [ ] GO / CONDITIONAL_GO / PILOT_ONLY / HOLD / NO_GO verdict
- [ ] Batch legacy backfill
- [ ] Observability + `/diagnostics` (dev only)
- [ ] BIV error audit complete
- [ ] 8 Playwright scenarios PASS
- [ ] 3 real cases complete
- [ ] Export artifacts valid
- [ ] No blocker/critical/high defects

When all pass → `waiting_for_owner_validation` → owner smoke → **`owner_accepted`**.

Next: **REAL-RESEARCH-READINESS** (real providers; QA-01 still closed).
