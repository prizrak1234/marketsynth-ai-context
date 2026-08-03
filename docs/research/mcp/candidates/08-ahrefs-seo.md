# MCP Audit — Ahrefs SEO MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-008` |
| **Connector name** | Ahrefs SEO MCP |
| **MCP server role (proposed)** | seo_data_mcp |
| **Provider / vendor** | Ahrefs |
| **Documentation URL** | **Unknown** official MCP — search registry |
| **License** | Commercial API |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

SEO metrics, backlinks, keyword data.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Research / SEO |
| User-visible result enabled | Supports SEO audit skill — secondary. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

**Unknown** — Requires verification if official MCP exists

---

## 4. Authentication

API key / OAuth — commercial plan

---

## 5. Trust boundary

Vendor API; cost per call

---

## 6. Controls (required gateway)

Budget caps; read-only tools only

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Expensive API — tenant budgets mandatory

---

## 8. Security

Low write risk if read-only

---

## 9. Comparison to existing connectors

XmlRiver different intent (SERP URLs vs SEO metrics)

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 1 | |
| Security / trust | 1 | |
| Operational cost | 0 | |
| Duplicate of existing | 2 | |

**Total:** 6 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Official MCP existence and pricing not verified in this audit. |
| **Required gateway controls** | Native Ahrefs adapter preferred over random MCP bundle |
| **Defer unblock condition** | Verify official server + pricing |
| **Conditions for pilot** | Read-only keyword lookup |
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

- ahrefs.com — **Not verified** MCP endpoint
