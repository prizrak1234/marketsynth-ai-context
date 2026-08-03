# Phase AI.146 — Business Campaign Layer Roadmap

**Date:** 2026-06-03  
**Goal:** Top-level **Campaign** container so users work with business outcomes, not isolated artifacts.

---

## Why Campaign

BotFazer already produces plans, content, media, and publication jobs. Businesses think in campaigns:

- Launch a dental clinic
- Promote a SaaS product
- Run a course launch

**Campaign** is the orchestration container — not an executor.

---

## What a Campaign unifies

| Linked artifact | Link mechanism |
|-----------------|----------------|
| MarketingPlan | `project_context.source_campaign_id` |
| ExecutionRun | via plan |
| Specialist outputs | via execution run |
| ContentAssets | `asset_metadata.source_campaign_id` |
| MediaAssets | via media brief / metadata |
| PublicationPackages | via content asset chain |
| PublicationPackageJobs | via package |
| ScenarioWizardRuns | `source_campaign_id` column |

---

## API registry (AI.148)

BOS Campaign registry (no execution):

```
POST   /projects/{id}/business-campaigns
GET    /projects/{id}/business-campaigns
GET    /projects/{id}/business-campaigns/{campaign_id}
PATCH  /projects/{id}/business-campaigns/{campaign_id}
GET    /projects/{id}/business-campaigns/{campaign_id}/dashboard
GET    /projects/{id}/business-campaigns/{campaign_id}/metrics
GET    /projects/{id}/business-campaigns/search
POST   /projects/{id}/business-campaigns/{campaign_id}/scenario-wizard-runs
```

> **Note:** Phase 9 legacy `MarketingCampaign` remains at `/projects/{id}/campaigns` (content-asset binding). BOS `Campaign` uses `/business-campaigns` to avoid route collision.

---

## Flows (AI.149)

**New (campaign-first):**

```
Campaign → Scenario → Wizard / Plan → Execution → Content → Media → Package → Job
```

**Legacy (unchanged):**

```
Scenario → Plan → …
Wizard without campaign_id → …
```

---

## Invariants (AI.155)

- Campaign does **not** change frozen pipeline
- Campaign does **not** auto-create execution runs
- Campaign does **not** publish
- Campaign = orchestration + provenance container only

---

## Deliverables map

| Phase | Item |
|-------|------|
| AI.147 | `Campaign` contract |
| AI.148 | Registry CRUD API |
| AI.149 | Wizard optional `campaign_id` |
| AI.150 | Dashboard UI |
| AI.151 | `source_campaign_id` provenance |
| AI.152 | Metrics endpoint |
| AI.153 | SQL search |
| AI.154 | Regression tests |
| AI.155 | Freeze audit + docs |
