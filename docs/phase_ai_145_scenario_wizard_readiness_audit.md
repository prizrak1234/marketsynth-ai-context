# Phase AI.145 — Scenario Auto-Run Wizard Readiness Audit

**Date:** 2026-06-03  
**Scope:** Manual step wizard over existing marketing-to-publish APIs (AI.136–AI.144).

---

## 1. Product intent

Users pick a business scenario and advance through a **guided campaign pipeline** without learning internal mechanics. Each click runs **exactly one** wizard step — no background worker, no full auto-run via API.

---

## 2. Wizard steps (15)

| Step | Action |
|------|--------|
| `create_plan` | Scenario → draft `MarketingPlan` |
| `approve_plan` | Existing approve gate |
| `create_execution_run` | Create + start run |
| `execute_specialists` | All plan tasks (idempotent skip) |
| `approve_copywriter_output` | Approve copywriter **or** sales_copywriter |
| `create_content_asset` | AI.40 copywriter path or wizard sales-copy path |
| `submit_asset` / `approve_asset` | Existing asset review gates |
| `create_media_brief` | From approved asset |
| `submit_media_brief` / `approve_media_brief` | Existing brief gates |
| `create_publication_package` | Telegram package from asset |
| `submit_package` / `approve_package` | Existing package gates |
| `create_dry_run_job` | Queued job only — **no real publish** |

---

## 3. API

```
POST /projects/{id}/scenario-wizard-runs          { "scenario_id": "..." }
GET  /projects/{id}/scenario-wizard-runs
GET  /projects/{id}/scenario-wizard-runs/{run_id}
POST /projects/{id}/scenario-wizard-runs/{run_id}/advance   ← one step
```

Contract: `ScenarioWizardRun` in `contracts.py`  
Engine: `app/services/scenario_wizard_service.py`  
Persistence: `scenario_wizard_runs` table

---

## 4. Safety gates (AI.141)

| Invariant | Enforcement |
|-----------|-------------|
| Approval rules | Reuses submit/approve services |
| No real Telegram publish | Job stays `queued`; no `execute` call |
| No external providers | No media generation / real send in wizard |
| Frozen layers | No changes to AI.39 / v2 deps |
| Idempotent advance | Steps check existing resource IDs in `step_results` |

---

## 5. Provenance (AI.142)

- `MarketingPlan.project_context.wizard_run_id`
- `ContentAsset.asset_metadata.wizard_run_id` (sales-copy path)
- `GET .../provenance/content-production/{job_id}` → `source_wizard_run_id`

---

## 6. UI (AI.140)

Marketing plans panel:

- Scenario cards: **Start wizard**
- Wizard panel: step list, current step, resource IDs, **Advance step**, failure reason, resume via GET after reload

---

## 7. Seed (AI.143)

Default seed unchanged. Optional:

```bash
uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen
```

Seed script may loop `advance` internally (demo only) — API still exposes single-step advance only.

---

## 8. Regression

```bash
uv run pytest tests/test_phase_ai_144_scenario_wizard_regression.py -q
```

Covers: dental scenario step-by-step to queued dry-run job, terminal advance conflict, provenance `source_wizard_run_id`.

---

## 9. Verification checklist

- [x] 15-step wizard engine
- [x] Manual advance endpoint
- [x] UI wizard panel
- [x] Safety invariants
- [x] Provenance linkage
- [x] Optional `--wizard` seed
- [x] Regression tests
- [x] Docs sync
