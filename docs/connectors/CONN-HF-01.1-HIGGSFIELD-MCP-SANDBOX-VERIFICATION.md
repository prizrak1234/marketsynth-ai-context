# CONN-HF-01.1 — Higgsfield MCP Sandbox Contract Verification

**Phase:** CONN-HF-01.1  
**Status:** `adapter_candidate` / `sandbox_verification_required`  
**Objective:** Verify real Higgsfield MCP protocol before any customer live rendering.

## Hard boundaries

| Forbidden | Allowed |
|-----------|---------|
| Customer-facing live generation | Owner-triggered sandbox handshake |
| CWF / Content / Publication integration | `initialize`, `tools/list` |
| Policy bypass on dry-run | Static schema capture |
| Guessed MCP tool names as canonical | One owner-approved image test (after mapping) |
| OAuth token in DB/logs/repo | Sanitized sandbox artifacts |

## Dry-run model (fixed)

```
dry_run=true
  → validate MediaRenderSpec locally
  → build MediaRenderPlan
  → status=planned_only
  → zero MCP network traffic

dry_run=false
  → explicit_confirmation + approval + billing gates
  → owner/admin sandbox gate
  → sandbox_verified manifest required
  → adapter invoked only after policy ALLOW
```

**Invariant:** No dry-run request can produce MCP network traffic.

## Canonical operations (Marketsynth internal)

| Operation | Role |
|-----------|------|
| `media.image.generate` | Image render |
| `media.video.generate` | Video render (disabled in CONN-HF-01.1) |
| `media.job.get_status` | Async job poll |
| `media.asset.fetch` | Result fetch |

Provider MCP tool names are discovered via `tools/list` and mapped in `packages/connectors/higgsfield/sandbox/operation_mapping.json`.

## Sandbox artifacts

```
packages/connectors/higgsfield/sandbox/
├── server_capabilities.json
├── tools_snapshot.json
├── tool_schema_hashes.json
├── operation_mapping.json
├── authentication_findings.json
└── freeze_manifest.json
```

Snapshot status must remain `sandbox_verification_required` until owner accepts mapping + one image test.

## Owner sandbox handshake

```bash
HIGGSFIELD_MCP_ENABLED=true \
HIGGSFIELD_OAUTH_ACCESS_TOKEN=... \
uv run python scripts/higgsfield_mcp_sandbox_handshake.py
```

Does not print tokens. Writes sanitized artifacts only.

## Customer API boundary

`POST /projects/{id}/media-renderer/render`:

- `dry_run=true` → always returns `planned_only` (no MCP)
- `dry_run=false` → `409 connector_not_production_ready` for ordinary users

Live sandbox calls require `UserRole.OWNER|ADMIN` + `HIGGSFIELD_OWNER_SANDBOX_ENABLED=true` + `freeze_manifest.status=sandbox_verified`.

## Definition of done

- [x] Dry-run policy bypass removed
- [x] Dry-run creates zero MCP traffic
- [ ] Actual authentication flow documented (requires real handshake)
- [ ] Actual tools/list captured (requires owner token)
- [ ] Canonical→provider mapping verified
- [ ] One owner-approved image sandbox call
- [x] Video remains disabled
- [x] Customer live calls blocked
- [x] Tests pass

## Next slice

**CONN-HF-01.2** — Tenant Credential Binding + Production Image Render (after sandbox acceptance).
