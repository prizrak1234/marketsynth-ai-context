## Phase AI.13.1 — Strategist execution readiness audit (freeze)

This audit **freezes** the execution layer after adding **strategist** as the third real child agent (Phase AI.13). Architecture **3.2** unchanged: one sequential child per orchestrator parent, classic `AgentRunCoordinator` only.

**Not in this freeze:** analyst child runs, multi-hop chains (orchestrator → multiple children), LangGraph, handoff, parallel execution, or new write permissions beyond existing gated strategist tools.

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.11 / AI.11.1** | `execute_subagent`, orchestrator → copywriter |
| **AI.12 / AI.12.1** | Researcher child execution + «Проанализируй рынок» = `None` |
| **AI.13** | Strategist in `_SUPPORTED_SUBAGENTS`; orchestrator → strategist child |
| **AI.13.1** | This document — **freeze** three child agents + strategist boundaries |

---

## Supported child agents (frozen)

| Sub-agent | Child execution | Persona router |
|-----------|-----------------|----------------|
| **copywriter** | **Yes** — `orchestrator → copywriter` | Yes |
| **researcher** | **Yes** — `orchestrator → researcher` | Yes |
| **strategist** | **Yes** — `orchestrator → strategist` | Yes |
| **analyst** | **No** — prompt overlay only | Yes |

`_SUPPORTED_SUBAGENTS` = `{ copywriter, researcher, strategist }` only.

---

## Execution paths (frozen)

| Path | Status |
|------|--------|
| `orchestrator → copywriter` | **Allowed** |
| `orchestrator → researcher` | **Allowed** |
| `orchestrator → strategist` | **Allowed** |
| `orchestrator → analyst` | **Forbidden** (future phase) |
| Sequential only (single hop per message) | **Required** |
| One child per parent | **Required** |
| No nesting (child cannot `execute_subagent`) | **Forbidden** |
| LangGraph / handoff / parallel / swarm | **Forbidden** |
| Multi-child chain under one parent (AI.14+) | **Forbidden** in AI.13.1 |

**Module:** `app/agents/marketer/execution.py` → `execute_subagent()`

**Chat:** `AgentChatService.send_message` — `delegate_subagent` when orchestrator + `selected_subagent in _SUPPORTED_SUBAGENTS`:

- Parent orchestrator run created; parent LLM **not** executed on delegate path
- `subagent_execution` = `{ "subagent": "<type>", "agent_run_id": "<child>" }`
- Strategist example: `{ "subagent": "strategist", "agent_run_id": "..." }`

---

## Router (frozen strategist phrases)

**Module:** `app/agents/marketer/router.py` — `MarketerSubAgentType.STRATEGIST` phrase list:

| Phrase (substring match) |
|--------------------------|
| `сделай контент-план` |
| `создай контент-план` |
| `разработай стратегию` |
| `стратегия запуска` |
| `позиционирование` |
| `оффер` |
| `план кампании` |

### Frozen routing examples

| User message | Router | Child run |
|--------------|--------|-----------|
| **«Сделай контент-план»** | `strategist` | **Yes** |
| **«Разработай стратегию запуска»** | `strategist` | **Yes** |
| **«Нужно позиционирование для продукта»** | `strategist` | **Yes** (contains `позиционирование`) |
| **«Предложи оффер»** | `strategist` | **Yes** (contains `оффер`) |
| **«Перепиши этот пост»** | `copywriter` | **Yes** |
| **«Исследуй аудиторию»** | `researcher` | **Yes** |
| **«Проанализируй кампанию»** | `analyst` | **No** — persona only |
| **«Проанализируй рынок»** | **`None`** | **No** — orchestrator only (AI.12.1) |

### Disambiguation: «Проанализируй рынок»

Unchanged from **AI.12.1**: router returns **`None`** — no analyst/researcher/strategist child. Do not auto-route market-analysis wording until an explicit future router change.

---

## Strategist tool profile (frozen)

From `app/agents/marketer/registry.py` — child uses `AgentType.STRATEGIST` / persona allowlist:

| Allowed (typical) |
|-------------------|
| `marketing_campaign.get`, `marketing_campaign.workflow` |
| `marketing_brief.get`, `marketing_brief.list` |
| `campaign_plan_draft.create` — **only when** existing env flags enable write tools (no new permissions in AI.13) |

**Forbidden on strategist persona / child:**

- `content_asset.approve`, `content_asset.publish`, `content_asset.schedule`, `content_asset.archive`
- `publication_job.create`, `publication_job.schedule`
- Spawning child runs from a strategist child run

Strategist does **not** automatically create plan drafts outside gated tool visibility.

---

## Boundaries (explicit no-goals)

| Capability | Status |
|------------|--------|
| `orchestrator → analyst` child | **Forbidden** |
| Two+ children per parent / sequential chain in one message | **Forbidden** (AI.14) |
| Child → child nesting | **Forbidden** |
| LangGraph / handoff / parallel | **Forbidden** |
| Sub-agent approve / publish / schedule / archive | **Forbidden** |
| New execution-layer tools in registry | **Forbidden** |

---

## API / UI

| Surface | Field |
|---------|--------|
| `AgentChatSendResponse` | `subagent_execution: { subagent, agent_run_id }` optional |
| Web UI | «Handled by {Subagent}» |

---

## Relationship to prior freezes

| Layer | Doc |
|-------|-----|
| Researcher execution | `docs/phase_ai_12_researcher_execution_readiness_audit.md` |
| Copywriter execution | `docs/phase_ai_11_subagent_execution_readiness_audit.md` |
| Persona registry | `docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md` |

---

## Future work (not AI.13.1)

- **AI.14** — multi-subagent orchestrator: one parent → **multiple sequential** child runs (model change)
- Analyst **execution** (separate phase; not part of AI.14 chain unless explicitly specified)

---

## Freeze checklist

```bash
uv run pytest tests/test_phase_ai_13_strategist_execution.py
uv run pytest tests/test_phase_ai_13_strategist_execution_invariants.py
```
