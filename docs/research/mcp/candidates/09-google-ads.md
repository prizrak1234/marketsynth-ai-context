# MCP Audit — Google Ads MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-009` |
| **Connector name** | Google Ads MCP |
| **MCP server role (proposed)** | ads_write_mcp |
| **Provider / vendor** | Google / third-party |
| **Documentation URL** | **Unknown** canonical MCP |
| **License** | Commercial |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Campaign/creative management for Google Ads.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Launch (paid) |
| User-visible result enabled | Post-launch spend surface — high risk. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Campaign create/update — **write-heavy**

---

## 4. Authentication

OAuth Google Ads account

---

## 5. Trust boundary

Billing-sensitive

---

## 6. Controls (required gateway)

Human approval per spend action; budget limits; deny auto-create

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Complex OAuth + policy compliance

---

## 8. Security

High — financial side effects

---

## 9. Comparison to existing connectors

marketingskills ad-creative is draft-only complement

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
| **Rationale** | Hard reject for SKILL-R0.1: uncontrolled spend/write surface conflicts with deny-by-default; defer native gated adapter later if commercial pull. |
| **Required gateway controls** | Future native adapter with RFC-CONN-001 |
| **Defer unblock condition** | Revisit as native adapter RFC after ad slice |
| **Conditions for pilot** | None now |
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

- Google Ads API docs (general)
