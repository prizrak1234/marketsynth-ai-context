# Phase 5.0 — Marketing Strategist Agent MVP

Phase 5 turns the marketing domain into a **product agent**: the strategist reads briefs, funnels, and assets through the existing tool layer, runs gap analysis, and optionally creates a **draft** strategy asset via `content_asset.create_draft`.

No separate `StrategistService` or DB shortcuts — execution goes through the same envelope, permissions, and audit path as Phase 2–4.

## Strategist template

`AgentType.strategist` default config (from `app/agents/templates.py`):

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.3,
    "max_tokens": 1800
  },
  "tools": {
    "profile": "strategist"
  },
  "output": {
    "default_asset_type": "article",
    "default_asset_title": "Marketing Strategy Draft"
  }
}
```

Capabilities: `read_project_context`, `read_marketing_briefs`, `read_content_assets`, `read_marketing_funnels`, `analyze_funnel_gaps`, `create_strategy_draft`.

## Tools

| Mode | Tools |
|------|--------|
| Read-only (default) | All **12** real read-only tools (memory, project context, tasks, briefs, assets, funnels) |
| Write enabled | Above + `content_asset.create_draft` |

Write requires **both** env flags:

```env
AGENT_WRITE_TOOLS_ENABLED=true
AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED=true
```

The strategist never receives approve/publish/archive tools.

## Run payload convention

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "goal": "analyze funnel and create strategy draft",
  "prompt": "optional free-text instruction"
}
```

The prompt builder adds a **Strategist run context** block with `brief_id`, `funnel_id`, and `goal`. Tool executors still enforce project ownership — IDs in the payload are hints for the LLM, not trust boundaries.

## Expected workflow

1. Create a **strategist** agent on a project (`POST /agents` with `type: strategist`).
2. Create marketing **brief**, **funnel** (with steps), and any **content assets** via HTTP API.
3. Create an **agent run** with `brief_id` / `funnel_id` in `input_payload`.
4. Execute: `POST /agent-runs/{id}/execute-dry-run` (classic) or `POST /agent-runs/{id}/execute-graph-dry-run` (LangGraph).
5. Review tool execution logs: `GET /agent-runs/{id}/tool-executions`.
6. If write tools are enabled, review the new **draft** content asset; **approve manually** via `POST .../content-assets/{id}/approve`.

## Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `input_payload.force_tool_call` | Single forced tool (e.g. `marketing_funnel.gap_analysis`) |
| `input_payload.mock_tool_call` | Explicit tool call list (existing) |
| `agent.config.mock_strategy_flow: true` | Mock LLM round 1: `marketing_funnel.gap_analysis` + `content_asset.create_draft` (if write enabled); round 2: strategist final text |

## Draft body structure

When creating a strategy draft, the system prompt instructs:

1. Summary  
2. Funnel gaps  
3. Recommended assets  
4. Next actions  
5. Risks  

## Out of scope (5.0)

- Auto-approve or publish
- Custom strategist-only executors bypassing tools
- Changes to Phase 3 graph topology, webhooks, or outbox

## Phase 5.1 — Strategy draft quality contract

Deterministic quality scoring for strategy drafts — **not** auto-approve. Humans still approve via the existing workflow.

### Contract (`app/marketing/strategy_contracts.py`)

`MarketingStrategyDraftQuality` fields:

- Section flags: `has_summary`, `has_funnel_gaps`, `has_recommended_assets`, `has_next_actions`, `has_risks`
- `min_body_length_met` (default minimum **500** characters)
- `score` = passed checks / 6 (five sections + min length)
- `missing_sections` — human-readable labels

`evaluate_strategy_draft_body(body)` runs without LLM.

### When quality metadata is stored

On `content_asset.create_draft`, when:

- `type == article`, and
- `metadata.purpose == "marketing_strategy"` **or** title contains `"strategy"` (case-insensitive)

then `metadata.quality` is populated. **Low scores do not block** draft creation.

Mock `mock_strategy_flow` drafts use `purpose: marketing_strategy`, `source: strategist_agent`, and a body with all five sections (500+ chars).

### Quality endpoint (read-only)

```
GET /projects/{project_id}/content-assets/{asset_id}/quality
```

- Project ownership required
- Returns stored `metadata.quality` when present
- Otherwise evaluates the current body on the fly (does **not** persist)

### Smoke workflow

```bash
# Server must have write tools enabled for draft creation
export BOTFAZER_API_KEY=bfz_...
export AGENT_WRITE_TOOLS_ENABLED=true
export AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED=true
uv run uvicorn app.main:app --reload

uv run python scripts/smoke_marketing_strategist.py
```

Script flow: project → brief → funnel → strategist (`mock_strategy_flow`) → `POST .../execute` → prints `draft_asset_id` and `quality_score` if a draft was created. No approval step.

### Human review path

1. Run strategist (above)
2. `GET .../content-assets/{id}/quality` — heuristic score for triage
3. Read draft body
4. `POST .../content-assets/{id}/approve` — manual only

## Phase 5.2 — Copywriter Agent MVP

Production copy agent: reads briefs, source assets, and funnel step context; creates **draft** copy only via `content_asset.create_draft` (same write gate as strategist).

### Copywriter template

`AgentType.copywriter` default config:

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.5,
    "max_tokens": 1600
  },
  "tools": {
    "profile": "copywriter"
  },
  "output": {
    "default_asset_type": "email",
    "default_asset_title": "Copy Draft"
  }
}
```

Capabilities: `read_marketing_briefs`, `read_content_assets`, `read_funnel_context`, `create_copy_draft`.

### Tools (copywriter profile)

| Mode | Tools |
|------|--------|
| Read-only | `project_context.get`, `memory.search`, `task.get`, brief/asset read tools, `marketing_funnel.get`, `marketing_funnel.step_assets` |
| Write enabled | Above + `content_asset.create_draft` |

**Not** exposed: `marketing_funnel.list`, `marketing_funnel.gap_analysis`, approve/publish/archive.

Same write env flags as strategist (both must be `true`).

### Run payload convention

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "step_id": "<uuid>",
  "source_asset_id": "<uuid>",
  "asset_type": "email",
  "title": "Optional title override",
  "goal": "write launch email",
  "prompt": "optional free-text instruction"
}
```

Supported `asset_type` values for copy drafts: `email`, `ad_copy`, `telegram_post`, `landing_page`.

The prompt builder adds a **Copywriter run context** block with the IDs above. Ownership is still enforced in tool executors.

### Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `agent.config.mock_copywriter_flow: true` | Round 1: optional `marketing_brief.get` (if `brief_id`), optional `marketing_funnel.step_assets` (if `step_id`), then `content_asset.create_draft` when write enabled; round 2: copywriter final text |
| `input_payload.force_tool_call` | Single forced tool (supports brief get, asset get, step assets, create_draft) |

### Draft body structure

- **email**: Subject line, Preview text, Body, CTA  
- **ad_copy**: Hook, Offer, Proof, CTA  
- **telegram_post**: Hook, Value, CTA  
- **landing_page**: headline, value blocks, CTA (prompt-level; quality heuristic uses email-style fallback)

### Copy draft quality (`app/marketing/copy_quality.py`)

When `metadata.purpose == "copy_draft"`, `content_asset.create_draft` stores `metadata.quality` from `evaluate_copy_draft_body(asset_type, body)`. Low scores **do not block** creation.

Mock copywriter drafts use `purpose: copy_draft`, `source: copywriter_agent`, and a deterministic structured body.

## Phase 5.3 — Content Planner Agent MVP

Production planning agent: reads briefs, funnels, assets, runs **gap analysis**, and drafts a **content plan** article (`metadata.purpose: content_plan`). Does **not** link assets to funnel steps or mutate funnel structure.

### Content planner template

`AgentType.content_planner` default config:

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.4,
    "max_tokens": 1800
  },
  "tools": {
    "profile": "content_planner"
  },
  "output": {
    "default_asset_type": "article",
    "default_asset_title": "Content Plan Draft"
  }
}
```

Capabilities: `read_marketing_briefs`, `read_content_assets`, `read_marketing_funnels`, `analyze_funnel_gaps`, `create_content_plan_draft`.

### Tools (content planner profile)

| Mode | Tools |
|------|--------|
| Read-only | `project_context.get`, `memory.search`, `task.get`, brief/asset reads, all four funnel read tools including **`marketing_funnel.gap_analysis`** |
| Write enabled | Above + `content_asset.create_draft` |

Same write env flags as strategist/copywriter. No approve/publish/link tools.

### Run payload convention

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "goal": "plan content for launch funnel",
  "prompt": "optional free-text instruction"
}
```

### Agent roles compared

| Agent | Primary output | Gap analysis | Typical draft |
|-------|----------------|--------------|---------------|
| **Strategist** | Strategic recommendations | Yes | `article` — strategy sections (summary, gaps, assets, actions, risks) |
| **Copywriter** | Channel copy | No (step assets only) | `email` / `ad_copy` / `telegram_post` / `landing_page` |
| **Content planner** | Production plan | Yes | `article` — plan sections (summary, gaps, assets per step, priority, notes, risks) |

### Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `agent.config.mock_content_planner_flow: true` | Round 1: `marketing_funnel.gap_analysis` (if `funnel_id`), then `content_asset.create_draft` when write enabled; round 2: planner final text |

### Content plan quality (`app/marketing/content_plan_quality.py`)

When `metadata.purpose == "content_plan"`, `content_asset.create_draft` stores `metadata.quality` from `evaluate_content_plan_body(body)` (six sections + min length 500). Low scores **do not block** creation.

## Phase 5.4 — Critic Agent MVP

Quality gate before human approval: reads the **source** asset, brief, and funnel context; produces a separate **review draft** (`metadata.purpose: content_review`). Never edits, approves, or publishes the source asset.

### Critic template

`AgentType.critic` default config:

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.2,
    "max_tokens": 1600
  },
  "tools": {
    "profile": "critic"
  },
  "output": {
    "default_asset_type": "article",
    "default_asset_title": "Content Review Draft"
  }
}
```

Capabilities: `read_marketing_briefs`, `read_content_assets`, `read_marketing_funnels`, `review_content_quality`, `create_review_draft`.

### Tools (critic profile)

| Mode | Tools |
|------|--------|
| Read-only | Same read set as content planner (brief/asset/funnel + `gap_analysis`) |
| Write enabled | Above + `content_asset.create_draft` (new review asset only) |

**Not** exposed: approve, archive, PATCH/update source, revision, rollback, funnel link tools.

### Run payload convention

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "source_asset_id": "<uuid>",
  "goal": "review this copy before approval",
  "prompt": "optional free-text instruction"
}
```

### Review workflow

1. Human or copywriter creates a **draft** source asset.
2. Critic run loads `source_asset_id` → writes a **Content Review Draft** (separate asset).
3. Human reads review + source; **`POST .../approve`** on the source remains manual only.

### Agent roles compared (updated)

| Agent | Role | Mutates source? |
|-------|------|-----------------|
| **Strategist** | Strategy + gaps | No (new strategy draft) |
| **Copywriter** | Channel copy | No (new copy draft) |
| **Content planner** | Production plan | No (new plan draft) |
| **Critic** | Pre-approval review | **No** (new review draft only) |

### Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `agent.config.mock_critic_flow: true` | Round 1: `content_asset.get` (if `source_asset_id`), `marketing_brief.get` (if `brief_id`), then `content_asset.create_draft` when write enabled; round 2: critic final text |

### Review quality (`app/marketing/review_quality.py`)

When `metadata.purpose == "content_review"`, `content_asset.create_draft` stores `metadata.quality` from `evaluate_review_body(body)` (six sections + min length 400). Low scores **do not block** creation.

## Phase 5.5 — Researcher Agent MVP

Internal research agent: synthesizes **project-only** data (brief, assets, funnel/gap analysis, memory) into a research memo. **No web search** in this phase.

### Researcher template

`AgentType.researcher` default config:

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.25,
    "max_tokens": 1800
  },
  "tools": {
    "profile": "researcher"
  },
  "output": {
    "default_asset_type": "article",
    "default_asset_title": "Research Draft"
  }
}
```

Capabilities: `read_project_context`, `read_memory`, `read_marketing_briefs`, `read_content_assets`, `read_marketing_funnels`, `create_research_draft`.

### Tools (researcher profile)

| Mode | Tools |
|------|--------|
| Read-only | All **12** real read-only tools (same as strategist: memory, project context, tasks, briefs, assets, funnels including `gap_analysis`) |
| Write enabled | Above + `content_asset.create_draft` |

No approve/publish/update/revision/link tools. External web search is **not** available.

### Run payload convention

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "research_topic": "audience objections",
  "goal": "prepare internal research memo",
  "prompt": "optional free-text instruction"
}
```

### Agent roles compared (updated)

| Agent | Output | External data |
|-------|--------|----------------|
| **Researcher** | Internal research memo | Project tools only; assumptions + “requires external validation” |
| **Strategist** | Strategy draft | Project tools |
| **Copywriter** | Channel copy drafts | Project tools |
| **Content planner** | Content plan | Project tools |
| **Critic** | Review of source asset | Project tools |

### Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `agent.config.mock_researcher_flow: true` | Round 1: optional `marketing_brief.get`, `marketing_funnel.gap_analysis`, `memory.search` (if `research_topic`), then `content_asset.create_draft` when write enabled; round 2: researcher final text |

### Research quality (`app/marketing/research_quality.py`)

When `metadata.purpose == "research_draft"`, `content_asset.create_draft` stores `metadata.quality` from `evaluate_research_body(body)` (seven sections + min length 500). Low scores **do not block** creation.

## Phase 5.6 — Orchestrator Agent MVP

Supervisor agent: reads project/brief/funnel/asset context, **routes** work to specialists, and **delegates** via the existing LangGraph handoff path (`handoff_gate` → `handoff_record`). No parallel orchestration service.

### Orchestrator template

`AgentType.orchestrator` default config:

```json
{
  "llm": {
    "provider": "mock",
    "model": "mock-model",
    "temperature": 0.2,
    "max_tokens": 1800
  },
  "tools": {
    "profile": "orchestrator"
  },
  "orchestration": {
    "handoff_enabled": true,
    "max_child_runs": 3,
    "default_inline_child_execution": false
  }
}
```

Capabilities: `read_project_context`, `read_marketing_briefs`, `read_content_assets`, `read_marketing_funnels`, `analyze_funnel_gaps`, `delegate_to_specialists`, `coordinate_marketing_workflow`.

### Specialist routing (goal / scope)

| Specialist | When to delegate |
|------------|------------------|
| **researcher** | `research_topic`, unknowns, internal research |
| **strategist** | strategy, positioning, funnel gaps |
| **content_planner** | content plan, editorial calendar, assets per step |
| **copywriter** | concrete copy (`step_id`, `asset_type`, write goals) |
| **critic** | review of `source_asset_id` |

Routing helpers live in `app/marketing/orchestration.py` (`resolve_specialist_agent_type`). Production runs should pass explicit handoff controls on the agent run `input_payload` (see Phase 3 handoff doc).

### Parent run payload

```json
{
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "goal": "coordinate launch content",
  "research_topic": "optional for researcher routing",
  "handoff_to_agent_id": "<uuid>",
  "handoff_target_agent_type": "content_planner",
  "handoff_reason": "optional note",
  "handoff_enqueue_child": true,
  "handoff_execute_child": false
}
```

`handoff_*` keys are stripped before the child prompt is built. Prefer **`handoff_target_agent_type`** when multiple agents of the same type exist — the orchestrator resolves the first non-archived agent of that type in the project.

### Child payload conventions (per specialist)

Fields copied into the child `input_payload` (plus prompt + handoff metadata):

| Specialist | Fields |
|------------|--------|
| **researcher** | `brief_id`, `funnel_id`, `research_topic`, `goal` |
| **strategist** | `brief_id`, `funnel_id`, `goal` |
| **content_planner** | `brief_id`, `funnel_id`, `goal` |
| **copywriter** | `brief_id`, `funnel_id`, `step_id`, `source_asset_id`, `asset_type`, `goal` |
| **critic** | `source_asset_id`, `brief_id`, `funnel_id`, `goal` |

Built by `build_specialist_child_payload()` and merged in `build_child_run_input_payload()`.

### Inline vs queued child execution

| Setting | Effect |
|---------|--------|
| `orchestration.default_inline_child_execution: false` (default) | Child run is **queued** (`handoff_execute_child` defaults false); worker drains Redis queue |
| `handoff_execute_child: true` + `GRAPH_HANDOFF_EXECUTE_CHILD=true` | Child runs inline in the parent graph transaction (debug / tests) |

`orchestration.max_child_runs` counts existing handoff children (`metadata.parent_agent_run_id`) and rejects further delegation with `handoff_max_children_exceeded`.

### Orchestrator rules

- Read-only tools + optional `content_asset.create_draft` when write flags are on — **do not** use create_draft for work that belongs to a specialist; delegate instead.
- No approve/publish/archive.
- **Recommended production:** LangGraph (`execute-graph-dry-run` / project `execution_engine: langgraph`). Classic `execute-dry-run` **ignores** handoff controls.

### Mock / test flows

| Trigger | Behavior |
|---------|----------|
| `agent.config.mock_orchestrator_flow: true` | Auto-routes from `goal` at `handoff_gate` when no `handoff_to_agent_id`; mock LLM (non-delegated runs): `project_context.get` + optional `marketing_funnel.gap_analysis` |
| `handoff_to_agent_id` / `handoff_target_agent_type` | Explicit delegation (graph handoff; parent succeeds with `output_payload.handoff`) |

## Phase 5.7 — End-to-end marketing workflow smoke

Regression shield for the **mini marketing agency** path:

`orchestrator` (delegate) → `content_planner` child (content plan draft) → `critic` (review draft) → **human** approve.

Helpers: `app/marketing/workflow_smoke.py` (demo project/brief/funnel/agents + payload builders).  
E2E tests: `tests/test_marketing_workflow_e2e.py`.  
Local smoke (optional API key): `scripts/smoke_marketing_workflow.py`.

### Workflow steps (API)

1. Create **project**, **brief**, **funnel** (+ at least one funnel step).
2. Create agents: `orchestrator`, `content_planner`, `critic` (enable mock flows for dry-run).
3. Create orchestrator **agent run** with delegation payload (see below).
4. `POST /agent-runs/{id}/execute-graph-dry-run` (or production `/execute` with LangGraph).
5. `POST /agent-runs/process-handoff-children` — drain queued planner child.
6. List `GET /projects/{id}/content-assets` — find plan draft (`agent_run_id` = child run).
7. Create **critic** run with `source_asset_id` = plan asset id; execute graph/classic.
8. **Human approve:** `POST /projects/{id}/content-assets/{asset_id}/approve` (not automatic).

### Orchestrator payload example

```json
{
  "goal": "build content plan for launch funnel",
  "brief_id": "<uuid>",
  "funnel_id": "<uuid>",
  "handoff_target_agent_type": "content_planner"
}
```

### Workflow summary (UI-friendly)

`GET /agent-runs/{parent_run_id}/workflow-summary` returns parent status, `handoff` block, child runs with `created_assets`, and `related_assets` (linked by `agent_run_id` / `metadata.source_asset_id`).

### Smoke script

```bash
export BOTFAZER_API_KEY=bfz_...
export BOTFAZER_BASE_URL=http://127.0.0.1:8000
uv run python scripts/smoke_marketing_workflow.py
# optional human approve step:
uv run python scripts/smoke_marketing_workflow.py --approve-draft
```

Without `BOTFAZER_API_KEY` / `SMOKE_API_KEY` the script exits 0 with `skip:`.

Write tools must be enabled in `.env` for draft creation in tests/smoke.

## Phase 5.8 — Product readiness freeze

Phase 5 is **frozen** as the marketing agency MVP. Full audit: [phase_5_product_readiness_audit.md](phase_5_product_readiness_audit.md).

### Freeze checklist

- Role boundaries locked (orchestrator delegates; specialists draft; humans approve).
- Tool matrix: `app/agents/tool_matrix.py` + `GET /agents/tool-matrix`.
- Invariant tests: `tests/test_phase_5_agent_invariants.py`.
- E2E regression: `tests/test_marketing_workflow_e2e.py`.
- Smoke: `scripts/smoke_phase_5_agents.py`.

### Tool matrix (read / write)

| Agent | Write (`create_draft` when flags on) |
|-------|--------------------------------------|
| strategist, researcher, content_planner, copywriter, critic, orchestrator | Yes |
| analyst | No |

See API `GET /agents/tool-matrix` for the full per-type `read_tools` / `write_tools` lists.

### What agents cannot do

- Approve, publish, archive, or revise existing assets via tools.
- Pass `owner_id`, `project_id`, or `task_id` in tool arguments (prompt-enforced).
- Orchestrator: must not perform specialist drafting when delegation is required.

### Agent draft vs human approval

| Step | Who |
|------|-----|
| Draft asset | Specialist agent via `content_asset.create_draft` |
| Review draft | Critic agent (new asset, source unchanged) |
| Approve | Human / API client via `POST .../approve` only |

## Next

Phase 5.9+ can add real LLM providers, external research, and publishing integrations — only with a new phase sign-off. Do not add approve/publish agent tools without security review.
