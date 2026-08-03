# Higgsfield Media Operation Mapping

**Status:** `sandbox_verification_required`

## Two-layer model

```
Marketsynth canonical operation          Provider MCP tool (from tools/list)
─────────────────────────────           ───────────────────────────────────
media.image.generate          ──map──►  (TBD — not guessed)
media.video.generate          ──map──►  unsupported in CONN-HF-01.1
media.job.get_status          ──map──►  (TBD)
media.asset.fetch             ──map──►  (TBD — may not exist as separate tool)
```

## Mapping record shape

```json
{
  "media.image.generate": {
    "provider_tool_name": "<from tools/list>",
    "tool_schema_hash": "<sha256>",
    "verified_at": "<iso8601>",
    "server_version": "<optional>",
    "enabled": true
  }
}
```

## Rules

- No automatic fuzzy matching in production path
- Unmapped canonical operation → `provider_tool_not_mapped` (fail closed)
- Unsupported operation → explicit `unsupported` status in mapping file
- Deprecated guessed IDs (`higgsfield.render_image`, …) are not canonical

## Source of truth

`packages/connectors/higgsfield/sandbox/operation_mapping.json`
