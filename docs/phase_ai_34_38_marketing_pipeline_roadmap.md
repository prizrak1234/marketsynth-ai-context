# Phase AI.34–AI.39 — Marketing production conveyor (roadmap)

**Status:** **Done** (AI.34–AI.38 implemented; **AI.39** production freeze).  
**Prerequisite:** AI.27–AI.33 complete (plan → approve → execution run → specialist outputs, manual per task).

**Freeze:** [phase_ai_39_marketing_pipeline_readiness_audit.md](phase_ai_39_marketing_pipeline_readiness_audit.md) — regression gate before **AI.40+**.

## Product framing

BotFazer is building a **marketing production conveyor**, not a multi-agent swarm:

- One specialist → one controlled path → one `MarketingSpecialistOutput` artifact.
- No parallel execution, no LangGraph marketing orchestration, no auto-`ContentAsset` in this wave.
- Manual `POST .../execute-specialist` per task until AI.37; AI.37 adds **dependency validation only** (still no auto-run).

After AI.38 the first closed loop exists:

```
Plan → Approve → Execution Run → Strategist → Researcher → Content Planner
  → Copywriter → Critic → Analyst → Run succeeded (result_summary)
```

**AI.40+** is the separate branch: Copywriter output → `ContentAsset` via explicit approval — not part of AI.34–38.

---

## Current foundation (AI.27–AI.39)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| AI.27 | Marketing orchestrator planning (no specialist execution) | Done |
| AI.28 | `MarketingPlan` persistence + approve gate | Done |
| AI.29 | `MarketingPlanExecutionRun` skeleton | Done |
| AI.30 | `MarketingSpecialistOutput` + versions | Done |
| AI.31 | Strategist dry-run → `output_type: strategy` | Done |
| AI.32 | Researcher desk-research → `output_type: research` (requires Strategist) | Done |
| AI.33 | Content Planner structure → `output_type: content_plan` (requires Strategist + Researcher) | Done |
| AI.34 | Copywriter → `content_copy` | Done |
| AI.35 | Critic → `critique` | Done |
| AI.36 | Analyst → `analysis` | Done |
| AI.37 | `MarketingPipelineExecutionService` | Done |
| AI.38 | Run `succeeded` + `specialist_pipeline` summary | Done |
| AI.39 | Production freeze (docs + invariants tests) | Done |

**Shared invariants (all specialist phases):**

- `run.status == running`, approved plan version match, no duplicate active output per task.
- LLM via existing adapter; mock deterministic; no tools, no child `AgentRun`, no raw provider payload in `structured_data`.
- Endpoint: `POST /projects/{id}/marketing-plan-execution-runs/{run_id}/tasks/{task_index}/execute-specialist`.

---

## Wave 1 — Complete MVP marketing department (AI.34–AI.36) ✅

Implemented in order. Each phase = one PR, contracts first, tests per endpoint behavior.

### AI.34 — Copywriter specialist execution

**Goal:** Turn Content Planner structure into **real copy text** (still only `MarketingSpecialistOutput`, not `ContentAsset`).

**Prerequisites (409 if missing):**

- Strategist output (draft/approved or task `specialist_completed`)
- Researcher output
- Content Planner output

**Prior context:** Safe `structured_data` + short excerpts from Strategist, Researcher, Content Planner only.

**Output contract:**

| Field | Value |
|-------|--------|
| `title` | e.g. `"Content copy"` |
| `output_type` | `content_copy` |
| `content` | Readable copy package summary (not asset creation) |

**`structured_data` (required keys):**

```json
{
  "content_items": [
    {
      "headline": "",
      "hook": "",
      "body": "",
      "cta": "",
      "funnel_stage": "",
      "content_pillar": "",
      "channel": ""
    }
  ],
  "llm_provider": "...",
  "model": "...",
  "mock": true
}
```

**Explicit non-goals:** No `ContentAsset` rows, no publish/schedule, no Media/Canva/Figma.

**Executor:** `app/agents/marketer/specialists/copywriter.py` → `execute_copywriter_specialist`.

**Guard messages:**

- Missing Strategist → `Copywriter requires completed Strategist output`
- Missing Researcher → `Copywriter requires completed Researcher output`
- Missing Content Planner → `Copywriter requires completed Content Planner output`

---

### AI.35 — Critic specialist execution

**Goal:** Internal quality review across the pipeline (recommendation only, no automated approve/revise actions).

**Prerequisites:** Strategist, Researcher, Content Planner, Copywriter outputs (same active/completed rules).

**Output contract:**

| Field | Value |
|-------|--------|
| `output_type` | `critique` |

**`structured_data` (required keys):**

- `strengths` (list)
- `weaknesses` (list)
- `inconsistencies` (list)
- `missing_information` (list)
- `improvement_actions` (list)
- `approval_recommendation`: one of `approve` | `revise` | `reject` (recommendation only)

**Non-goals:** Does not change run status, does not archive outputs, does not trigger re-execution.

**Executor:** `app/agents/marketer/specialists/critic.py`.

---

### AI.36 — Analyst specialist execution

**Goal:** Feasibility / execution realism check using **all** prior specialist outputs in the run.

**Prerequisites:** All of Strategist, Researcher, Content Planner, Copywriter, Critic (per plan task snapshots — only roles present in the approved plan).

**Output contract:**

| Field | Value |
|-------|--------|
| `output_type` | `analysis` |

**`structured_data` (required keys):**

- `risks`
- `resource_requirements`
- `channel_fit`
- `funnel_gaps`
- `execution_complexity`
- `kpi_recommendations`

**Executor:** `app/agents/marketer/specialists/analyst.py`.

**Note:** Analyst is last in the **MVP six** (`MarketingSpecialistType` already includes `analyst`, `critic`, `copywriter`). Do not add new specialist enum values in AI.34–36.

---

## Wave 2 — Pipeline glue (AI.37–AI.38) ✅

### AI.37 — Marketing pipeline orchestration (validation only)

**Goal:** Centralize **dependency rules** so UI and API share one truth — **no automatic specialist execution**.

**Add:** `MarketingPipelineExecutionService` (or extend `SpecialistExecutionService` with a dedicated module) exposing:

- `validate_task_execution(run, task_index) -> None | raises InvalidStateError`
- `required_prior_specialists(specialist) -> list[MarketingSpecialistType]`
- `pipeline_order() -> list[MarketingSpecialistType]` for UI hints

**Canonical order (MVP six):**

```
strategist → researcher → content_planner → copywriter → critic → analyst
```

**Dependency matrix (minimum):**

| Task | Requires completed/active output or `specialist_completed` for |
|------|------------------------------------------------------------------|
| strategist | — |
| researcher | strategist |
| content_planner | strategist, researcher |
| copywriter | strategist, researcher, content_planner |
| critic | strategist, researcher, content_planner, copywriter |
| analyst | all above roles that exist in plan snapshots |

Refactor AI.31–36 guards to call shared validation (avoid drift).

**Non-goals:** No batch execute, no queue worker, no LangGraph.

---

### AI.38 — Run completion rules

**Goal:** When **every** task snapshot in the run is `specialist_completed`, transition run to terminal success with aggregate summary.

**Trigger:** Explicit endpoint only (recommended), e.g.  
`POST .../marketing-plan-execution-runs/{run_id}/complete`  
— **not** auto-fired on last specialist execute (keeps AI.37 “no automation” spirit for execution; completion is a deliberate human checkpoint).

Alternative (if product prefers): auto-check at end of each `execute-specialist` when all tasks completed — document choice in AI.38 implementation.

**On success:**

- `MarketingPlanExecutionRun.status` → `succeeded`
- `finished_at` set
- `result_summary` example:

```json
{
  "mode": "specialist_pipeline",
  "completed_specialists": [
    "strategist",
    "researcher",
    "content_planner",
    "copywriter",
    "critic",
    "analyst"
  ],
  "output_count": 6,
  "message": "All plan tasks completed via specialist pipeline."
}
```

Build `completed_specialists` from task snapshots + linked `MarketingSpecialistOutput` types (safe metadata only).

**Non-goals:** Does not approve/archive outputs, does not create assets.

---

## AI.39 — Production freeze ✅

**Goal:** Cement AI.27–AI.38 before any `ContentAsset` work.

- Audit: [phase_ai_39_marketing_pipeline_readiness_audit.md](phase_ai_39_marketing_pipeline_readiness_audit.md)
- Tests: `tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py`
- No new product features, specialists, LLM behavior, tools, or assets.

---

## After AI.39 — Next major branch

| Phase | Topic |
|-------|--------|
| **AI.40+** | **New branch:** approved Copywriter `content_copy` → `ContentAsset` draft conversion (explicit user action). Not part of AI.27–39 pipeline. |

Scaling to **12 marketing specialists** later = new executors + dependency rows, not a rewrite of the conveyor.

---

## Explicitly out of scope (AI.34–AI.38)

Do **not** implement in this package:

- Media generation, Canva, Figma, HeyGen
- MCP / web research / scraping
- LangGraph marketing orchestration
- Parallel or swarm execution
- Auto `ContentAsset` on copywriter or critic approve
- Full-plan one-click “run all specialists”
- Chat layer changes (frozen per AI.26)
- Programmer / Media domains

---

## Implementation checklist (per phase)

1. Extend `contracts.py` (`MarketingSpecialistExecutionOutput` shapes documented; no new DB tables unless needed).
2. Add `app/agents/marketer/specialists/<role>.py`.
3. Register in `executor.py`; extend `SpecialistExecutionService` guards + `_PRIOR_OUTPUT_SPECIALISTS`.
4. Reuse `execute-specialist` endpoint (no new routes except AI.38 complete if chosen).
5. UI: enable button when pipeline validation passes; show prerequisite messages from AI.37.
6. Tests: `tests/test_phase_ai_XX_<role>_specialist_execution.py` + regression AI.31–33 (and prior phases).
7. README section + this doc updated with **Done** status.

---

## Regression command (AI.27–AI.39 freeze)

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
