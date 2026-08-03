## Phase AI.14.1 — Multi-subagent sequential chain readiness audit (freeze)

This audit **freezes** linear multi-child execution under one orchestrator parent (Phase AI.14). All children are **siblings** (`parent_agent_run_id` = orchestrator run id). No DAG, LangGraph, handoff, or parallel execution.

**Not in this freeze:** analyst child runs, child→child nesting, more than 3 children per parent. General Agent hierarchy is frozen in **AI.15.1** (`docs/phase_ai_15_general_agent_readiness_audit.md`).

---

## Supported child agents (unchanged from AI.13.1)

`copywriter`, `researcher`, `strategist` — analyst persona-only.

---

## Execution model (frozen)

| Rule | Status |
|------|--------|
| Max chain length | **3** (`MAX_SUBAGENT_CHAIN_LENGTH`) |
| All children share same `parent_agent_run_id` | **Required** |
| Sequential execution only | **Required** |
| `previous_child_output` handoff | **Required** (compact, ≤ 4 KB) |
| Child → child spawn | **Forbidden** |
| LangGraph / handoff / parallel | **Forbidden** |
| Approve / publish / schedule / archive | **Forbidden** |

---

## Frozen chains (`app/agents/marketer/chains.py`)

| Chain | Steps |
|-------|--------|
| **CONTENT_LAUNCH** | researcher → strategist → copywriter |
| **CONTENT_PLAN** | strategist → copywriter |
| **RESEARCH** | researcher |
| **REWRITE** | copywriter |

---

## Router (`detect_execution_chain`)

| Message | Chain |
|---------|--------|
| «Запусти новый продукт» | CONTENT_LAUNCH (3) |
| «Сделай контент-план» | CONTENT_PLAN (2) |
| «Перепиши этот пост» | REWRITE (1) |
| «Исследуй аудиторию» | RESEARCH (1) |
| «Проанализируй рынок» | **None** (AI.12.1) |

---

## Chat API

| Field | Purpose |
|-------|---------|
| `subagent_chain[]` | Full ordered list `{ subagent, agent_run_id }` |
| `subagent_execution` | Last step (backward compatible) |

---

## Freeze checklist

```bash
uv run pytest tests/test_subagent_chain_execution.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
```
