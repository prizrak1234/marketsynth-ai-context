# MCP Audit — GitHub MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-007` |
| **Connector name** | GitHub MCP |
| **MCP server role (proposed)** | dev_integration_mcp |
| **Provider / vendor** | GitHub / community servers |
| **Documentation URL** | https://github.com/github/github-mcp-server (if official — **Requires verification**) |
| **License** | Verify per repo |
| **Hosting model** | Remote or self-hosted |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Repository issues, PRs, code search for agent dev workflows.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | none (internal dev) |
| User-visible result enabled | Low for paying customer CWF — internal engineering only. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

Issues, PRs, file read — mixed R/W.

---

## 4. Authentication

GitHub PAT or OAuth.

---

## 5. Trust boundary

Repo access = code leak risk.

---

## 6. Controls (required gateway)

Read-only for research; write forbidden in product runtime.

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Engineering tool — not customer-facing.

---

## 8. Security

Medium-high if write tools enabled.

---

## 9. Comparison to existing connectors

Out of product golden path.

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 0 | |
| Golden path fit | 0 | |
| Evidence integrity | 1 | |
| Security / trust | 1 | |
| Operational cost | 1 | |
| Duplicate of existing | 2 | |

**Total:** 5 / 12

---

## 11. Decision

| Decision | **Defer** |
|----------|----------------|
| **Rationale** | Engineering convenience — not CWF.1; keep out of tenant runtime. |
| **Required gateway controls** | Dev-only allowlist |
| **Defer unblock condition** | If internal agent needs — separate dev RFC |
| **Conditions for pilot** | None for product |
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

- MCP Registry / GitHub docs — **Requires verification**
