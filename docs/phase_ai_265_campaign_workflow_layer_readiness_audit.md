# Phase AI.265 — Campaign Workflow Layer Readiness Audit

**Date:** 2026-06-03  
**Status:** Ready (AI.256–AI.265)

---

## Scope delivered

| Phase | Deliverable | Status |
|-------|-------------|--------|
| AI.256 | Roadmap | ✅ |
| AI.257 | Raw workflow inventory index | ✅ |
| AI.258 | `CampaignWorkflowTemplate` contract | ✅ |
| AI.259 | Curated registry v1 (5 templates) | ✅ |
| AI.260 | Recommendation engine (read-only) | ✅ |
| AI.261 | `CampaignWorkflowRun` persistence | ✅ |
| AI.262 | Workflow API | ✅ |
| AI.263 | Step → Action Center mapping | ✅ |
| AI.264 | Control Center UI + regression | ✅ |
| AI.265 | This audit | ✅ |

---

## Contracts

- `CampaignWorkflowTemplate` — id, name, goal, scenarios, brief fields, skills, tools, steps, artifacts, out_of_scope
- `CampaignWorkflowStep` — recommended action/skill/tool (recommendation only)
- `CampaignWorkflowSuggestion` — read-only template pick
- `CampaignWorkflowRun` — draft | active | completed | archived checklist state
- `CampaignWorkflowRunSummary` — active run + step views + progress for Control Center

---

## Services

- `app/marketing/workflows/registry.py` — five reusable process templates
- `workflows/mapped/raw_inventory_index.json` — read-only archive index (AI.257)
- `workflows/mapped/curated_templates.json` — curation manifest (AI.259)
- `docs/WORKFLOW_RAW_INVENTORY.md` — human-readable inventory
- `app/domain/campaign_workflow_recommendation_engine.py` — scenario, brief, supervisor, skills, artifacts
- `app/domain/campaign_workflow_step_mapper.py` — step progress inference from campaign state
- `app/services/campaign_workflow_service.py` — recommend, create run, active summary

---

## Invariants

- **Not** Make-import, **not** auto-execution, **not** background worker
- Recommendations are read-only until user starts a checklist
- `create-run` inserts one workflow run row only — no skill/tool execution
- Steps link to existing `CampaignActionType` buttons — user runs explicitly
- Supervisor findings can elevate workflow suggestions (e.g. brief gaps → `offer_validation`)

---

## Regression

```bash
uv run pytest tests/test_phase_ai_264_campaign_workflow_layer_regression.py -q
uv run python scripts/build_workflow_raw_inventory.py
```

---

## UI

Campaign Control Center workflow panel: recommended templates, active checklist, step status, linked Action Center buttons, progress bar.

---

## Next (out of scope)

- Manual step completion recording
- Gradual Make-workflow → managed template migration
- Workflow analytics across campaigns
