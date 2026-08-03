# Phase AI.236 — Skill-Campaign Integration Roadmap

**Date:** 2026-06-03  
**Goal:** Connect skills to campaigns as the operating brain — not a side panel.

---

## Flow

```
Business Operator → Campaign → Brief → Recommended Skills → Skill Runs
→ Campaign Context → Plan / Content / Media / Publishing
```

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.236 | This roadmap |
| AI.237 | `CampaignSkillSuggestion` contract |
| AI.238 | Skill suggestion engine v1 |
| AI.239 | Campaign-linked runs, timeline, provenance |
| AI.240 | Skill results → campaign `skill_context` |
| AI.241 | Safe summaries → plan `project_context` |
| AI.242 | Action Center skill actions |
| AI.243 | Control Center skill UI |
| AI.244 | Regression |
| AI.245 | Freeze audit |

---

## Principles

- Suggestions never auto-run skills
- Action Center runs exactly one skill per action
- Tool calls only when `create_tool_call=true`
- Plan/campaign context gets safe summaries only — no raw tool payloads

---

## Regression

```bash
uv run pytest tests/test_phase_ai_244_skill_campaign_integration_regression.py -q
```
