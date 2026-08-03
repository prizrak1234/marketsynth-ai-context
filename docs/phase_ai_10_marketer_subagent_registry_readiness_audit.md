## Phase AI.10.1 — Marketer sub-agent registry readiness audit (freeze)

This audit freezes **persona routing only** for the Marketer orchestrator (Phase AI.10). The registry defines who should answer; it does **not** spawn child agents or change execution permissions.

Architecture **3.2** step: General → Marketer → (future) sub-agent execution. AI.10.1 locks the **registry + router + prompt overlay** before AI.11 changes the execution model.

**Not in this freeze:** AI.11 real sub-agent execution (child `AgentRun`, handoff, parallel runs).

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.9 / AI.9.1** | Orchestrator scenarios + workflow steps (prompt only) |
| **AI.10** | Marketer sub-agent registry, router, orchestrator persona overlay |
| **AI.10.1** | This document — registry freeze, no execution |

---

## Sub-agent set (frozen: four, not twelve)

| `MarketerSubAgentType` | `mapped_agent_type` |
|------------------------|---------------------|
| `strategist` | `AgentType.STRATEGIST` |
| `copywriter` | `AgentType.COPYWRITER` |
| `analyst` | `AgentType.ANALYST` |
| `researcher` | `AgentType.RESEARCHER` |

Source: `app/agents/marketer/contracts.py`, `app/agents/marketer/registry.py`.

No `content_planner`, `critic`, or additional personas in AI.10.1.

---

## Registry profile fields

Each entry in `_REGISTRY` is a `MarketerSubAgentProfile`:

| Field | Purpose |
|-------|---------|
| `subagent_type` | `MarketerSubAgentType` enum value |
| `name` | Human-readable persona name |
| `description` | Short role summary |
| `responsibilities` | Tuple of responsibility strings |
| `allowed_tools` | Frozenset of tool names this persona may use (documentation + prompt) |
| `mapped_agent_type` | Corresponding `AgentType` for allowlist validation |

API:

- `list_subagents()`
- `get_subagent(subagent_type)`
- `get_subagent_prompt(subagent_type)` → `app/prompts/marketer_subagents.py`

---

## Router (phrase matching)

**Module:** `app/agents/marketer/router.py` → `detect_best_subagent(message)`.

| User intent (examples) | Routed persona |
|------------------------|----------------|
| «Перепиши пост» / improve copy | `copywriter` |
| «Проанализируй кампанию» | `analyst` |
| «Сделай контент-план» | `strategist` |
| «Исследуй аудиторию» | `researcher` |
| Generic / unknown («Что делать дальше?») | `None` → orchestrator voice |

`None` means **no** `subagent_routing` payload field (orchestrator coordinates without persona overlay rules).

---

## Chat integration (orchestrator-only overlay)

**Injection:** `AgentChatService.send_message` → when `detect_best_subagent()` returns a type:

```json
{ "subagent_routing": { "selected_subagent": "copywriter" } }
```

**Prompt:** `build_agent_chat_workflow_system_content()` in `app/prompts/agent_chat_workflow.py`:

- **Only** when `agent_type == AgentType.ORCHESTRATOR` and `selected_subagent` is set:
  - Persona prompt from `get_subagent_prompt()`
  - `Marketer sub-agent routing` context block (responsibilities, `allowed_tools`)
- **Not** applied when user selects a direct `copywriter` / `strategist` agent row — same DB agent, no overlay

Single parent `AgentRun` per chat message (unchanged). Persona is **prompt-layer only**.

---

## What AI.10 does (allowed)

- Register four marketer personas with metadata
- Route chat text to a persona suggestion
- Enrich orchestrator system prompt with persona voice and tool hints
- Validate persona `allowed_tools` ⊆ mapped `AgentType` tool profile (when write flags on)

---

## Explicit no-goals (AI.10.1 freeze)

| Capability | Status |
|------------|--------|
| Child `AgentRun` per sub-agent | **Forbidden** — not implemented |
| LangGraph / swarm | **Forbidden** |
| Handoff queue / child run execution | **Forbidden** |
| Parallel sub-agent execution | **Forbidden** |
| Sub-agent memory layer | **Forbidden** |
| Approve / publish / schedule via persona | **Forbidden** — `FORBIDDEN_PERSONA_TOOLS` |
| New tools in registry | **Forbidden** — persona tools must exist in global registry |
| New chat write permissions | **Forbidden** — reuses AI.3–AI.8 gates only |
| Auto-execution of persona steps | **Forbidden** — advisory routing only |

Persona prompts explicitly state: do not approve, schedule, or publish from chat.

---

## Relationship to prior freezes

| Layer | Doc |
|-------|-----|
| Chat writes | `docs/phase_ai_7_revision_readiness_audit.md` |
| Revision context | `docs/phase_ai_8_campaign_aware_revision_readiness_audit.md` |
| Orchestrator scenarios | `docs/phase_ai_9_marketing_orchestrator_readiness_audit.md` |

AI.10 does not replace scenarios or revision context; orchestrator may receive **scenario_context**, **subagent_routing**, and workflow blocks in one run.

---

## Future work (not AI.10.1)

- **AI.11** — real sub-agent execution (child runs or delegated runs — separate freeze required)
- **AI.12** — General Agent
- **Marketer sub-agent expansion** — additional personas beyond four (explicit phase only)

---

## Freeze checklist

```bash
uv run pytest tests/test_marketer_subagent_registry.py
uv run pytest tests/test_phase_ai_10_marketer_subagent_registry_invariants.py
uv run pytest tests/test_phase_ai_9_marketing_orchestrator_invariants.py
```
