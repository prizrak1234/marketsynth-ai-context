# UI.13 — Product analytics (deferred)

**Status:** Not implemented. Prioritized **after** internal tester round (demo script, feedback, 10–15 sessions).

## Intended scope (when resumed)

Minimal telemetry — simple events table, no full product analytics suite.

| Event | Trigger (conceptual) |
|-------|----------------------|
| `campaign_created` | Human creates campaign via UI/API |
| `plan_draft_created` | Plan draft created |
| `assets_generated` | Plan draft generate-assets success |
| `asset_approved` | Human approve |
| `publication_scheduled` | Publication job created with `scheduled_at` |
| `channel_created` | Publishing channel created |

## Why deferred

- Post–UI.12, **qualitative feedback from real testers** beats more backend phases.
- Event schema should reflect **actual** friction points from feedback, not guessed funnels.
- See prioritization in team decision: demo materials → 10–15 demos → analysis → UI.13.

## Prerequisites before implementation

- [ ] ≥5 completed [ui_tester_feedback_template.md](./ui_tester_feedback_template.md) forms  
- [ ] Agreement on PII (no body text in events)  
- [ ] Contract entry in `app/schemas/contracts.py` before DB  
- [ ] Tests for ingest endpoint or service  

Do not add agent-side analytics tools in the same phase.
