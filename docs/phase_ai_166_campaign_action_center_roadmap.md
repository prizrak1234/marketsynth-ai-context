# Phase AI.166 — Campaign Action Center Roadmap

**Date:** 2026-06-03  
**Goal:** Turn Control Center **next_action** into explicit **action buttons** that call existing services.

---

## Context

AI.156–AI.165 delivered read-only Control Center (health, timeline, recommendations). Users still jump across panels to act.

Action Center adds **safe explicit buttons** — not background automation.

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.167 | `CampaignAction` contract |
| AI.168 | Action builder from control center state |
| AI.169 | `POST .../actions/{action_type}/execute` |
| AI.170 | Safety guards (no real publish, no worker, match available actions) |
| AI.171 | `CampaignActionResult` + optional control center snapshot |
| AI.172 | UI primary/secondary buttons + confirmation modal |
| AI.173 | Optional `Idempotency-Key` replay (hashed, no raw storage) |
| AI.174 | Regression — dental wizard via actions to dry-run |
| AI.175 | Freeze audit + docs |

---

## API

```
GET  .../business-campaigns/{id}/control-center   ← adds primary_action + available_actions

POST .../business-campaigns/{id}/actions/{action_type}/execute
Header: Idempotency-Key (optional)
```

---

## Action types (AI.168)

`start_wizard`, `advance_wizard`, `approve_plan`, `start_execution`, `execute_next_specialist`, `approve_copywriter_output`, `create_content_asset`, `submit_asset_review`, `approve_asset`, `create_media_brief`, `submit_media_brief_review`, `approve_media_brief`, `create_publication_package`, `submit_package_review`, `approve_package`, `create_publication_job`, `schedule_job`, `dry_run_dispatch`

---

## Invariants (AI.170)

- One action per request; server rebuilds state — **no client payload trust**
- Does not bypass approval gates
- **No real Telegram publish** — dry-run dispatch only
- No background workers / external providers
- Action must match `available_actions` (enabled)
- Frozen pipeline unchanged

---

## Why this step

See recommendation → click button → see updated control center. One-screen agency cockpit.
