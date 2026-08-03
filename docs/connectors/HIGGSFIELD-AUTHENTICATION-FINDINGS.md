# Higgsfield Authentication Findings

**Status:** `sandbox_verification_required`  
**Phase:** CONN-HF-01.1

## What is proven today

| Claim | Evidence |
|-------|----------|
| Official MCP endpoint exists | `https://mcp.higgsfield.ai/mcp` (public) |
| Cursor plugin can connect | User environment — not Marketsynth backend |
| Marketsynth backend S2S credential | **Not proven** |

## What is not assumed

- `HIGGSFIELD_OAUTH_ACCESS_TOKEN` as production auth — env bearer is sandbox-only probe
- Browser OAuth session from Cursor plugin ≠ backend trust context
- Guessed tool names (`higgsfield.render_image`, etc.) — **removed from authoritative code**

## Expected verification steps

1. `initialize` — protocol version negotiation
2. HTTP 401/403 or MCP auth error inspection
3. Authenticated retry with owner-supplied bearer (in-memory only)
4. `tools/list` success/failure recording in `authentication_findings.json`

## Storage policy

- Tokens: process memory during sandbox only
- Never: DB, logs, git, snapshot JSON

## Production credential binding

Deferred to **CONN-HF-01.2**.
