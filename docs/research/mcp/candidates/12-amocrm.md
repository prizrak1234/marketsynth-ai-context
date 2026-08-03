# MCP Audit — amoCRM MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-012` |
| **Connector name** | amoCRM MCP |
| **MCP server role (proposed)** | crm_mcp |
| **Provider / vendor** | amoCRM / community |
| **Documentation URL** | **Unknown** official MCP |
| **License** | Commercial API |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

CRM lead/deal read/write.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Lead handoff (MS-SKILL-025) |
| User-visible result enabled | Lead handoff after launch — P2 skill territory. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Contact/deal create — write

---

## 4. Authentication

OAuth/API key

---

## 5. Trust boundary

Customer PII

---

## 6. Controls (required gateway)

Write approval; field allowlist

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Per-tenant CRM credentials

---

## 8. Security

High PII

---

## 9. Comparison to existing connectors

No CRM connector today

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
| **Rationale** | Commercial value later; requires native adapter + DPA review. |
| **Required gateway controls** | Native CRM handoff service |
| **Defer unblock condition** | CRM slice + legal |
| **Conditions for pilot** | Read-only lead export first |
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

- amocrm.ru developers — **Not verified** MCP
