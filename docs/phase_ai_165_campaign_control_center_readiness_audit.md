# Phase AI.165 — Campaign Control Center Readiness Audit

**Date:** 2026-06-03  
**Scope:** Campaign command panel — timeline, health, next action (AI.156–AI.164).

---

## 1. Product intent

Campaign container (AI.146–AI.155) tells users **what exists**. Control Center tells them **what to do next** — without new agents or hidden automation.

---

## 2. API

```
GET /projects/{id}/business-campaigns/{campaign_id}/control-center

GET /projects/{id}/business-campaigns?view=control&health=&next_action_type=&failed_only=&completed_only=
GET /projects/{id}/business-campaigns/search?view=control&...
```

Response: `CampaignControlCenter`

| Field | Purpose |
|-------|---------|
| `health` | `healthy` · `waiting_for_user` · `blocked` · `failed` · `completed` + `progress_percent` |
| `next_action` | Recommendation only — maps to existing manual APIs |
| `timeline` | Read-only events (wizard → job) |
| `metrics` | Aggregate counts (unchanged from AI.152) |
| `resource_ids` | Deep-link artifact ids |
| `safe_warnings` | Non-blocking guidance |
| `recovery_hint` | Failed object + suggested recovery (no auto-fix) |

---

## 3. Next action engine (AI.158)

Service: `app/services/campaign_control_center_service.py`

Actions (recommendation only):

- `attach_scenario`, `start_wizard`, `advance_wizard`
- `approve_plan`, `start_execution`, `execute_next_specialist`
- `approve_copywriter_output`, `create_content_asset`, `approve_asset`
- `create_media_brief`, `approve_media_brief`, `create_publication_package`
- `schedule_or_dry_run`

---

## 4. Timeline (AI.157)

Read-only `CampaignTimelineEvent` entries from linked:

- Wizard steps, plans, execution runs, specialist outputs
- Content assets, media briefs, publication packages/jobs

No new mutations from timeline.

---

## 5. UI (AI.161)

Marketing plans panel → **Campaign control center**:

- Progress bar
- Next action card (type + description)
- Timeline list
- Metric counts + artifact id links
- Health filter on campaign list
- **Start wizard** button only where explicit — no hidden advance

---

## 6. Invariants (freeze)

| Invariant | Enforcement |
|-----------|-------------|
| Read-only control center | GET only — no POST on control-center |
| No auto-execution | Next action is text + resource ids |
| No auto-recovery | `recovery_hint` is suggestion only |
| Frozen pipeline unchanged | Reuses existing status enums and repos |
| Legacy flows preserved | Control center observes tags, does not replace wizard |

---

## 7. Regression

```bash
uv run pytest tests/test_phase_ai_164_campaign_control_center_regression.py -q
```

Covers: `start_wizard`, `attach_scenario`, `advance_wizard`, completed pipeline, list filters, read-only guarantee.

---

## 8. Files

| Area | Path |
|------|------|
| Roadmap | `docs/phase_ai_156_campaign_control_center_roadmap.md` |
| Contracts | `app/schemas/contracts.py` |
| Service | `app/services/campaign_control_center_service.py` |
| API | `app/api/routes/business_campaigns.py` |
| UI | `web/src/components/agent-chat/business-campaigns-panel.tsx` |
| Tests | `tests/test_phase_ai_164_campaign_control_center_regression.py` |

---

## 9. Status

**READY** for control center freeze. Next value: cross-campaign portfolio views or scheduling UX — not new specialists.
