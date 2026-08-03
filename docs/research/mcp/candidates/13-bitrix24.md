# MCP Audit — Bitrix24 MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-013` |
| **Connector name** | Bitrix24 MCP |
| **MCP server role (proposed)** | crm_mcp |
| **Provider / vendor** | Bitrix24 / community |
| **Documentation URL** | **Unknown** |
| **License** | Commercial |
| **Hosting model** | Vendor/self-host CRM |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Bitrix24 CRM integration.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Lead handoff |
| User-visible result enabled | RU/CIS enterprise leads — later. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Write CRM — **Unknown**

---

## 4. Authentication

OAuth/webhook

---

## 5. Trust boundary

PII

---

## 6. Controls (required gateway)

Gated writes

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Complex on-prem variants

---

## 8. Security

High

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
| **Rationale** | Same as amoCRM — defer native adapter path. |
| **Required gateway controls** | Native adapter |
| **Defer unblock condition** | CRM RFC |
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

- bitrix24 REST docs — general
