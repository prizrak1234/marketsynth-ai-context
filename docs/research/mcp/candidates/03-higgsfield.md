# MCP Audit — Higgsfield MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-003` |
| **Connector name** | Higgsfield MCP |
| **MCP server role (proposed)** | media_generation_mcp (proposed) |
| **Provider / vendor** | Higgsfield |
| **Documentation URL** | https://higgsfield.ai/mcp |
| **License** | Proprietary service; MCP endpoint `https://mcp.higgsfield.ai/mcp` |
| **Hosting model** | Vendor-hosted remote MCP + OAuth |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Official vendor MCP for image/video generation across 30+ models with OAuth via Higgsfield account.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Optional Visuals → Content Factory |
| User-visible result enabled | Closes creative brief → asset loop for CWF optional visuals — high willingness-to-pay if gated. |
| Required for first paying customer? | no — optional visuals / Content Factory (P1 track) |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

| Tool | Read/Write | Description | Allowlist |
|------|------------|-------------|----------|
| **Unknown** — specific MCP tool names/schemas | Write (generation) | Image/video generation, history browse | **Requires technical validation** via MCP `tools/list` in sandbox |

Source-verified capabilities (marketing/docs): 4K images, ~15s video, reference images, consistent characters, async polling, credit billing.

---

## 4. Authentication

OAuth via Higgsfield account (no manual API key per official FAQ). Token storage: **Requires security review** — tenant-scoped vault required.

---

## 5. Trust boundary

Vendor-hosted; generation history on vendor side. Cross-tenant risk if shared OAuth. Data retention: **Unknown**.

---

## 6. Controls (required gateway)

**Mandatory before pilot:** model whitelist; per-tenant budget; generation count limits; prompt+model+cost+output lineage; human approval before paid/ repeat generation; block auto-publish.

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Adapter required in Connector Gateway. Async job polling. Fallback: manual asset upload.

---

## 8. Security

High — billing-sensitive writes, large egress, prompt injection via references. Deny-by-default tool allowlist.

---

## 9. Comparison to existing connectors

No existing media MCP in registry. Overlaps internal Video Studio / design services — route by policy.

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 2 | |
| Golden path fit | 1 | |
| Evidence integrity | 0 | |
| Security / trust | 0 | |
| Operational cost | 1 | |
| Duplicate of existing | 2 | |

**Total:** 6 / 12

---

## 11. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | Strong Content Factory candidate but **must not** connect directly to runtime — pilot only with gateway. |
| **Required gateway controls** | RFC-CONN-001 + RFC-SKILL for MS-SKILL-021; no CWF.1 behavior change in R0.1. |
| **Defer unblock condition** | Until tool schema verified + legal review on generated content rights |
| **Conditions for pilot** | Single-tenant sandbox with explicit_confirmation on each generation |
| **Owner sign-off** | pending |
| **RFC required** | Yes — RFC-CONN-001 |

---

## 12. Implementation gate

| Gate | Allowed? |
|------|----------|
| SKILL-R0.1 research only | ✅ |
| Production MCP connection | **Forbidden** until RFC-CONN-001 + owner approval |
| CWF.1 behavior change | **Forbidden** in this phase |

---

## Sources

- https://higgsfield.ai/mcp
- Official FAQ on page (OAuth, credits, models)
