# Higgsfield MCP Integration

**Phase:** CONN-HF-01 / CONN-HF-01.1 / **CONN-HF-01.1L** (live verification)  
**Status:** `adapter_candidate` / `sandbox_verification_required`  
**Live report:** [CONN-HF-01.1-LIVE-VERIFICATION-REPORT.md](../connectors/CONN-HF-01.1-LIVE-VERIFICATION-REPORT.md)  
**Architecture layer:** Media Renderer → `connector.higgsfield` → Higgsfield MCP

> **Not accepted:** Higgsfield MCP is **not** connected to Marketsynth production or CWF.

## Principle

Higgsfield is an **executor**, not a decision-maker. Upstream Skills produce a complete `MediaRenderSpec`; the connector forwards it to MCP without changing business meaning.

```
Presentation Architecture
        ↓
Visual Brief (future skill)
        ↓
Image Generation Spec (future skill)
        ↓
Media Renderer (abstraction)
        ↓
connector.higgsfield (sandbox verification required)
        ↓
Higgsfield MCP (verified tools only)
```

## Canonical operations (Marketsynth internal)

| Operation | Role |
|-----------|------|
| `media.image.generate` | Execute image render from spec |
| `media.video.generate` | Execute video render (gated + disabled in 01.1) |
| `media.job.get_status` | Poll async job |
| `media.asset.fetch` | Fetch completed artifact |

Provider MCP tool names come from sandbox `tools/list` capture — see [HIGGSFIELD-MEDIA-OPERATION-MAPPING.md](../connectors/HIGGSFIELD-MEDIA-OPERATION-MAPPING.md).

## What Higgsfield must NOT do

- Choose style, offer, or positioning
- Modify copy or invent characters
- Publish results
- Run without complete upstream spec + approval gates
- Run on dry-run or customer API without sandbox verification

## Configuration

```env
HIGGSFIELD_MCP_ENABLED=true
HIGGSFIELD_MCP_ENDPOINT=https://mcp.higgsfield.ai/mcp
HIGGSFIELD_OAUTH_ACCESS_TOKEN=<sandbox bearer — not stored in DB>
HIGGSFIELD_VIDEO_RENDER_ENABLED=false
HIGGSFIELD_OWNER_SANDBOX_ENABLED=false
```

Live paid calls additionally require:

- `explicit_confirmation=true`
- `accept_unknown_cost=true` (until cost visibility verified)
- `approval_reference` when spec requires approval
- Owner/admin role + sandbox verified manifest

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/projects/{id}/media-renderer/readiness` | Connector + sandbox status |
| POST | `/projects/{id}/media-renderer/render` | `dry_run=true` → plan only; live → owner sandbox only |
| GET | `/projects/{id}/media-renderer/jobs/{job_id}/status` | Poll job (live gated) |
| GET | `/projects/{id}/media-renderer/jobs/{job_id}/download` | Download metadata (live gated) |

### Dry-run example

```json
{
  "spec": {
    "asset_type": "image",
    "style": "minimal",
    "aspect_ratio": "16:9",
    "brand": "Marketsynth",
    "prompt": "...",
    "negative_prompt": "...",
    "references": [],
    "approval_required": true
  },
  "upstream_skill_id": "ms.skill.presentation_architecture",
  "dry_run": true
}
```

Response: `status=planned_only`, no MCP traffic.

## Swappable renderer

The `MediaRendererBackend` protocol in `app/media_generation/media_renderer.py` allows future executors. Higgsfield is the first MCP-derived candidate — not production-approved.

## Related docs

- [CONN-HF-01.1 sandbox verification](../connectors/CONN-HF-01.1-HIGGSFIELD-MCP-SANDBOX-VERIFICATION.md)
- [Authentication findings](../connectors/HIGGSFIELD-AUTHENTICATION-FINDINGS.md)
- [Risk register](../connectors/HIGGSFIELD-RISK-REGISTER.md)

## Next slices

1. **CONN-HF-01.1** — sandbox handshake + mapping (this phase)
2. **CONN-HF-01.2** — tenant credential binding + production image render
3. **PRODUCT-MEDIA-01** — Visual Brief → spec → approval → render → asset review
