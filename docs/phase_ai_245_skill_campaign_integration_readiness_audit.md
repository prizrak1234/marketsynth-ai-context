# Phase AI.245 — Skill-Campaign Integration Readiness Audit

**Date:** 2026-06-03  
**Status:** Ready (AI.236–AI.245)

---

## Scope delivered

| Phase | Deliverable | Status |
|-------|-------------|--------|
| AI.236 | Roadmap | ✅ |
| AI.237 | `CampaignSkillSuggestion` contract | ✅ |
| AI.238 | Campaign skill suggestion engine v1 | ✅ |
| AI.239 | Campaign-linked skill runs + timeline + provenance | ✅ |
| AI.240 | Skill results → `campaign.metadata.skill_context` | ✅ |
| AI.241 | Safe summaries → plan `project_context.campaign_skill_summaries` | ✅ |
| AI.242 | Action Center skill actions (explicit, no auto-run) | ✅ |
| AI.243 | Control Center skills UI (recommendations, runs, context cards) | ✅ |
| AI.244 | Regression tests | ✅ |
| AI.245 | This audit | ✅ |

---

## Flow verified

```
Business Operator → Campaign → Brief → Recommended Skills → Skill Runs
→ Campaign Context → Plan / Content / Media / Publishing
```

---

## Contracts

- `CampaignSkillSuggestion` — reason, priority, expected_output, related_brief_fields, related_next_action
- `CampaignSkillContext` — segment/offer/demand/analytics summaries + source_run_ids
- `CampaignControlCenter` — skill_suggestions, latest_skill_runs, skill_context
- `CampaignActionType` — run_* skill actions (7 types)
- `CampaignTimelineEventType.SKILL_RUN`

---

## Services

- `app/domain/campaign_skill_suggestion_engine.py` — rule-based recommendations from brief, intent, health, missing artifacts
- `app/domain/campaign_skill_input.py` — campaign input builder + action/skill mapping
- `app/services/campaign_skill_context_service.py` — merge successful runs into campaign + linked plans
- `app/services/campaign_control_center_service.py` — suggestions, timeline, latest runs
- `app/services/campaign_action_builder.py` — skill action buttons from suggestions
- `app/services/campaign_action_executor_service.py` — dispatch one skill per action
- `app/services/marketing_skill_run_service.py` — apply campaign context on success
- `app/services/scenario_wizard_service.py` — plan step copies safe skill summaries

---

## Invariants (regression)

- Skill suggestions never auto-run skills
- Action Center runs exactly one skill per action
- Successful skill output merges into campaign `skill_context` (safe summaries only)
- Wizard plan receives `campaign_skill_summaries` without raw tool payloads
- Data skills call tools only when `create_tool_call=true` (actions use `false`)

---

## Regression

```bash
uv run pytest tests/test_phase_ai_244_skill_campaign_integration_regression.py -q
uv run pytest tests/test_phase_ai_235_marketing_skills_freeze.py -q
```

---

## UI

- Campaign Control Center skills block: recommendations with reason, run buttons, latest runs, output cards, skill context summaries
- Action Center exposes matching `run_*` actions when suggestions are present

---

## Permissions

Unchanged from AI.235: `MARKETING_SKILLS_ENABLED`, `MARKETING_DATA_TOOLS_ENABLED` (prod default off).
