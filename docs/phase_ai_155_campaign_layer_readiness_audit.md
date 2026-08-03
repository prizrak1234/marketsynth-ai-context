# Phase AI.155 — Business Campaign Layer Readiness Audit

**Date:** 2026-06-03  
**Scope:** Business Operating System campaign container (AI.146–AI.154).

---

## 1. Product intent

Users work with a **business campaign** (goal + scenario + linked artifacts), not isolated plans or assets. Campaign is an **orchestration container** — not an executor or publisher.

---

## 2. Entity: `Campaign`

| Field | Notes |
|-------|--------|
| `id`, `owner_id`, `project_id` | Standard ownership |
| `name`, `goal` | Business framing |
| `scenario_id` | Optional link to marketing scenario template |
| `status` | `draft` · `active` · `paused` · `completed` · `archived` |
| `metadata` | JSON bag for future extensions |

Contract: `Campaign`, `CampaignStatus`, `CampaignMetrics`, `CampaignDashboard` in `app/schemas/contracts.py`  
Persistence: `campaigns` table (`CampaignTable`)

> **Route note:** Phase 9 legacy `MarketingCampaign` remains at `/projects/{id}/campaigns`. BOS `Campaign` uses `/projects/{id}/business-campaigns` to avoid collision.

---

## 3. API (AI.148–AI.153)

```
POST   /projects/{id}/business-campaigns
GET    /projects/{id}/business-campaigns
GET    /projects/{id}/business-campaigns/search?q=&scenario_id=&status=
GET    /projects/{id}/business-campaigns/{campaign_id}
PATCH  /projects/{id}/business-campaigns/{campaign_id}
GET    /projects/{id}/business-campaigns/{campaign_id}/dashboard
GET    /projects/{id}/business-campaigns/{campaign_id}/metrics
POST   /projects/{id}/business-campaigns/{campaign_id}/scenario-wizard-runs
```

No execution, publish, or pipeline mutation endpoints on campaign routes.

---

## 4. Flow: Campaign → Scenario → Plan → Execution (AI.149)

| Path | Behaviour |
|------|-----------|
| **New** | `POST .../business-campaigns/{id}/scenario-wizard-runs` → wizard with `source_campaign_id` |
| **Legacy** | `POST .../scenario-wizard-runs` with `{ scenario_id }` — unchanged |

Wizard tags:

- `MarketingPlan.project_context.source_campaign_id`
- `ContentAsset.asset_metadata.source_campaign_id`
- `ScenarioWizardRun.source_campaign_id` (FK)

---

## 5. Provenance (AI.151)

`GET .../provenance/content-production/{job_id}` includes:

- `source_wizard_run_id` (existing)
- `source_campaign_id` (new)

---

## 6. Metrics (AI.152)

Campaign-level counts (no publication analytics):

- `plans_total`, `outputs_total`, `assets_total`, `media_total`, `packages_total`, `jobs_total`, `wizard_runs_total`

Aggregated in `CampaignLayerService.compute_metrics` from tagged plans and downstream artifact chains.

---

## 7. Search (AI.153)

SQL-only via `CampaignRepository.search`:

- campaign name / goal (ILIKE)
- `scenario_id`
- `status`

---

## 8. UI (AI.150)

Marketing plans panel → **Business campaigns** section:

- Create campaign (name, goal, scenario)
- Campaign selector + dashboard card: goal, scenario, plan/execution status, content/media/publication counts
- **Start wizard** from campaign (requires `scenario_id`)

---

## 9. Invariants (freeze)

| Invariant | Enforcement |
|-----------|-------------|
| Campaign does not change frozen pipeline | No edits to AI.39 six-chain or v2 deps |
| Campaign does not create execution | No execution endpoints on campaign routes |
| Campaign does not publish | No publish/execute calls from campaign layer |
| Campaign = orchestration container | CRUD + dashboard + wizard entry + provenance tags only |
| Legacy flows preserved | Direct scenario plan + standalone wizard unchanged |

---

## 10. Regression

```bash
uv run pytest tests/test_phase_ai_154_campaign_layer_regression.py -q
```

Covers: create, scenario attach, campaign wizard, provenance, metrics, search, legacy wizard.

---

## 11. Files touched

| Area | Path |
|------|------|
| Roadmap | `docs/phase_ai_146_campaign_layer_roadmap.md` |
| Contract | `app/schemas/contracts.py` |
| DB | `app/db/models/campaign.py`, migration `20260603_0024_*` |
| Service | `app/services/campaign_layer_service.py` |
| API | `app/api/routes/business_campaigns.py` |
| Wizard link | `app/services/scenario_wizard_service.py` |
| Provenance | `app/demo/provenance_helpers.py`, `app/schemas/demo_flow.py` |
| UI | `web/src/components/agent-chat/business-campaigns-panel.tsx` |
| Tests | `tests/test_phase_ai_154_campaign_layer_regression.py` |

---

## 12. Status

**READY** for campaign-layer freeze. Next value jumps should build on campaign dashboards and cross-artifact workflows — not new specialist agents.
