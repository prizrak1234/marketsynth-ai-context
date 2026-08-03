## Phase AI.15.1 — General Agent readiness audit (freeze)

This audit **freezes** the top-level General Agent router (Phase AI.15). General detects domain and **delegates**; it does not execute marketing work, tools, or approve/publish/schedule/archive actions.

**Superseded by AI.16 / AI.16.1:** `GeneralDomain.PROGRAMMER` and Programmer delegation freeze (`docs/phase_ai_16_programmer_domain_readiness_audit.md`).

**Still not in scope:** Media, Tilda, Email domains; General executing sub-agents directly; depth > 2; LangGraph / handoff / parallel.

---

## Role (frozen)

| Rule | Status |
|------|--------|
| General = top-level router | **Required** |
| Supported domain | **marketing only** |
| Unknown intent | Clarification text, **no** Marketer child run |
| Marketing intent | Creates General parent run → Marketer orchestrator child → existing AI.14 chain (if matched) |
| General executes marketing work | **Forbidden** |
| General tool allowlist | **Empty** |
| approve / publish / schedule / archive | **Forbidden** on General |

---

## AgentRun hierarchy (frozen)

`MAX_AGENT_RUN_DEPTH = 2` (`app/agents/run_depth.py`)

| Depth | Run type |
|-------|----------|
| **0** | General parent (`parent_agent_run_id` = null) |
| **1** | Marketer orchestrator child under General (`source` = `general_delegation`) |
| **2** | Marketer subagents (siblings under orchestrator child; `source` = `subagent_execution`) |

Direct orchestrator chat (no General): orchestrator at depth **0**, subagents at depth **1** — still within max depth.

Creating a child when parent depth ≥ `MAX_AGENT_RUN_DEPTH` → `InvalidStateError` (“Maximum agent run depth exceeded”).

Subagent runs **cannot** delegate further (`Only orchestrator runs may delegate to sub-agents`).

---

## Domain routing (`app/agents/general/router.py`)

| Domain | Behavior |
|--------|----------|
| **marketing** | Phrase match → delegate to project orchestrator |
| **unknown** | `UNKNOWN_DOMAIN_CLARIFICATION`, no delegation |

`GeneralDomain` enum: `marketing`, `unknown` (AI.15.1); `programmer` added in **AI.16**.

**Not routed:** media, tilda, email — no handlers, no child runs.

---

## Delegation payload (frozen)

Marketer orchestrator child receives:

```json
{
  "source": "general_delegation",
  "parent_agent_run_id": "<general-run-uuid>",
  "delegated_domain": "marketing"
}
```

---

## Chat API

| Field | When |
|-------|------|
| `general_delegation.domain` | General + marketing intent |
| `general_delegation.agent_run_id` | Marketer orchestrator child run id |
| `subagent_chain[]` | After orchestrator runs AI.14 chain (optional) |
| `general_delegation` | **Absent** on direct orchestrator chat |

---

## Relationship to AI.14

- AI.14 chains unchanged: max 3 sibling subagents under **orchestrator** parent.
- General adds **one** extra hierarchy level (orchestrator may be depth 1 under General).
- `execute_marketer_orchestrator_delegation` shared by orchestrator chat and General delegation.

---

## Freeze checklist

```bash
uv run pytest tests/test_general_agent_skeleton.py
uv run pytest tests/test_phase_ai_15_general_agent_invariants.py
uv run pytest tests/test_phase_ai_14_subagent_chain_invariants.py
```

**Not in this freeze:** AI.16+ domain skeletons (Programmer, Media, etc.).
