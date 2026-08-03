# Integration I5 — MarketingPlan audit

**Option B:** MarketingPlan is a **project-scoped specialist execution spine**, not GTM Strategy.

## Actual shape

| Field | Present |
|-------|---------|
| title, goal | yes |
| specialist_tasks[] | yes (task prompts) |
| status draft/approved/archived | yes |
| versions | yes |
| positioning / segments / offers / funnel / budget / KPIs | **no** |
| campaign_id FK | **no** (soft `project_context.source_campaign_id`) |

## APIs (read in I5)

- `GET /projects/{id}/marketing-plans`
- `GET .../marketing-plans/{plan_id}`
- `GET .../versions`
- `POST .../approve` | `archive` — **not called** from Strategy Workspace in I5

Create paths: scenarios, chat save, wizard, demo — **orthogonal** to Alpha Strategy.

Approve does **not** create Campaign or execution run (execution is a separate follow-up API).
