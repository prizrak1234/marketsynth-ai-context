## Phase AI.11.1 — Sub-agent execution readiness audit (freeze)

This audit freezes **real sequential sub-agent execution** for the Marketer orchestrator (Phase AI.11). The orchestrator creates a **child `AgentRun`** for copywriter work; persona routing (AI.10) is no longer prompt-only for that path.

**Not in this freeze:** researcher / strategist / analyst child runs, LangGraph, handoff, parallel execution, or multi-hop chains.

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.10 / AI.10.1** | Sub-agent registry, router, orchestrator persona overlay (prompt) |
| **AI.11** | `parent_agent_run_id`, `execute_subagent`, orchestrator → copywriter child run |
| **AI.11.1** | This document — execution freeze + natural-language copywriter router |

---

## AgentRun hierarchy

| Field | Purpose |
|-------|---------|
| `parent_agent_run_id` | FK to parent `agent_runs.id`; `NULL` for top-level runs |

**Rules (frozen):**

- Parent run: orchestrator `AgentType`, no `parent_agent_run_id`
- Child run: copywriter `AgentType`, `parent_agent_run_id` = parent id
- **One child per parent** (`_MAX_CHILDREN_PER_PARENT = 1`)
- **No nesting:** child runs cannot call `execute_subagent` (parent must be top-level)
- Owner / project / task scope inherited from parent agent resolution

Migration: `alembic/versions/20260602_0006_agent_run_parent_hierarchy_phase_ai_11.py`

---

## Execution path (frozen: copywriter only)

**Module:** `app/agents/marketer/execution.py` → `execute_subagent()`

| Step | Behavior |
|------|----------|
| 1 | Validate `subagent_type` ∈ `_SUPPORTED_SUBAGENTS` (`copywriter` only) |
| 2 | Reject if `parent_run.parent_agent_run_id` is set |
| 3 | Require parent agent `AgentType.ORCHESTRATOR` |
| 4 | Enforce ≤1 existing child for parent |
| 5 | Resolve project copywriter agent (`mapped_agent_type`) |
| 6 | Create child run with `parent_agent_run_id`, input `source: subagent_execution` |
| 7 | Execute child via **classic** `AgentRunCoordinator` (not LangGraph) |
| 8 | Return succeeded child run to chat layer |

**Chat:** `AgentChatService.send_message` when `agent.type == orchestrator` and router selects `copywriter`:

- Creates parent orchestrator run (audit / linkage)
- Delegates execution to child; does **not** execute parent LLM
- Response `agent_run_id` = parent; `subagent_execution` = `{ subagent, agent_run_id: child }`
- Assistant message `agent_run_id` = child

Analyst / strategist / researcher router hits still set `subagent_routing` for **prompt overlay only** — no child run.

---

## Router (natural copywriter intent)

**Module:** `app/agents/marketer/router.py`

Copywriter scoring uses:

- **Phrases:** `перепиши`, `переписать`, `улучши`, `улучшить`, `сделай текст`, `rewrite`, `improve`, …
- **Intent pair:** rewrite verb token + content noun token (`пост`, `текст`, `copy`) — non-adjacent OK

Frozen example: **«Перепиши этот пост»** → `copywriter` (verb + noun, not a single contiguous substring).

---

## Boundaries (explicit no-goals)

| Capability | Status |
|------------|--------|
| Child runs for analyst / strategist / researcher | **Forbidden** — router may detect; no `execute_subagent` |
| orchestrator → strategist chain | **Forbidden** |
| Child → child nesting | **Forbidden** |
| LangGraph / handoff child worker | **Forbidden** in marketer execution path |
| Parallel sub-agents | **Forbidden** |
| Approve / publish / schedule from sub-agent | **Forbidden** — copywriter persona + agent profile |
| New execution tools in registry | **Forbidden** |

Copywriter child uses normal **copywriter** `AgentType` tool profile (not expanded orchestrator tools).

---

## API / UI

| Surface | Field |
|---------|--------|
| `AgentChatSendResponse` | `subagent_execution: { subagent, agent_run_id }` optional |
| `AgentRun` contract | `parent_agent_run_id` optional |
| Web UI | «Handled by Copywriter» when `subagent_execution` present |

---

## Relationship to prior freezes

| Layer | Doc |
|-------|-----|
| Persona registry | `docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md` |
| Orchestrator scenarios | `docs/phase_ai_9_marketing_orchestrator_readiness_audit.md` |
| Revision / campaign context | `docs/phase_ai_7_revision_readiness_audit.md`, `docs/phase_ai_8_campaign_aware_revision_readiness_audit.md` |

---

## Future work (not AI.11.1)

- **AI.12** — researcher or strategist **execution** (separate freeze after this one proves orchestrator → child → result)
- Additional copywriter router phrases / disambiguation vs strategist «сделай текст» edge cases

---

## Freeze checklist

```bash
uv run pytest tests/test_subagent_execution.py
uv run pytest tests/test_phase_ai_11_subagent_execution_invariants.py
uv run pytest tests/test_marketer_subagent_registry.py
```
