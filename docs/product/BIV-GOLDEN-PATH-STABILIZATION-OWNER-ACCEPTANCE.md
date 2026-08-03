# BIV Golden Path Stabilization — Owner Acceptance

**Status:** `owner_accepted` (2026-07-28)

**Prior status:** `waiting_for_owner_validation` → owner smoke **PASS**

## Owner-confirmed behaviors

| Check | Result |
|-------|--------|
| Budget autofill regression | Not reproduced |
| Confirm → one run | PASS |
| Duplicate restart | Absent |
| Completed report visible | PASS |
| Refresh preserves report | PASS |
| Reopen project restores same report | PASS |
| Blank screen | Absent |

## Automated gate (pre-owner)

| Gate | Result |
|------|--------|
| Backend `test_product_01_3a_biv_intake_gate` + `test_product_01_3b_research_run_smoke` | **25/25 PASS** |
| Playwright A–I run 1 (`BIV_STABILIZATION_RUN_ID=biv-gp-run9b`) | **9/9 PASS** (~18.7 min) |
| Playwright A–I run 2 (`BIV_STABILIZATION_RUN_ID=biv-gp-run10`) | **9/9 PASS** (~18.9 min) |
| `project_limit_exceeded` during E2E | **0** (per-run isolated user + cleanup) |

## Browser evidence (scenarios)

Artifacts written under `web/test-results/biv-golden-path/{runId}/` when `saveScenarioArtifact` runs:

| Scenario | Evidence |
|----------|----------|
| A | Budget/intake autofill semantics |
| B | One POST, one idempotency key |
| C | Double confirm → still one POST |
| D | Refresh during running → same `run_id` |
| E | Failure panel (no blank screen) |
| F | Workspace shell never empty |
| G | `customer_report` + `biv-report-hydrated` after backend succeeded |
| H | Refresh POST count = 0, same `run_id`, report visible |
| I | Isolated owner flow: POST=1, refresh + projects list reopen persistence |

### G state sequence (verified)

`research_running` → backend `succeeded` → `customer_report` available via GET → UI `business-validation-result-card` + `biv-report-hydrated`

### E2E isolation

- Script: `scripts/e2e_biv_isolation.py` (`provision` / `cleanup`, `--dry-run`)
- Per-run user: `biv-e2e-{runId}@marketsynth.test`
- Project markers: `E2E-BIV-{runId}-{scenario}`, `test_project=true`, `e2e_run_id`, `e2e_scenario`

## E2E prerequisites (dev)

- Backend: `RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS=true` (see `.env.example`)
- Backend `:8000`, frontend `:3000`

### RUNTIME-01F — canonical commercial PASS (async `/runs`)

- Backend: `BIV_E2E_DETERMINISTIC_ENABLED=true`, `BIV_RUN_DISPATCHER_ENABLED=true`
- Artifacts: `web/test-results/runtime-01f-canonical-golden-path/{runId}/`
- Command: `npm run test:e2e:runtime-01f` (or `npx playwright test e2e/runtime-01f-canonical-golden-path.spec.ts`)

### Legacy regression (sync `/run`, short intake — not commercial PASS)

- `npx playwright test e2e/biv-golden-path.spec.ts`

## Known limitation (accepted for this slice)

Mechanics are green under mock research providers. **Real** search/fetch quality, source strength, and report substance are **out of scope** — tracked in **REAL-RESEARCH-READINESS** (next slice). QA-01 remains closed until real-research PASS.

## Next slice

**REAL-RESEARCH-READINESS** — real providers, evidence validation, source/report quality, latency/cost, one commercial case without mock.
