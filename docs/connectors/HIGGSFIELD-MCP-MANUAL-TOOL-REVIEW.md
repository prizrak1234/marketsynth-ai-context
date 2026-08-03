# Higgsfield MCP — Manual Tool Review

**Work package:** CONN-HF-01.1L — B5  
**Status:** `pending_live_tools_list`

Fill this document **after** owner-approved handshake (`tools_snapshot.json` populated).  
**Do not auto-map tools.**

---

## Review rules

1. Map only verified semantic equivalents to canonical operations.
2. Record `tool_schema_hash` from `tool_schema_hashes.json`.
3. Video canonical op stays `verified_disabled` regardless of discovery.
4. Ambiguous tools → `ambiguous` or `unsupported`.
5. No mapping from tool name alone.

## Canonical operations

| Canonical operation | Purpose |
|--------------------|---------|
| `media.image.generate` | Image render |
| `media.video.generate` | Video (disabled) |
| `media.job.get_status` | Async poll |
| `media.asset.fetch` | Result fetch |

---

## Tool review table

_Copy one block per discovered tool after handshake._

### Tool: _&lt;provider_tool_name&gt;_

| Field | Value |
|-------|-------|
| provider_tool_name | |
| description | |
| input fields | |
| required fields | |
| output/result hints | |
| annotations | |
| billing sensitivity | low / medium / high / unknown |
| write/side-effect sensitivity | |
| publication sensitivity | |
| possible canonical operation | |
| reviewer decision | verified_enabled / verified_disabled / unsupported / ambiguous / deferred |
| tool_schema_hash | |
| limitations | |

---

## Mapping decision summary

After review, update `packages/connectors/higgsfield/sandbox/operation_mapping.json`:

```json
{
  "media.image.generate": {
    "provider_tool_name": "<actual-name>",
    "tool_schema_hash": "<sha256>",
    "mapping_status": "verified_enabled",
    "verified_at": "<ISO8601>",
    "limitations": [],
    "owner_review_required": false
  },
  "media.video.generate": {
    "mapping_status": "verified_disabled",
    "limitations": ["Video deferred — separate phase."]
  }
}
```

---

## Reviewer sign-off

| Field | Value |
|-------|-------|
| Reviewer | _owner_ |
| Date | |
| Image mapping approved | ☐ yes ☐ no |
| Notes | |
