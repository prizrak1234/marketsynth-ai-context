# Testing Strategy

> **Dev gate:** [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)  
> **Last updated:** 2026-07-29

---

## Pre-commit commands

```bash
uv run ruff check app tests
uv run mypy app
uv run pytest
```

---

## Test layout

| Path | Purpose |
|------|------|
| `tests/` | All pytest tests |
| `tests/test_phase_ai_*` | Phase regression suites |
| `tests/test_architecture_subsystem_standard.py` | Subsystem invariant |
| `tests/test_workflow_library_pilot.py` | n8n library pilot |

**Rule:** Every new endpoint requires tests in `tests/`.

---

## Test categories

### Unit / domain

- Business rules in `app/domain/`
- Contract validation in `app/schemas/`
- Knowledge modules in `app/knowledge/`

### API integration

- FastAPI TestClient against route handlers
- Auth dependency overrides where needed
- Sanitization and error envelope

### Phase regression (smoke)

Frozen phases ship dedicated regression files — run on touch:

| Phase | Command |
|-------|---------|
| Marketing dept v2 | `pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q` |
| Scenario builder | `pytest tests/test_phase_ai_134_scenario_builder_regression.py -q` |
| Scenario wizard | `pytest tests/test_phase_ai_144_scenario_wizard_regression.py -q` |
| Campaign layer | `pytest tests/test_phase_ai_154_campaign_layer_regression.py -q` |
| Control center | `pytest tests/test_phase_ai_164_campaign_control_center_regression.py -q` |
| Action center | `pytest tests/test_phase_ai_174_campaign_action_center_regression.py -q` |
| Business operator | `pytest tests/test_phase_ai_184_business_operator_regression.py -q` |
| Operator assist | `pytest tests/test_phase_ai_194_business_operator_assist_regression.py -q` |
| LLM fallback | `pytest tests/test_phase_ai_204_business_operator_llm_fallback_regression.py -q` |
| Brief intake | `pytest tests/test_phase_ai_214_campaign_brief_intake_regression.py -q` |
| Data tools | `pytest tests/test_phase_ai_224_marketing_data_tools_regression.py -q` |
| Skills layer | `pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q` |
| Skill-campaign | `pytest tests/test_phase_ai_244_skill_campaign_integration_regression.py -q` |
| Supervisor | `pytest tests/test_phase_ai_254_campaign_supervisor_regression.py -q` |
| Workflow layer | `pytest tests/test_phase_ai_264_campaign_workflow_layer_regression.py -q` |
| Identity H2.8E | `pytest tests/test_phase_h2_8e_identity_subsystem.py tests/test_phase_h2_8d_identity_engine.py -q` |
| Subsystem standard | `pytest tests/test_architecture_subsystem_standard.py -q` |
| Workflow library | `pytest tests/test_workflow_library_pilot.py -q` |

---

## Smoke vs regression vs acceptance

| Level | Purpose | Who |
|-------|---------|-----|
| **Smoke** | Fast path works | CI / dev |
| **Regression** | Frozen phase unchanged | CI on related changes |
| **Owner acceptance** | Browser visual + real external calls | Owner |

Commercial smoke: [docs/product/PRODUCT-01.3A-SMOKE-PROTOCOL.md](../docs/product/PRODUCT-01.3A-SMOKE-PROTOCOL.md)  
QA harness: [docs/product/PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md](../docs/product/PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md)

---

## Demo & seed data

```bash
uv run python scripts/seed_e2e_demo.py
uv run python scripts/seed_e2e_demo.py --include-v2-marketing
uv run python scripts/seed_e2e_demo.py --scenario dental_clinic_lead_gen
uv run python scripts/seed_e2e_demo.py --wizard --scenario dental_clinic_lead_gen
```

---

## Critical scenarios (commercial)

1. **BIV golden path** — intake confirm → analysis → structured report → earned verdict
2. **Launch Pack** — blocked when BIV invalid; offer review when valid
3. **Telegram publish** — dry-run vs real; approval gate
4. **Video smoke** — explicit_confirmation required
5. **Campaign create** — blocked without confirmed brief_id
6. **Supervisor** — read-only, no side effects
7. **Identity** — preflight blocks without manifest

---

## Coverage philosophy

- Meaningful behavior coverage over line coverage targets
- Frozen phases: regression file must stay green
- No tests that only assert obvious mocks
- Real external calls only in owner-acceptance / marked integration tests

---

## CI expectations

- Full `pytest` on PR
- Ruff + mypy per DEVELOPMENT.md
- Phase regression when touching related modules
