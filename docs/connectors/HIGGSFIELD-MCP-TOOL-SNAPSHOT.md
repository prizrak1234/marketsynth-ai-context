# Higgsfield MCP Tool Snapshot

**Status:** `sandbox_verification_required` (live handshake pending)  
**Live verification:** [CONN-HF-01.1-LIVE-VERIFICATION-REPORT.md](./CONN-HF-01.1-LIVE-VERIFICATION-REPORT.md)  
**After handshake:** status becomes `tools_discovered_pending_mapping` until manual mapping approved

## Current state

No live `tools/list` capture committed yet. Placeholder snapshot:

- `packages/connectors/higgsfield/sandbox/tools_snapshot.json` — empty tools array
- `tool_schema_hashes.json` — pending capture

## After owner handshake

Record for each discovered tool:

- `name` (provider truth — not guessed)
- `description`
- `inputSchema` (hashed via SHA-256 canonical JSON)
- Normalized output hints if present in schema/docs

## Rules

- Do not commit access tokens
- Do not commit generated media binaries
- Redact signed URL query parameters in stored metadata

## Schema drift

Live calls fail closed when runtime schema hash ≠ frozen `tool_schema_hashes.json` entry.
