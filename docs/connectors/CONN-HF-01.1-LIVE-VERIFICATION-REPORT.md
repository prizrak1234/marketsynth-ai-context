# CONN-HF-01.1L — Live MCP Verification Report

**Work package:** CONN-HF-01.1L  
**Status:** `sandbox_verification_required` — live handshake **not executed**  
**Endpoint:** `https://mcp.higgsfield.ai/mcp`

---

## Owner gates (mandatory)

| Gate | Status | Owner action |
|------|--------|--------------|
| B3 Temporary token + permission for initialize/tools/list | **STOP** | Provide env-only token; approve network |
| B7 One paid image render | **STOP** | Explicit approval + `accept_unknown_cost` |

Cursor must **not** proceed past these gates without owner confirmation.

---

## Preflight (code — complete)

| Check | Result |
|-------|--------|
| Handshake script no token in stdout | ✓ dry test |
| Snapshots redact secrets | ✓ `sanitize_snapshot_payload` |
| Bounded timeout | ✓ `higgsfield_mcp_timeout_seconds` |
| No tools/call in handshake | ✓ |
| Customer live blocked | ✓ `409 connector_not_production_ready` |
| Video disabled | ✓ |
| No automatic tool mapping | ✓ manual review required |

Run preflight tests:

```bash
uv run pytest tests/test_conn_hf_handshake_preflight.py -q
```

---

## B4 — Initialize + tools/list

| Field | Value |
|-------|-------|
| Executed | **no** — awaiting owner token |
| Protocol version | _pending_ |
| Tool count | _pending_ |
| Post-handshake status | `tools_discovered_pending_mapping` |

**Owner command:**

```bash
HIGGSFIELD_MCP_ENABLED=true \
HIGGSFIELD_OAUTH_ACCESS_TOKEN="<temporary-token>" \
uv run python scripts/higgsfield_mcp_sandbox_handshake.py
```

Unset token after run. Do not commit snapshots containing secrets.

---

## B5–B6 — Manual tool audit + mapping

See [HIGGSFIELD-MCP-MANUAL-TOOL-REVIEW.md](./HIGGSFIELD-MCP-MANUAL-TOOL-REVIEW.md).

`operation_mapping.json` must remain manual until owner approves each binding.

---

## B9–B12 — Sandbox image render

See [HIGGSFIELD-IMAGE-SANDBOX-RESULT.md](./HIGGSFIELD-IMAGE-SANDBOX-RESULT.md) — **pending**.

---

## Freeze

See [HIGGSFIELD-SANDBOX-FREEZE-AUDIT.md](./HIGGSFIELD-SANDBOX-FREEZE-AUDIT.md).

`freeze_manifest.status` must become `sandbox_verified` only after all 14 factual criteria in CONN-HF-01.1 TZ.

**Not allowed:** `production_ready`, `active`, `tenant_enabled`, `globally_enabled`.

---

## Remaining blockers for production

- Real MCP handshake
- Manual image tool mapping
- One owner-approved image call
- Billing visibility documented
- CONN-HF-01.2 tenant credential binding (separate slice)
