# Phase AI.119 — Marketing Department v2 Freeze

**Status:** Frozen baseline (14 roles; 8 v2 executable).  
**Prerequisite:** AI.111–AI.118 specialist execution phases.

---

## Baseline 14-role department

| # | Role | Enum | Execution |
|---|------|------|-----------|
| 1–6 | Frozen pipeline | `strategist` … `analyst` | Enabled (AI.31–AI.36) |
| 7 | Offer Strategist | `offer_strategist` | Enabled (AI.111) |
| 8 | Funnel Architect | `funnel_architect` | Enabled (AI.112) |
| 9 | Lead Magnet Specialist | `lead_magnet_specialist` | Enabled (AI.113) |
| 10 | Sales Copywriter | `sales_copywriter` | Enabled (AI.114) |
| 11 | Email/DM Specialist | `email_dm_specialist` | Enabled (AI.115) |
| 12 | CRO Specialist | `cro_specialist` | Enabled (AI.116) |
| 13 | SMM Strategist | `smm_strategist` | Enabled (AI.117) |
| 14 | Ad Creative Strategist | `ad_creative_strategist` | Enabled (AI.118) |

Registry: `app/agents/marketer/marketing_specialist_registry.py`

---

## Frozen six (unchanged)

```
strategist → researcher → content_planner → copywriter → critic → analyst
```

- `MarketingPipelineExecutionService.pipeline_order()` — frozen order only
- `_DEPENDENCY_MATRIX` — frozen six only
- Orchestrator planning — frozen six only (`build_marketing_execution_plan`)

---

## V2 dependency matrix (separate)

Enforced via `V2_SPECIALIST_DEPENDENCIES` in  
`app/services/marketing_pipeline_execution_service.py`.

Executor allow-list: `app/agents/marketer/specialists/executor.py` (14 executable roles).

Planning mode **excludes** all v2 roles until a future orchestrator phase.

---

## Safety invariants (frozen at AI.119)

- No tools on specialist execution paths
- No child AgentRun delegation
- No ContentAsset auto-create from v2 specialists
- Manual `execute-specialist` only (no auto-run conveyor for v2)

---

## Regression

```bash
uv run pytest tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py -q
uv run pytest tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

Optional demo seed extension (AI.124):

```bash
uv run python scripts/seed_e2e_demo.py --include-v2-marketing
```

---

## Next (post-freeze)

AI.120–AI.125: UX integration, output cards, docs sync, regression smoke, readiness audit.
