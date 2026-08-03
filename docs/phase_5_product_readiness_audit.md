# Phase 5 — Marketing agents product readiness audit (freeze)

**Status:** MVP frozen at Phase 5.8  
**Scope:** Marketing mini-agency — orchestrator supervises specialists; humans approve assets.

```
orchestrator → specialist (researcher | strategist | planner | copywriter | critic)
            → content_asset.create_draft (draft only)
            → critic review draft (optional)
            → human approve (HTTP API only)
```

**Out of scope for Phase 5:** auto-publish, external web search, social integrations, UI product shell.

---

## Agent inventory

| Agent | Role | Draft output | Handoff |
|-------|------|--------------|---------|
| **orchestrator** | Supervisor — read context, route, delegate | Optional (discouraged for specialist tasks) | Yes (LangGraph) |
| **strategist** | Strategy + funnel gaps | Strategy article draft | No |
| **researcher** | Internal research memo | Research article draft | No |
| **content_planner** | Content production plan | Content plan article draft | No |
| **copywriter** | Channel copy | email / ad / post / landing drafts | No |
| **critic** | Pre-approval review | Review article draft (new asset) | No |
| **analyst** | Metrics read-only | None | No |

Templates: `app/agents/templates.py` (frozen — do not change without a new phase).

---

## Role boundaries

### What marketing agents MAY do

- Read project context, briefs, funnels, assets, memory (per tool profile).
- Run `marketing_funnel.gap_analysis` when profile allows.
- Create **new** assets in **`draft`** status via `content_asset.create_draft` when write flags and agent type allow.
- Orchestrator: delegate via `handoff_*` controls / `handoff_target_agent_type` (LangGraph only).

### What agents CANNOT do (enforced)

| Capability | Enforcement |
|------------|-------------|
| Approve assets | No tool; `POST .../content-assets/{id}/approve` only |
| Publish / archive assets | No agent tools |
| Update / revise source assets | No agent tools |
| Link assets to funnel steps | Prompt + no link tools |
| Pass `owner_id` / `project_id` / `task_id` in tool args | Prompt + `CREATE_DRAFT_FORBIDDEN_ARGUMENT_KEYS` |
| Nested handoff beyond depth | `GRAPH_HANDOFF_MAX_DEPTH` |
| Analyst marketing drafts | Not in `CREATE_DRAFT_ALLOWED_AGENT_TYPES` |

Orchestrator must **not** replace specialists: system prompt requires delegation; mock orchestrator flow does not call `create_draft`.

---

## Tool access matrix

Source of truth (docs/tests): `app/agents/tool_matrix.py`  
Debug API: `GET /agents/tool-matrix` (auth required).

### Read tools (write flags OFF)

| Agent | Read tools (count) | Notes |
|-------|-------------------|--------|
| strategist | 13 | Full marketing read set + `search_brief` stub |
| researcher | 13 | Same as strategist |
| content_planner | 12 | No `task.list_recent` |
| critic | 12 | Same as planner |
| copywriter | 10 | Narrow funnel read; no `task.list_recent` |
| orchestrator | 13 | Full read set |
| analyst | 11 | No `task.get`; no `content_asset.get` |

### Write tools (when `AGENT_WRITE_TOOLS_ENABLED` + `AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED`)

| Agent | `content_asset.create_draft` |
|-------|------------------------------|
| strategist | Yes |
| researcher | Yes |
| content_planner | Yes |
| copywriter | Yes |
| critic | Yes |
| orchestrator | Yes (policy: delegate instead) |
| analyst | **No** |

---

## Write safety gates

1. **Global flags** (`app/core/config.py`): `agent_write_tools_enabled`, `agent_write_tool_content_asset_create_draft_enabled`.
2. **Agent type allowlist** (`app/tools/write_tool_settings.py`): `CREATE_DRAFT_ALLOWED_AGENT_TYPES`.
3. **Profile exposure** (`app/tools/agent_tool_profiles.py`): write tool appended only when flags + type allow.
4. **Permission layer** (`app/tools/permissions.py`): `WRITE_TOOL_NAMES` / execution mode checks.
5. **Executor** (`app/tools/executors/content_asset_create_draft.py`): draft status only; sanitization; body max length.

Agents never receive legacy write stubs (`memory.write`, `task.create`, `agent.update`) in the marketing matrix.

---

## Draft-only policy

- `content_asset.create_draft` always creates `ContentAssetStatus.DRAFT`.
- Quality metadata is attached (`metadata.purpose`, `metadata.quality`) but **low scores do not block** creation.
- Purposes: `marketing_strategy`, `content_plan`, `copy_draft`, `content_review`, `research_draft` (heuristics in `app/marketing/*_quality.py`).

---

## Human approval policy

- **Only** humans (or authenticated API clients) approve via `POST /projects/{project_id}/content-assets/{asset_id}/approve`.
- Sets `approved_version_number` and emits `content_asset.approved` outbox event.
- Agents receive advisory “approval recommendation” text in critic drafts only — not executable approval.

---

## Orchestrator routing

- Routing helpers: `app/marketing/orchestration.py` (`resolve_specialist_agent_type`, child payload conventions).
- Handoff: existing Phase 3 graph (`handoff_gate` → `handoff_record`) — no parallel orchestration service.
- Config: `orchestration.handoff_enabled`, `max_child_runs`, `default_inline_child_execution`.
- Production: LangGraph execution recommended; classic executor ignores handoff controls.

---

## E2E workflow

Frozen regression:

- `tests/test_marketing_workflow_e2e.py` — full agency path + workflow summary.
- `tests/test_phase_5_agent_invariants.py` — role/permission freeze (Phase 5.8).
- `app/marketing/workflow_smoke.py` — demo workspace seeding.
- `scripts/smoke_marketing_workflow.py` — optional live API smoke.
- `scripts/smoke_phase_5_agents.py` — matrix + all specialist mocks + orchestrator summary.

---

## Quality heuristics

| Module | Purpose | Blocking? |
|--------|---------|-----------|
| `strategy_contracts.py` | Strategy draft sections | No |
| `content_plan_quality.py` | Content plan sections | No |
| `copy_quality.py` | Copy structure by asset type | No |
| `review_quality.py` | Review sections (min length 400) | No |
| `research_quality.py` | Research sections (min length 500) | No |

Scores are for UI/analytics and mock enrichment — not publish gates.

---

## Known limitations

- Mock LLM only in default templates; production LLM providers need separate hardening phase.
- No external web search for researcher.
- Single-child handoff per orchestrator run in typical MVP (configurable `max_child_runs`).
- `search_brief` is a no-op stub in profiles.
- Workflow summary scans project assets (limit 500) — not a full audit trail UI.
- Analyst agent is placeholder (read-only, no marketing drafts).

---

## Production checklist

- [ ] `AGENT_WRITE_TOOLS_ENABLED=true` only when intentional
- [ ] `AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED=true` for draft creation
- [ ] LangGraph: `AGENT_EXECUTION_LANGGRAPH_ENABLED=true` for orchestrator/handoff
- [ ] `GRAPH_HANDOFF_WORKER_ENABLED=true` + Redis for child queue
- [ ] Handoff depth / max children aligned with product policy
- [ ] Human approval trained in ops runbooks (no agent auto-approve)
- [ ] Run `uv run pytest tests/test_phase_5_agent_invariants.py`
- [ ] Run `uv run pytest tests/test_marketing_workflow_e2e.py`
- [ ] Optional: `uv run python scripts/smoke_phase_5_agents.py`

---

## Phase 5 freeze checklist

- [x] Six marketing roles + orchestrator defined in templates and prompts
- [x] Tool matrix documented and exposed via API
- [x] Write gates and analyst exclusion tested
- [x] No approve/publish agent tools
- [x] E2E workflow test (delegate → draft → review → approve)
- [x] Phase 3 execution/handoff/outbox unchanged in this freeze
- [x] Phase 4 domain schema unchanged in this freeze

---

## Next roadmap (post-freeze)

| Phase | Topic |
|-------|--------|
| 5.9+ | Real LLM providers with guardrails |
| 6.x | External research / citations |
| 6.x | Multi-child orchestration loops |
| 6.x | Publishing integrations (explicit product decision) |
| UI | Workflow dashboard consuming `workflow-summary` + tool-matrix |

Do **not** add approve/publish tools to agents without a formal security review and new phase sign-off.
