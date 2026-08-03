# Phase AI.135 — Product Scenario Builder Readiness Audit

**Date:** 2026-06-03  
**Scope:** Business scenario templates over 14-role marketing department (AI.126–AI.134).

---

## 1. User entry point

Users pick a **business outcome** (restaurant launch, dental leads, etc.) instead of assembling specialists manually.

| Scenario ID | Name | Specialists |
|-------------|------|-------------|
| `restaurant_launch` | Restaurant Launch | 9 |
| `dental_clinic_lead_gen` | Dental Clinic Lead Gen | 8 |
| `expert_blogger_content_machine` | Expert / Blogger Content Machine | 7 |
| `telegram_bot_saas_launch` | Telegram Bot / SaaS Launch | 8 |
| `local_service_promo` | Local Service Promo | 7 |

Registry: `app/marketing/scenarios/registry.py` — **read-only**, no execution.

---

## 2. Plan creation flow (AI.129)

```
GET  /projects/{id}/marketing-scenarios
POST /projects/{id}/marketing-scenarios/{scenario_id}/create-plan
```

- Creates **draft** `MarketingPlan` with tasks from template.
- Sets `source_scenario_id` / `source_scenario_name`.
- Does **not** create an execution run.

---

## 3. Execution guard (AI.131)

After plan creation:

1. User approves plan (`POST .../marketing-plans/{id}/approve`) — existing endpoint.
2. User creates execution run (`POST .../marketing-plans/{id}/execution-runs`) — existing endpoint.
3. Specialists run through **unchanged** frozen + v2 pipeline.

No scenario-specific execution path was added.

---

## 4. Provenance (AI.133)

`GET .../provenance/content-production/{job_id}` includes:

- `source_scenario_id`
- `source_scenario_name`

(when the linked marketing plan was created from a scenario).

---

## 5. Frozen layer invariants

| Layer | Status |
|-------|--------|
| AI.39 frozen six pipeline | Unchanged |
| `V2_SPECIALIST_DEPENDENCIES` | Unchanged (8 v2 roles) |
| Specialist registry (14 roles) | Unchanged |
| Execution services | Reused as-is |

Regression: `uv run pytest tests/test_phase_ai_134_scenario_builder_regression.py -q`

---

## 6. UI (AI.130)

Agent chat **Marketing plans** panel includes **Start from scenario**:

- Scenario cards with task preview
- **Create plan** → draft plan in list (shows scenario name)

---

## 7. Optional seed (AI.132)

Default E2E seed unchanged. Optional:

```bash
uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen
```

Creates an additional draft scenario plan; prints `scenario_plan_id`.

---

## 8. Out of scope (unchanged)

- LangGraph / auto-run full department
- New specialist roles
- Scenario-specific executors
- Changing default demo seed without `--scenario`

---

## 9. Verification checklist

- [x] Five scenarios in registry
- [x] `ScenarioTemplate` contract
- [x] create-plan endpoint + tests
- [x] UI scenario picker
- [x] Provenance fields
- [x] Frozen layers regression assertions
- [x] Docs sync (README, AGENTS, DEVELOPMENT)
