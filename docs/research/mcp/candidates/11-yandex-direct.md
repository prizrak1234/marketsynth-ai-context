# MCP Audit — Yandex Direct MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-011` |
| **Connector name** | Yandex Direct MCP |
| **MCP server role (proposed)** | ads_write_mcp |
| **Provider / vendor** | Yandex / third-party |
| **Documentation URL** | **Unknown** |
| **License** | Commercial |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Yandex advertising campaign tools.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Launch (RU market) |
| User-visible result enabled | Relevant for RU market customers — later. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Write-heavy — **Unknown**

---

## 4. Authentication

Yandex OAuth/API

---

## 5. Trust boundary

Billing-sensitive

---

## 6. Controls (required gateway)

Budget + approval gates

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Regional compliance

---

## 8. Security

High

---

## 9. Comparison to existing connectors

No existing adapter

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
| **Rationale** | Reject direct MCP install; future native adapter if RU ad slice prioritized. |
| **Required gateway controls** | RFC-CONN-001 native pattern |
| **Defer unblock condition** | RU commercial track + credentials |
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

- Yandex Direct API docs — **Not verified** MCP
