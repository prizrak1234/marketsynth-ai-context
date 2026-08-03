## Phase AI.9.1 — Marketing orchestrator readiness audit (freeze)

This audit freezes the **first orchestrator behavior layer** in agent chat (Phase AI.9): marketing scenario detection and workflow-aware **recommended_next_steps** in the prompt. AI.9 adds **marketing thinking**, not new tools or write permissions.

This is the first brick of architecture **3.2** (General → Marketer → sub-agents): coordinate campaigns in chat before sub-agent registry work (AI.10+).

Human approve, schedule, publish, and plan execution remain **UI-only** or gated chat writes defined in earlier freezes (AI.3–AI.8).

**Superseded for sub-agent personas by:** AI.10 / AI.10.1 (`docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md`).

---

## Phases in scope

| Phase | What shipped |
|-------|----------------|
| **AI.1–AI.2** | Chat pipe, optional `campaign_id` → workflow snapshot |
| **AI.3–AI.6** | Gated plan create, generate assets (orchestrator / content_planner) |
| **AI.7 / AI.7.1** | Chat revision write boundary |
| **AI.8 / AI.8.1** | Campaign-aware copywriter context (quality, not permissions) |
| **AI.9** | Scenario detection + `scenario_context` for orchestrator coordination |
| **AI.9.1** | This document — behavior freeze, no new tools/permissions |

---

## What AI.9 does (allowed)

### Scenario detection

**Module:** `app/agents/scenarios/detector.py` → `detect_marketing_scenario(message, workflow_state)`.

Inputs:

- Sanitized chat **message**
- **workflow_state** from `CampaignWorkflowService` (via `AgentChatWorkflowContext`)

Output: `MarketingScenarioType | None` (`None` = unknown / generic request → workflow fallback).

### Scenario types (frozen set)

| `MarketingScenarioType` | Typical triggers |
|-------------------------|------------------|
| `content_launch` | Plan / launch / content launch phrases |
| `telegram_content_month` | Monthly Telegram content plan |
| `lead_magnet` | Lead magnet / checklist |
| `product_announcement` | New product / launch announcement |
| `campaign_revival` | Revive / reactivate campaign; `completed` workflow hint |

Source: `app/agents/scenarios/contracts.py`.

### Scenario context builder

**Module:** `app/agents/scenario_context.py` → `build_marketing_scenario_context(...)`.

Injected when `campaign_id` is set: `AgentChatService.send_message` → `agent_chat.scenario_context` in run `input_payload`.

Always includes:

| Field | Role |
|-------|------|
| `workflow_state` | Current campaign workflow enum string |
| `recommended_next_steps` | Ordered human/UI steps (max 5) |
| `scenario_type` | Detected scenario value or `null` |
| `scenario_detected` | `true` when a scenario matched |
| `next_recommended_action` | Workflow read-model hint |
| `pending_review_assets` | Review queue count snapshot |

### Workflow-aware recommendations

`build_recommended_next_steps()` combines:

1. **Scenario-specific** steps when `scenario_type` is set
2. **Workflow fallback** when scenario is unknown (e.g. «Что делать дальше?»)

Example (`ready_for_review`, 3 pending):

1. Review 3 draft asset(s) in Review Queue (`/review`)
2. Approve assets in the UI
3. Schedule approved assets in the publication calendar (human-initiated)

### Campaign-aware orchestration (prompt only)

**Orchestrator** (`AgentType.ORCHESTRATOR`) when `scenario_detected`:

- `_AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES` in `app/prompts/agent_chat_workflow.py`
- Act as marketing **coordinator**; use numbered `recommended_next_steps`
- Never claim a step completed without tool confirmation
- **Marketing scenario context** block always present for orchestrator when campaign is selected (including fallback steps)

Other agent types do **not** receive the scenario coordinator rules block.

---

## Data sources (guidance only — no new tools)

Orchestrator rules reference **existing** read tools when available (non-chat profile or gated chat profiles from prior phases):

| Source | Tool / UI |
|--------|-----------|
| Workflow | `marketing_campaign.workflow` |
| Campaign | `marketing_campaign.get`, `marketing_campaign.overview` |
| Review queue | `review_queue.list` → UI `/review` |
| Calendar | `publication_calendar.list` → publication calendar UI |

AI.9 does **not** register new tools. Chat tool allowlists (`AGENT_CHAT_*`) are unchanged by AI.9.

---

## Explicit no-goals (AI.9.1 freeze)

Agent scenario layer must **not**:

| Capability | Status |
|------------|--------|
| Approve assets | **Forbidden** — steps say «in the UI» only; no `content_asset.approve` in scenario layer |
| Schedule publication | **Forbidden** — human-initiated wording only; no schedule write tools |
| Publish / dispatch | **Forbidden** |
| Execute multi-step plans automatically | **Forbidden** — advisory steps only |
| Create publication jobs | **Forbidden** — no `publication_job.create` |
| Modify campaign status | **Forbidden** — no campaign write tools in chat |
| New write tools | **Forbidden** — zero added in AI.9 |
| New read tools | **Forbidden** — zero added in AI.9 |
| New permissions / flags | **Forbidden** — reuses AI.7 revision + prior chat flags only |
| Auto-execution | **Forbidden** — prompt coordination only |

---

## Fallback behavior

When `detect_marketing_scenario()` returns `None`:

- `scenario_detected: false`, `scenario_type: null`
- `recommended_next_steps` still populated from **workflow_state** (+ `next_recommended_action`, `pending_review_assets`)
- Orchestrator uses standard advisor rules + **Marketing scenario context** block (no coordinator rules until a scenario is detected)

---

## Related freezes

| Doc | Boundary |
|-----|----------|
| `docs/phase_ai_7_revision_readiness_audit.md` | Chat revision writes |
| `docs/phase_ai_8_campaign_aware_revision_readiness_audit.md` | Revision prompt context |
| `docs/phase_14_review_queue_readiness_audit.md` | Human review |
| `docs/phase_13_campaign_workflow_readiness_audit.md` | Workflow read model |

---

## Future work (not AI.9.1)

- **AI.10 / AI.10.1** — marketer sub-agent registry freeze (`docs/phase_ai_10_marketer_subagent_registry_readiness_audit.md`)
- **AI.11** — real sub-agent execution (separate freeze required)

---

## Freeze checklist

```bash
uv run pytest tests/test_marketing_scenarios.py
uv run pytest tests/test_phase_ai_9_marketing_orchestrator_invariants.py
uv run pytest tests/test_phase_ai_8_campaign_aware_revision_invariants.py
uv run pytest tests/test_phase_ai_7_revision_invariants.py
```
