# Phase AI.246 — Campaign Supervisor Roadmap

**Date:** 2026-06-03  
**Goal:** Read-only campaign quality controller — gaps, contradictions, risks. Not an agent. Not auto-run.

---

## Scope

```
Brief + Intent + Scenario + Skills + Plan + Outputs + Media + Publishing
→ Supervisor Rule Engine → Findings + Health Score → Control Center + API
```

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.246 | This roadmap |
| AI.247 | `CampaignSupervisorFinding`, `CampaignSupervisorReport` contracts |
| AI.248 | Supervisor rule engine v1 |
| AI.249 | `GET .../supervisor-report` |
| AI.250 | Control Center summary fields |
| AI.251 | Quality panel UI |
| AI.252 | Findings → `CampaignActionType` suggestions |
| AI.253 | Safe audit logging |
| AI.254 | Regression |
| AI.255 | Freeze audit |

---

## Principles

- Read-only — no side effects, no LLM, no tools
- Findings may reference Action Center buttons — user executes explicitly
- Safe metadata only — no raw brief/content/tool payloads

---

## Regression

```bash
uv run pytest tests/test_phase_ai_254_campaign_supervisor_regression.py -q
```
