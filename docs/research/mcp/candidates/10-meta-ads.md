# MCP Audit — Meta Ads MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-010` |
| **Connector name** | Meta Ads MCP |
| **MCP server role (proposed)** | ads_write_mcp |
| **Provider / vendor** | Meta / third-party |
| **Documentation URL** | **Unknown** |
| **License** | Commercial |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Facebook/Instagram ads management.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Launch (paid) |
| User-visible result enabled | Optional paid channel. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Write-heavy — **Unknown** specifics

---

## 4. Authentication

Meta OAuth

---

## 5. Trust boundary

Billing-sensitive

---

## 6. Controls (required gateway)

Same as Google Ads

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Policy/compliance burden

---

## 8. Security

High

---

## 9. Comparison to existing connectors

Draft creative skill only for now

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 0 | |
| Security / trust | 0 | |
| Operational cost | 0 | |
| Duplicate of existing | 2 | |

**Total:** 4 / 12

---

## 11. Decision

| Decision | **Reject** |
|----------|----------------|
| **Rationale** | Same hard reject as Google Ads MCP for ungated marketplace MCP pattern. |
| **Required gateway controls** | Native gated adapter only in future RFC |
| **Defer unblock condition** | Ad slice + legal review |
| **Conditions for pilot** | None |
| **Owner sign-off** | pending |
| **RFC required** | No |

---

## 12. Implementation gate

| Gate | Allowed? |
|------|----------|
| SKILL-R0.1 research only | ✅ |
| Production MCP connection | **Forbidden** until RFC-CONN-001 + owner approval |
| CWF.1 behavior change | **Forbidden** in this phase |

---

## Sources

- Meta Marketing API (general reference)
