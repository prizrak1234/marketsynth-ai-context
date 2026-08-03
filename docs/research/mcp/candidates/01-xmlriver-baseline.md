# MCP Audit — XmlRiver Search (baseline)

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-001` |
| **Connector name** | XmlRiver Search (baseline) |
| **MCP server role (proposed)** | search_mcp |
| **Provider / vendor** | XmlRiver |
| **Documentation URL** | http://xmlriver.com/ (API); internal adapter `app/business_tools/providers/xmlriver_search.py` |
| **License** | Commercial API — **Requires legal review** for redistribution; adapter code internal |
| **Hosting model** | Vendor-hosted HTTP API |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Read-only web search returning URL candidates for research operators — already partially integrated.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Research / Evidence (source candidates) |
| User-visible result enabled | Core research input for BIV and source collection. |
| Required for first paying customer? | yes |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

| Tool | Read/Write | Description | Allowlist |
|------|------------|-------------|----------|
| `search` (native adapter) | Read | XML search API → SourceCandidate list | yes — registered in `app/mcp/registry.py` |

---

## 4. Authentication

API key + user ID via `app/core/config.py` (`xmlriver_user_id`, `xmlriver_api_key`). Tenant scoping: **Requires technical validation** — currently deployment-level credentials.

---

## 5. Trust boundary

Returns candidates only (`is_evidence=False`). Audit via research/MCP audit patterns. No write tools.

---

## 6. Controls (required gateway)

- Tool allowlist: `search` only
- Read-only flag true
- Timeout 25s in adapter
- Rate limits: **Unknown** — vendor docs
- Budget: per-tenant caps **Requires RFC**

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Existing baseline. Failure: BusinessToolError surfaced to operator. Fallback: manual URL entry.

---

## 8. Security

Prompt injection via SERP snippets — sanitize before LLM. Secret in env only. Supply chain: direct HTTPS to xmlriver.com.

---

## 9. Comparison to existing connectors

| Existing | Overlap | Keep? |
|----------|---------|-------|
| Native XmlRiverSearchTool | Same | **Yes** — document baseline |
| Firecrawl | Complementary fetch | Both |
| Playwright | Different — browser automation | Hybrid routing |

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 2 | |
| Golden path fit | 2 | |
| Evidence integrity | 2 | |
| Security / trust | 2 | |
| Operational cost | 1 | |
| Duplicate of existing | 0 | |

**Total:** 9 / 12

---

## 11. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | Already production-adjacent baseline; document and harden — do not expand tool surface without RFC. |
| **Required gateway controls** | Keep native adapter; optional MCP wrapper must preserve allowlist + audit parity. |
| **Defer unblock condition** | N/A |
| **Conditions for pilot** | N/A — already in use as business tool |
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

- `app/mcp/registry.py`
- `app/business_tools/providers/xmlriver_search.py`
- http://xmlriver.com/
