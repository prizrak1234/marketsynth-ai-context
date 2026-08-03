# Phase AI.110 — Marketing Department v2 Roadmap

**Status:** Historical roadmap; **superseded by AI.119 freeze** (baseline **14-role department**).  
**Prerequisite:** AI.27–AI.39 frozen marketing pipeline.  
**Freeze:** [phase_ai_119_marketing_department_v2_freeze.md](phase_ai_119_marketing_department_v2_freeze.md)  
**Readiness:** [phase_ai_125_marketing_department_v2_readiness_audit.md](phase_ai_125_marketing_department_v2_readiness_audit.md)

---

## Goal

Expand the marketing department from **6 frozen roles** to a **14-role baseline**:

- Frozen six pipeline **unchanged** in order and `_DEPENDENCY_MATRIX`.
- Eight v2 roles executable via separate `V2_SPECIALIST_DEPENDENCIES`.
- Orchestrator planning still selects **frozen six only**.

---

## Baseline 14-role department (AI.119)

| # | Role | Enum | Phase | Execution |
|---|------|------|-------|-----------|
| 1–6 | Frozen pipeline | `strategist` … `analyst` | AI.31–AI.36 | Enabled |
| 7 | Offer Strategist | `offer_strategist` | AI.111 | Enabled |
| 8 | Funnel Architect | `funnel_architect` | AI.112 | Enabled |
| 9 | Lead Magnet Specialist | `lead_magnet_specialist` | AI.113 | Enabled |
| 10 | Sales Copywriter | `sales_copywriter` | AI.114 | Enabled |
| 11 | Email/DM Specialist | `email_dm_specialist` | AI.115 | Enabled |
| 12 | CRO Specialist | `cro_specialist` | AI.116 | Enabled |
| 13 | SMM Strategist | `smm_strategist` | AI.117 | Enabled |
| 14 | Ad Creative Strategist | `ad_creative_strategist` | AI.118 | Enabled |

Registry: `app/agents/marketer/marketing_specialist_registry.py`

---

## Phase status (AI.111–AI.125)

| Phase | Status | Deliverable |
|-------|--------|-------------|
| AI.111 | Done | Offer Strategist |
| AI.112 | Done | Funnel Architect |
| AI.113 | Done | Lead Magnet Specialist |
| AI.114 | Done | Sales Copywriter |
| AI.115 | Done | Email/DM Specialist |
| AI.116 | Done | CRO Specialist (`cro_recommendations`) |
| AI.117 | Done | SMM Strategist |
| AI.118 | Done | Ad Creative Strategist |
| AI.119 | Done | Department v2 freeze |
| AI.120 | Done | V2 execution panel (grouped pipelines + dependency hints) |
| AI.121 | Done | V2 output cards by `output_type` |
| AI.122 | Done | README / AGENTS / DEVELOPMENT sync |
| AI.123 | Done | V2 regression smoke tests |
| AI.124 | Done | Optional `--include-v2-marketing` demo seed |
| AI.125 | Done | Readiness audit doc |

---

## Frozen pipeline (unchanged)

```
strategist → researcher → content_planner → copywriter → critic → analyst
```

---

## V2 dependency matrix (enforced separately)

| Specialist | Dependencies |
|------------|--------------|
| offer_strategist | strategist, researcher |
| funnel_architect | strategist, researcher, offer_strategist |
| lead_magnet_specialist | offer_strategist, funnel_architect |
| sales_copywriter | offer_strategist, researcher |
| email_dm_specialist | offer_strategist, sales_copywriter |
| cro_specialist | offer_strategist, funnel_architect, sales_copywriter |
| smm_strategist | strategist, researcher, content_planner, offer_strategist |
| ad_creative_strategist | offer_strategist, researcher, sales_copywriter |

Implementation: `V2_SPECIALIST_DEPENDENCIES` in `marketing_pipeline_execution_service.py`.

---

## Regression

```bash
uv run pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q
uv run pytest tests/test_phase_ai_119_marketing_department_v2_freeze.py -q
uv run pytest tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

Optional v2 demo seed:

```bash
uv run python scripts/seed_e2e_demo.py --include-v2-marketing
```
