# Phase AI.59 — Media generation readiness audit

**Status:** Production freeze (AI.56–AI.58).  
**Prerequisite:** [AI.55 media production foundation](phase_ai_55_media_production_readiness_audit.md).

## Canonical flow (frozen)

```
ContentAsset (approved)
  → MediaBrief (approved)
  → Create MediaGenerationJob (explicit, provider=mock by default)
  → Start job (optional) → Complete mock / Execute (gated OpenAI)
  → MediaGenerationJob succeeded
  → MediaAsset draft + MediaAssetVersion (metadata/refs only)
```

**Not in this flow:** Flux, Canva, Figma, HeyGen, video generation, publishing, chat auto-generation, direct generation from ContentAsset.

---

## Phase inventory

| Phase | Deliverable |
|-------|-------------|
| **AI.56** | Provider abstraction + `MediaGenerationJob` + mock lifecycle |
| **AI.57** | OpenAI Images adapter (`MEDIA_GENERATION_ENABLED`, `OPENAI_IMAGES_ENABLED`) |
| **AI.58** | `MediaAsset` storage fields + `media_asset_versions` |
| **AI.59** | **Freeze** — this doc + invariant tests |

---

## Provider gates (default)

| Setting | Default |
|---------|---------|
| `MEDIA_GENERATION_ENABLED` | `false` |
| `OPENAI_IMAGES_ENABLED` | `false` |
| `OPENAI_IMAGES_MODEL` | `dall-e-3` (unused until enabled) |

| Provider | AI.56–AI.59 |
|----------|-------------|
| `mock` | Always allowed (deterministic, no HTTP) |
| `openai_images` | Requires both flags + API key |
| `flux` | **409** — not implemented |

---

## Storage rules (frozen)

- No base64 in DB
- No raw OpenAI/Flux payloads in `result_metadata`
- No API keys in metadata
- `storage_uri` may be `mock://…` placeholder only until binary storage lands post-AI.59
- OpenAI URL refs stored as `provider_asset_ref` only (short), not full response blob

---

## API surface

| Action | Endpoint |
|--------|----------|
| Create job | `POST .../media-briefs/{id}/generation-jobs` |
| Start | `POST .../media-generation-jobs/{id}/start` |
| Complete mock | `POST .../media-generation-jobs/{id}/complete-mock` |
| Execute provider | `POST .../media-generation-jobs/{id}/execute` |

---

## After AI.59

| Phase | Intent |
|-------|--------|
| **AI.56–AI.59** (this freeze) | Foundation only |
| **Future AI.56–59 roadmap** | Flux adapter, generation pipeline hardening |
| **AI.60–AI.65** | [Publishing foundation](phase_ai_65_publishing_foundation_readiness_audit.md) (done) |

---

## Regression

```bash
uv run pytest \
  tests/test_phase_ai_56_media_generation_abstraction.py \
  tests/test_phase_ai_57_openai_images_provider_gated.py \
  tests/test_phase_ai_58_media_asset_storage_boundary.py \
  tests/test_phase_ai_59_media_generation_freeze_invariants.py -q
```

With media production foundation:

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
