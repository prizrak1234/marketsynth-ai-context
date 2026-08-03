# Phase AI.39 — Marketing pipeline readiness audit

**Status:** Production freeze (AI.27–AI.38).  
**Purpose:** Cement the first closed marketing production conveyor before **AI.40+** (`ContentAsset` conversion branch).

---

## Canonical product flow

```
Marketing chat (planning only)
  → Save MarketingPlan (draft)
  → Approve MarketingPlan (version pinned)
  → Create MarketingPlanExecutionRun (queued snapshots from approved version)
  → Start run (running)
  → Execute specialists (manual, one task at a time):
        Strategist → Researcher → Content Planner → Copywriter → Critic → Analyst
  → Run succeeded (result_summary.mode = specialist_pipeline)
```

**Not in this flow:** auto-run all specialists, parallel execution, LangGraph marketing swarm, web research, tools on specialist path, `ContentAsset` creation from copy.

---

## Phase inventory

| Phase | Deliverable | Persistence / API |
|-------|-------------|-------------------|
| **AI.27** | Marketing orchestrator **planning only** | Chat `marketing_plan` block; `MarketingExecutionPlan` in run output; no specialist execution |
| **AI.28** | `MarketingPlan` + versions | `POST .../agent-chat/block-actions` (`save_marketing_plan`); `GET/POST .../marketing-plans`, `approve`, `archive` |
| **AI.29** | `MarketingPlanExecutionRun` skeleton | `POST .../marketing-plans/{id}/execution-runs` (approved only); `start`, `complete-placeholder`, `cancel` |
| **AI.30** | `MarketingSpecialistOutput` containers | Placeholder output per task; approve/archive; no LLM on placeholder path |
| **AI.31** | Strategist execution | `execute-specialist` → `output_type: strategy`, draft + v1 |
| **AI.32** | Researcher execution | Requires Strategist; `output_type: research` |
| **AI.33** | Content Planner execution | Requires Strategist + Researcher; `output_type: content_plan` |
| **AI.34** | Copywriter execution | Requires three priors; `output_type: content_copy` (not `ContentAsset`) |
| **AI.35** | Critic execution | Requires four priors; `output_type: critique`; recommendation only |
| **AI.36** | Analyst execution | Requires five priors; `output_type: analysis`; completes MVP six |
| **AI.37** | `MarketingPipelineExecutionService` | Shared dependency matrix + prior assembly + exact 409 messages |
| **AI.38** | Run auto-completion | When all snapshots `specialist_completed` → `succeeded` + `specialist_pipeline` summary |
| **AI.39** | **Freeze** | Docs + `test_phase_ai_39_marketing_pipeline_freeze_invariants.py`; no product code |

---

## Dependency matrix (canonical)

Order:

`strategist → researcher → content_planner → copywriter → critic → analyst`

| Specialist | Requires completed/active prior |
|------------|-------------------------------|
| strategist | — |
| researcher | strategist |
| content_planner | strategist, researcher |
| copywriter | strategist, researcher, content_planner |
| critic | strategist, researcher, content_planner, copywriter |
| analyst | strategist, researcher, content_planner, copywriter, critic |

**Satisfied when:** task snapshot `specialist_completed` **or** `MarketingSpecialistOutput` in `draft` / `approved` for same run. **Archived** outputs do not satisfy.

**First missing dependency** wins for 409 message text (matrix order).

Implementation: `app/services/marketing_pipeline_execution_service.py`.

---

## Frozen invariants

### Planning & chat (AI.27–AI.28)

- Marketing orchestrator chat returns `marketing_plan` block only — **no** `MarketingSpecialistOutput` rows from chat alone.
- `execution_mode: planning` in orchestrator output; no sub-agent child runs from planning path.
- Save plan creates **draft** `MarketingPlan` version 1; approve pins `approved_version_number`.

### Execution run (AI.29)

- Execution run creation requires **approved** plan.
- `marketing_plan_version_number` on run equals plan `approved_version_number` (not draft-only version).
- Specialist work uses **persisted** run snapshots + plan version goal/context — not raw chat JSON.

### Specialist execution (AI.31–AI.36)

- `POST .../tasks/{task_index}/execute-specialist` only when `run.status == running`.
- Each success: `MarketingSpecialistOutput` **draft** + version **1**; task → `specialist_completed`.
- No child `AgentRun` from specialist execution; no tools; no `raw_response` in `structured_data` (safe `llm_provider`, `model`, `mock` only).
- Approving specialist output does **not** create `ContentAsset`.

### Completion (AI.38)

- Run → `succeeded` only when **every** task snapshot is `specialist_completed`.
- `placeholder_completed`, `skipped`, `pending` **do not** count toward completion.
- `result_summary.mode == specialist_pipeline` with `completed_specialists`, `output_ids_by_specialist`, `task_count`.
- `ExecuteMarketingSpecialistTaskResponse`: `execution_run_status`, `run_completed` on last specialist when pipeline completes.

### Chat layer (AI.26)

- Agent chat send/history/block-action contracts frozen for marketing pipeline work — AI.39 regression asserts AI.26 response key subset unchanged.

---

## Endpoint families

| Family | Prefix / path |
|--------|----------------|
| Chat | `POST /projects/{id}/agent-chat`, `.../block-actions` |
| Plans | `/projects/{id}/marketing-plans`, `.../approve`, `.../archive` |
| Execution runs | `/projects/{id}/marketing-plan-execution-runs`, `.../start`, `.../cancel` |
| Specialist execute | `POST .../execution-runs/{run_id}/tasks/{task_index}/execute-specialist` |
| Specialist outputs | `/projects/{id}/marketing-specialist-outputs`, `.../approve`, `.../archive` |

---

## Safety boundaries (frozen)

| Allowed | Out of scope until AI.40+ |
|---------|---------------------------|
| Manual per-task `execute-specialist` | Auto-run full pipeline |
| `MarketingSpecialistOutput` artifacts | Copywriter → `ContentAsset` conversion |
| Mock/real LLM via safe adapter | Raw provider payload in DB |
| Desk research (no web) | Web research / MCP |
| Dependency validation only (AI.37) | LangGraph marketing execution |
| Run completion when all tasks done (AI.38) | Publish / export / media generation |

---

## Next branch (AI.40–AI.45)

**Content Production Layer** — see [phase_ai_40_45_content_production_layer_roadmap.md](phase_ai_40_45_content_production_layer_roadmap.md).

**AI.40** (opened): explicit approved Copywriter → `ContentAsset` draft. Do not change AI.27–39 conveyor behavior when extending content production.

---

## Regression command

```bash
uv run pytest \
  tests/test_phase_ai_27_marketing_orchestrator_skeleton.py \
  tests/test_phase_ai_28_marketing_plan_persistence.py \
  tests/test_phase_ai_29_marketing_plan_execution_skeleton.py \
  tests/test_phase_ai_30_marketing_specialist_output_skeleton.py \
  tests/test_phase_ai_31_strategist_specialist_execution.py \
  tests/test_phase_ai_32_researcher_specialist_execution.py \
  tests/test_phase_ai_33_content_planner_specialist_execution.py \
  tests/test_phase_ai_34_copywriter_specialist_execution.py \
  tests/test_phase_ai_35_critic_specialist_execution.py \
  tests/test_phase_ai_36_analyst_specialist_execution.py \
  tests/test_phase_ai_37_marketing_pipeline_validation.py \
  tests/test_phase_ai_38_marketing_run_completion.py \
  tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py -q
```

See also: [phase_ai_34_38_marketing_pipeline_roadmap.md](phase_ai_34_38_marketing_pipeline_roadmap.md) (implementation history).
