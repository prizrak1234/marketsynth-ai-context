## Phase AI.12.1 — Researcher execution readiness audit (freeze)

This audit **freezes** the execution layer after adding **researcher** as the second real child agent (Phase AI.12). Architecture **3.2** unchanged: sequential `AgentRun` hierarchy, classic executor only.

**Not in this freeze:** strategist / analyst child runs, LangGraph, handoff, parallel execution, multi-hop chains, or expanding `_SUPPORTED_SUBAGENTS` beyond copywriter + researcher.

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.11 / AI.11.1** | `execute_subagent`, orchestrator → copywriter child run |
| **AI.12** | Researcher in `_SUPPORTED_SUBAGENTS`; orchestrator → researcher child run |
| **AI.12.1** | This document — **freeze** copywriter + researcher execution boundaries |

---

## Supported child agents (frozen)

| Sub-agent | Child execution | Persona router |
|-----------|-----------------|----------------|
| **copywriter** | **Yes** — `orchestrator → copywriter` | Yes |
| **researcher** | **Yes** — `orchestrator → researcher` | Yes |
| **strategist** | **No** — prompt overlay only | Yes |
| **analyst** | **No** — prompt overlay only | Yes |

`_SUPPORTED_SUBAGENTS` = `{ copywriter, researcher }` only.

---

## Execution model (frozen)

| Rule | Status |
|------|--------|
| `orchestrator → copywriter` | **Allowed** |
| `orchestrator → researcher` | **Allowed** |
| Sequential only (one hop) | **Required** |
| One child per parent (`_MAX_CHILDREN_PER_PARENT = 1`) | **Required** |
| No nesting (child cannot `execute_subagent`) | **Forbidden** |
| LangGraph in marketer execution path | **Forbidden** |
| Handoff | **Forbidden** |
| Parallel sub-agents | **Forbidden** |
| `orchestrator → strategist` child run | **Forbidden** (AI.13+) |
| `orchestrator → analyst` child run | **Forbidden** |
| Approve / publish / schedule / archive from sub-agent child | **Forbidden** |
| New execution tools in registry | **Forbidden** |

**Module:** `app/agents/marketer/execution.py` → `execute_subagent()`

| Step | Behavior |
|------|----------|
| 1 | Validate `subagent_type` ∈ `_SUPPORTED_SUBAGENTS` |
| 2 | Reject if `parent_run.parent_agent_run_id` is set |
| 3 | Require parent agent `AgentType.ORCHESTRATOR` |
| 4 | Enforce ≤1 existing child for parent |
| 5 | Resolve project agent for `mapped_agent_type` (copywriter or researcher) |
| 6 | Create child with `parent_agent_run_id`, input `source: subagent_execution` |
| 7 | Execute child via **classic** `AgentRunCoordinator` |
| 8 | Return succeeded child run to chat layer |

**Chat:** `AgentChatService.send_message` — `delegate_subagent` when orchestrator + router selects supported type:

- Parent orchestrator run created (audit / linkage); parent LLM **not** executed on delegate path
- Response `agent_run_id` = parent; `subagent_execution` = `{ subagent, agent_run_id: child }`
- Assistant message `agent_run_id` = child

Migration (hierarchy): `alembic/versions/20260602_0006_agent_run_parent_hierarchy_phase_ai_11.py`

---

## Router (frozen examples)

**Module:** `app/agents/marketer/router.py`

| User message | Router | Child run |
|--------------|--------|-----------|
| **«Исследуй аудиторию»** | `researcher` | **Yes** — researcher child |
| **«Перепиши этот пост»** | `copywriter` | **Yes** — copywriter child |
| **«Проанализируй кампанию»** | `analyst` | **No** — persona overlay only |
| **«Сделай контент-план»** | `strategist` | **No** — persona overlay only |
| **«Проанализируй рынок»** | **`None`** | **No** — orchestrator voice |

### Disambiguation: «Проанализируй рынок»

Frozen as **`None`** (no sub-agent persona, no child):

- Does **not** match analyst phrase list (`проанализируй кампанию`, …) — campaign analysis is analyst-shaped, market wording is not auto-bound to analyst.
- Does **not** match researcher phrase list (`исследуй аудиторию`, `изучи бриф`, …) — research execution requires explicit research/brief phrases.
- Avoids ambiguous router → wrong child before **AI.13** (strategist) / future analyst execution.

Future router phrases for market analysis are a **separate** change (not AI.12.1).

Copywriter natural-language scoring unchanged from AI.11.1.

---

## Researcher tool profile (frozen)

From `app/agents/marketer/registry.py` — child uses `AgentType.RESEARCHER` allowlist subset:

| Allowed (read / context) |
|--------------------------|
| `marketing_brief.get`, `marketing_brief.list` |
| `project_context.get`, `memory.search`, `task.get` |

**Forbidden on researcher persona / child:**

- `content_asset.approve`, `content_asset.publish`, `content_asset.schedule`, `content_asset.archive`
- `publication_job.create`, `publication_job.schedule`
- Plan/asset **write** tools (`campaign_plan_draft.create`, `content_asset.create_revision`, …)

No new write permissions in AI.12 / AI.12.1.

---

## Boundaries (explicit no-goals)

| Capability | Status |
|------------|--------|
| Child runs for strategist | **Forbidden** until AI.13 |
| Child runs for analyst | **Forbidden** |
| Two children per parent | **Forbidden** |
| Child → child nesting | **Forbidden** |
| LangGraph / handoff / parallel / swarm | **Forbidden** in execution + chat delegate path |
| Sub-agent approves / publishes / schedules / archives | **Forbidden** |

---

## API / UI

| Surface | Field |
|---------|--------|
| `AgentChatSendResponse` | `subagent_execution: { subagent, agent_run_id }` optional |
| `AgentRun` contract | `parent_agent_run_id` optional |
| Web UI | «Handled by {Subagent}» when `subagent_execution` present |

---

## Relationship to prior freezes

| Layer | Doc |
|-------|-----|
| Copywriter execution | `docs/phase_ai_11_subagent_execution_readiness_audit.md` |
| Persona registry | `docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md` |
| Orchestrator scenarios | `docs/phase_ai_9_marketing_orchestrator_readiness_audit.md` |

---

## Future work (not AI.12.1)

- **AI.13** — strategist **execution** (same pattern; do not implement in AI.12.1)
- **AI.14** — multi-subagent orchestrator chain

---

## Freeze checklist

```bash
uv run pytest tests/test_subagent_execution.py
uv run pytest tests/test_phase_ai_12_subagent_execution_invariants.py
```
