# MCP Audit — Firecrawl Fetch (baseline)

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-002` |
| **Connector name** | Firecrawl Fetch (baseline) |
| **MCP server role (proposed)** | web_fetch_mcp |
| **Provider / vendor** | Firecrawl |
| **Documentation URL** | https://docs.firecrawl.dev/ |
| **License** | Commercial API; OSS SDK license **Not verified** for self-host |
| **Hosting model** | Vendor-hosted API (`api.firecrawl.dev`) |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Read-only single-URL scrape to markdown excerpt — no recursive crawl in Marketsynth adapter.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Research / Evidence |
| User-visible result enabled | Fetches candidate page text for evidence admission pipeline. |
| Required for first paying customer? | yes |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

| Tool | Read/Write | Description | Allowlist |
|------|------------|-------------|----------|
| `fetch` / scrape (native) | Read | POST `/v1/scrape` single URL | yes — `firecrawl_fetch_v1` |

---

## 4. Authentication

Bearer API key via settings `firecrawl_api_key`.

---

## 5. Trust boundary

Candidate-only output; 2000 char excerpt cap. Warnings: no_recursive_crawl.

---

## 6. Controls (required gateway)

- Single URL only
- Read-only
- Timeout 45s
- Response size cap in adapter
- Human evidence admission required

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Failure → BusinessToolError. Cost: Firecrawl credit model — **Requires pricing validation**.

---

## 8. Security

High prompt injection from arbitrary URLs — block internal IPs **Requires security review** if not already.

---

## 9. Comparison to existing connectors

Primary managed extraction counterpart to Playwright.

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 2 | |
| Golden path fit | 2 | |
| Evidence integrity | 2 | |
| Security / trust | 1 | |
| Operational cost | 1 | |
| Duplicate of existing | 0 | |

**Total:** 8 / 12

---

## 11. Decision

| Decision | **Adapt** |
|----------|----------------|
| **Rationale** | Baseline managed fetch — keep narrow; benchmark vs Playwright for JS-heavy pages. |
| **Required gateway controls** | Native adapter preferred over third-party MCP server. |
| **Defer unblock condition** | N/A |
| **Conditions for pilot** | Active as business tool |
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

- `app/business_tools/providers/firecrawl_fetch.py`
- https://docs.firecrawl.dev/
