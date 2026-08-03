# MCP Audit — Playwright MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-004` |
| **Connector name** | Playwright MCP |
| **MCP server role (proposed)** | browser_automation_mcp |
| **Provider / vendor** | Microsoft (Playwright team) |
| **Documentation URL** | https://github.com/microsoft/playwright-mcp |
| **License** | Apache-2.0 (repo — **Requires verification** of package license) |
| **Hosting model** | Self-hosted stdio (`npx @playwright/mcp`) |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Browser automation via accessibility snapshots — navigate, click, type, etc.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Research (controlled browsing) |
| User-visible result enabled | Enables research on JS-heavy sites where Firecrawl scrape insufficient — not first-transaction required. |
| Required for first paying customer? | yes |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

| Tool examples (source-verified README) | Read/Write | Notes |
|-------------------------------------|------------|-------|
| `browser_navigate` | Write-ish | Navigation |
| `browser_click` | Write | DOM interaction |
| `browser_snapshot` | Read | A11y tree |
| + many interaction tools | Mixed | Full list in README |

**Not read-only** — high side-effect surface.

---

## 4. Authentication

Local process — no OAuth; runs with server OS privileges.

---

## 5. Trust boundary

Self-host possible. Data stays local unless navigates external URLs. Session persistence risk.

---

## 6. Controls (required gateway)

Strict tool allowlist (read-only subset if any); URL allowlist; no credential entry tools; sandbox network; human approval for any form submit.

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

High ops burden (Node, browser binaries). Token-heavy contexts vs CLI+Skills alternative per Microsoft README.

---

## 8. Security

High — prompt injection via page content, credential exfiltration if login allowed, RCE surface via browser.

---

## 9. Comparison to existing connectors

See browser-research-comparison.md

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 1 | |
| Evidence integrity | 1 | |
| Security / trust | 0 | |
| Operational cost | 0 | |
| Duplicate of existing | 1 | |

**Total:** 4 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Valuable for controlled research but write-capable browser automation fails default deny-by-default posture until benchmark + read-only profile proven. |
| **Required gateway controls** | If adopted: isolated runner + tool subset + URL policy |
| **Defer unblock condition** | browser-research-comparison benchmark + security review |
| **Conditions for pilot** | Dev sandbox only — never tenant production until RFC |
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

- https://github.com/microsoft/playwright-mcp
- README tool list
