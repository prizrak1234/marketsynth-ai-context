# MCP Audit — Notion MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-015` |
| **Connector name** | Notion MCP |
| **MCP server role (proposed)** | collaboration_mcp |
| **Provider / vendor** | Notion (official integration likely) |
| **Documentation URL** | Notion MCP via registry — **Requires verification** |
| **License** | Service terms |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Read/write Notion pages and databases.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Delivery / documentation |
| User-visible result enabled | Internal delivery docs — not customer CWF core. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Page create/update — write

---

## 4. Authentication

OAuth Notion

---

## 5. Trust boundary

Customer content in Notion

---

## 6. Controls (required gateway)

Write approval; workspace scoping

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

OAuth per tenant

---

## 8. Security

Medium — exfiltration if over-scoped

---

## 9. Comparison to existing connectors

Marketsynth workspace is product — avoid parallel Notion SoT

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 0 | |
| Evidence integrity | 1 | |
| Security / trust | 1 | |
| Operational cost | 1 | |
| Duplicate of existing | 2 | |

**Total:** 6 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Risk of second system of record; defer unless export-only use case. |
| **Required gateway controls** | Export-only read adapter first |
| **Defer unblock condition** | Delivery export requirements defined |
| **Conditions for pilot** | Read-only export |
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

- notion.so developers — **Not verified** MCP tool list
