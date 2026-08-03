# Phase AI.175 — Campaign Action Center Readiness Audit

**Date:** 2026-06-03  
**Scope:** Explicit campaign action buttons calling existing services (AI.166–AI.174).

---

## 1. Product intent

Control Center (AI.156–AI.165) recommends next steps. **Action Center** adds safe **Execute** buttons — one action per request, server-validated, no hidden automation.

---

## 2. API

```
GET  .../business-campaigns/{id}/control-center
     → primary_action + available_actions

POST .../business-campaigns/{id}/actions/{action_type}/execute
Header: Idempotency-Key (optional)
```

Contracts: `CampaignAction`, `CampaignActionResult` in `app/schemas/contracts.py`

---

## 3. Action types (AI.168)

`start_wizard`, `advance_wizard`, `approve_plan`, `start_execution`, `execute_next_specialist`, `approve_copywriter_output`, `create_content_asset`, `submit_asset_review`, `approve_asset`, `create_media_brief`, `submit_media_brief_review`, `approve_media_brief`, `create_publication_package`, `submit_package_review`, `approve_package`, `create_publication_job`, `schedule_job`, `dry_run_dispatch`

Builder: `app/services/campaign_action_builder.py`  
Executor: `app/services/campaign_action_executor_service.py`

---

## 4. Safety guards (AI.170)

| Guard | Enforcement |
|-------|-------------|
| Match available actions | 409 if action not enabled in current snapshot |
| No client payload trust | Server rebuilds state; empty POST body |
| Approval workflow | Uses existing submit/approve services |
| No real Telegram publish | `dry_run_dispatch` only uses `PublishingDispatchMode.DRY_RUN` |
| No background worker | Direct service calls only |
| No external providers | No media generation / real send |
| Frozen pipeline | No changes to specialist matrix |
| Active wizard | Non-advance actions disabled while wizard running |

---

## 5. Idempotency (AI.173)

Optional `Idempotency-Key` → SHA-256 hash stored in `campaign.campaign_metadata.action_replay_cache` (raw key never stored).

Same campaign + action + state fingerprint → replay cached `CampaignActionResult`.  
State changed → `409 idempotency_state_conflict`.

---

## 6. UI (AI.172)

Campaign action center panel:

- Primary action button from `primary_action`
- Secondary enabled actions
- Confirmation modal when `confirmation_required`
- Refresh control center after execute

---

## 7. Regression

```bash
uv run pytest tests/test_phase_ai_174_campaign_action_center_regression.py -q
```

Includes full **dental_clinic_lead_gen** wizard via action buttons to queued dry-run job.

---

## 8. Files

| Area | Path |
|------|------|
| Roadmap | `docs/phase_ai_166_campaign_action_center_roadmap.md` |
| Contracts | `app/schemas/contracts.py` |
| Builder | `app/services/campaign_action_builder.py` |
| Executor | `app/services/campaign_action_executor_service.py` |
| Idempotency | `app/services/campaign_action_idempotency.py` |
| API | `app/api/routes/business_campaigns.py` |
| UI | `web/src/components/agent-chat/business-campaigns-panel.tsx` |
| Tests | `tests/test_phase_ai_174_campaign_action_center_regression.py` |

---

## 9. Status

**READY** for action center freeze.
