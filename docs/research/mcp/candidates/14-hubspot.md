# MCP Audit — HubSpot MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-014` |
| **Connector name** | HubSpot MCP |
| **MCP server role (proposed)** | crm_mcp |
| **Provider / vendor** | HubSpot / community |
| **Documentation URL** | **Unknown** official MCP |
| **License** | Commercial |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

HubSpot CRM/marketing hub tools.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Lead handoff |
| User-visible result enabled | International CRM — later. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Mixed R/W — **Unknown**

---

## 4. Authentication

OAuth

---

## 5. Trust boundary

PII in CRM

---

## 6. Controls (required gateway)

Scoped OAuth; write approval

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

HubSpot rate limits

---

## 8. Security

Medium-high

---

## 9. Comparison to existing connectors

No existing

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 0 | |
| Security / trust | 1 | |
| Operational cost | 1 | |
| Duplicate of existing | 2 | |

**Total:** 6 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Defer until lead handoff slice prioritized. |
| **Required gateway controls** | Native adapter preferred |
| **Defer unblock condition** | CRM slice |
| **Conditions for pilot** | Read-only contact lookup |
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

- developers.hubspot.com — general
