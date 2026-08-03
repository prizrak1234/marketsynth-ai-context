# Phase AI.156 — Campaign Control Center Roadmap

**Date:** 2026-06-03  
**Goal:** Campaign becomes the **main business screen** — what is done, stuck, and next.

---

## Context

AI.146–AI.155 delivered **Campaign** as an orchestration container (CRUD, metrics, wizard entry, provenance). Users still ask: *“What do I click next?”*

The Control Center answers that **without** new agents, auto-execution, or frozen pipeline changes.

---

## Deliverables

| Phase | Item |
|-------|------|
| AI.157 | Read-only **timeline** (wizard steps → publish job) |
| AI.158 | **Next action engine** — recommendation only |
| AI.159 | **Health status** + safe `blocking_reason` |
| AI.160 | `GET .../control-center` aggregate API |
| AI.161 | Control Center UI (progress, next action, timeline, links) |
| AI.162 | **Failure recovery hints** — no auto-recovery |
| AI.163 | List/search filters: health, next_action, failed/completed |
| AI.164 | Regression tests |
| AI.165 | Freeze audit + docs |

---

## API

```
GET /projects/{id}/business-campaigns/{campaign_id}/control-center

GET /projects/{id}/business-campaigns?view=control&health=&next_action_type=&failed_only=&completed_only=
GET /projects/{id}/business-campaigns/search?view=control&...
```

Response (`CampaignControlCenter`):

- `campaign`, `health`, `next_action`, `timeline`, `metrics`, `resource_ids`, `safe_warnings`, `recovery_hint`

---

## Next action types (AI.158)

Recommendations map to **existing** manual APIs / wizard advance — never auto-run:

- `attach_scenario`, `start_wizard`, `advance_wizard`
- `approve_plan`, `start_execution`, `execute_next_specialist`
- `approve_copywriter_output`, `create_content_asset`, `approve_asset`
- `create_media_brief`, `approve_media_brief`, `create_publication_package`
- `schedule_or_dry_run`

---

## Health (AI.159)

| Status | Meaning |
|--------|---------|
| `healthy` | Ready to proceed, no failures |
| `waiting_for_user` | Manual step required |
| `blocked` | Missing prerequisite (e.g. no scenario) |
| `failed` | Wizard, execution, or job failed |
| `completed` | Dry-run job queued / pipeline done |

---

## Invariants (AI.165)

- Control Center is **read-only** — no hidden automation
- Does **not** change frozen pipeline or specialist matrix
- Does **not** execute specialists, approve, or publish on behalf of user
- Recovery hints are **suggestions only**

---

## Why this step

Campaign container → **campaign command panel**. Same product depth as an agency dashboard, zero new agent risk.
