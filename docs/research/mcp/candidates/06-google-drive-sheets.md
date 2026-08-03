# MCP Audit — Google Drive / Sheets MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-006` |
| **Connector name** | Google Drive / Sheets MCP |
| **MCP server role (proposed)** | reporting_mcp |
| **Provider / vendor** | Various community + Google APIs |
| **Documentation URL** | **Unknown** single canonical MCP — evaluate per registry entry |
| **License** | Apache-2.0 / MIT typical — verify per server |
| **Hosting model** | Usually self-hosted OAuth |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Read/write Google Sheets and Drive files for reporting exports.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Reporting / delivery artifacts |
| User-visible result enabled | Nice-to-have delivery evidence — not CWF.1 critical path. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Typical: read_sheet, write_sheet, list_files — **Requires technical validation** per chosen server.

---

## 4. Authentication

OAuth 2.x Google — tenant token vault required.

---

## 5. Trust boundary

Google-hosted data; OAuth scope minimization critical.

---

## 6. Controls (required gateway)

Read-only export first; write gated; no auto-share public links.

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

OAuth refresh + quota management.

---

## 8. Security

Medium — OAuth scope creep, accidental PII export.

---

## 9. Comparison to existing connectors

No existing connector.

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 1 | |
| Security / trust | 1 | |
| Operational cost | 1 | |
| Duplicate of existing | 2 | |

**Total:** 7 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Not on CWF.1 critical path; multiple unvetted servers — pick after RFC scoping. |
| **Required gateway controls** | Google OAuth scoped adapter |
| **Defer unblock condition** | After reporting slice defined |
| **Conditions for pilot** | Read-only export pilot |
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

- Google API docs (general)
- MCP Registry search — **Not verified** single entry
