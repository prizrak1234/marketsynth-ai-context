# Phase AI.55 — Media production readiness audit

**Status:** Production freeze (AI.50–AI.54).  
**Prerequisite:** [AI.45 content production freeze](phase_ai_45_content_production_readiness_audit.md).

## Canonical product flow (frozen)

```
ContentAsset (approved)
  → Create Media Brief (explicit)
  → MediaBrief draft
  → Submit for Review → Approve
  → Create Media Asset (explicit, per type)
  → MediaAsset draft (generation_provider = placeholder)
```

**Not in this flow:** Flux, OpenAI Images, DALL-E, Midjourney, Canva, HeyGen, video render APIs, outbound publish.

---

## Phase inventory

| Phase | Deliverable | API / persistence |
|-------|-------------|-------------------|
| **AI.50** | `MediaBrief` | Table `media_briefs` |
| **AI.51** | Asset → brief | `POST .../content-assets/{id}/create-media-brief`; `source_content_asset_id` |
| **AI.52** | Brief workflow | `draft → review → approved \| archived`; audit timestamps |
| **AI.53** | `MediaAsset` | Table `media_assets`; types image / video / carousel |
| **AI.54** | Brief → placeholder | `POST .../media-briefs/{id}/create-media-asset`; `source_media_brief_id` |
| **AI.55** | **Freeze** | This doc + `test_phase_ai_55_media_production_freeze_invariants.py` |

---

## MediaBrief transitions

| From | To | Endpoint |
|------|-----|----------|
| draft | review | `POST .../submit-review` |
| review | approved | `POST .../approve` |
| review | archived | `POST .../archive` |
| approved | archived | `POST .../archive` |

One brief per `content_asset_id` (duplicate → 409).

---

## MediaAsset rules

- Created only from **approved** brief
- One asset per `media_brief_id` + `media_type` (duplicate → 409)
- `generation_provider = placeholder` until AI.56+
- `generation_metadata.placeholder = true`

---

## Architecture stack (frozen layers)

```
AI.19–26  Chat Layer           ✅
AI.27–39  Marketing Pipeline   ✅
AI.40–45  Content Production   ✅
AI.50–55  Media Production     ✅  (foundation only)
AI.56–59  Media Generation     ✅  [audit](phase_ai_59_media_generation_readiness_audit.md)
AI.60+    Publishing           (later)
```

---

## Regression

```bash
uv run pytest \
  tests/test_phase_ai_50_media_brief_foundation.py \
  tests/test_phase_ai_51_content_asset_media_brief_conversion.py \
  tests/test_phase_ai_52_media_brief_review_workflow.py \
  tests/test_phase_ai_53_media_asset_foundation.py \
  tests/test_phase_ai_54_media_brief_media_asset_conversion.py \
  tests/test_phase_ai_55_media_production_freeze_invariants.py \
  tests/test_phase_ai_56_media_generation_abstraction.py \
  tests/test_phase_ai_57_openai_images_provider_gated.py \
  tests/test_phase_ai_58_media_asset_storage_boundary.py \
  tests/test_phase_ai_59_media_generation_freeze_invariants.py -q
```

Full stack (marketing + content + media foundation + generation):

```bash
uv run pytest \
  tests/test_phase_ai_39_marketing_pipeline_freeze_invariants.py \
  tests/test_phase_ai_45_content_production_freeze_invariants.py \
  tests/test_phase_ai_55_media_production_freeze_invariants.py -q
```
