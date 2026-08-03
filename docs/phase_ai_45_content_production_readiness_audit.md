# Phase AI.45 — Content production readiness audit

**Status:** Production freeze (AI.40–AI.44).  
**Prerequisite:** [AI.39 marketing pipeline freeze](phase_ai_39_marketing_pipeline_readiness_audit.md).

## Canonical product flow (frozen)

```
Copywriter output (approved)
  → Create Content Asset (explicit)
  → ContentAsset draft
  → Submit for Review
  → ContentAsset review
  → Approve
  → ContentAsset approved
  → Create Publication Package (explicit, per channel)
  → PublicationPackage draft
```

**Not in this flow:** outbound publish, Telegram/Instagram/LinkedIn send, webhooks, scheduler auto-run, `PublicationJob` creation from content-production endpoints, media generation.

---

## Phase inventory

| Phase | Deliverable | API / persistence |
|-------|-------------|-------------------|
| **AI.40** | Copywriter → `ContentAsset` draft | `POST .../marketing-specialist-outputs/{id}/create-content-asset` |
| **AI.41** | Asset provenance | `source_marketing_plan_id`, `source_execution_run_id`, `source_specialist_output_id`, `source_specialist_type` |
| **AI.42** | Review workflow | `draft → review → approved \| archived`; `POST .../submit-review`, `/approve`, `/archive`; audit `submitted_for_review_at`, `approved_at` |
| **AI.43** | `PublicationPackage` | Table `publication_packages`; `GET .../publication-packages` |
| **AI.44** | Asset → package | `POST .../content-assets/{id}/create-publication-package`; `source_content_asset_id` |
| **AI.45** | **Freeze** | This doc + `test_phase_ai_45_content_production_freeze_invariants.py` |

---

## Asset status transitions (canonical)

| From | To | Endpoint |
|------|-----|----------|
| draft | review | `POST .../submit-review` |
| review | approved | `POST .../approve` |
| review | archived | `POST .../archive` |
| approved | archived | `POST .../archive` |

**Forbidden:** draft→approved, draft→archived, approved→review, archived→*.

---

## PublicationPackage (canonical)

- **Channels:** `telegram`, `instagram`, `linkedin`, `blog`
- **Statuses:** `draft`, `approved`, `archived` (entity only; no send)
- **One package per asset+channel** (duplicate → 409)

---

## Explicitly out of scope (until AI.50+ Media or AI.60+ Publishing)

- Telegram / Instagram / LinkedIn **publishing**
- Canva, Figma, HeyGen, MCP, web research
- LangGraph marketing execution, parallel specialists, scheduler
- Auto-create assets on Copywriter approve
- Auto-create packages on asset approve

**Next branch (done):** [AI.50–AI.55 Media Production foundation](phase_ai_55_media_production_readiness_audit.md). **Not** AI.60+ publishing before AI.56–59 generation discipline.

---

## Regression (content production suite)

```bash
uv run pytest \
  tests/test_phase_ai_40_copywriter_content_asset_conversion.py \
  tests/test_phase_ai_42_content_asset_review_workflow.py \
  tests/test_phase_ai_43_publication_package_foundation.py \
  tests/test_phase_ai_44_content_asset_publication_package_conversion.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py -q
```

Full stack (marketing + content):

```bash
uv run pytest \
  tests/test_phase_ai_27_marketing_orchestrator_skeleton.py \
  tests/test_phase_ai_28_marketing_plan_persistence.py \
  tests/test_phase_ai_29_marketing_plan_execution_skeleton.py \
  tests/test_phase_ai_30_marketing_specialist_output_skeleton.py \
  tests/test_phase_ai_31_strategist_specialist_execution.py \
  tests/test_phase_ai_32_researcher_specialist_execution.py \
  tests/test_phase_ai_33_content_planner_specialist_execution.py \
  tests/test_phase_ai_34_copywriter_specialist_execution.py \
  tests/test_phase_ai_35_critic_specialist_execution.py \
  tests/test_phase_ai_36_analyst_specialist_execution.py \
  tests/test_phase_ai_37_marketing_pipeline_validation.py \
  tests/test_phase_ai_38_marketing_run_completion.py \
  tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py \
  tests/test_phase_ai_40_copywriter_content_asset_conversion.py \
  tests/test_phase_ai_42_content_asset_review_workflow.py \
  tests/test_phase_ai_43_publication_package_foundation.py \
  tests/test_phase_ai_44_content_asset_publication_package_conversion.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py -q
```
