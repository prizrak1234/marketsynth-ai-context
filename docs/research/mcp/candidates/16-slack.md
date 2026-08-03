# MCP Audit — Slack MCP

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-016` |
| **Connector name** | Slack MCP |
| **MCP server role (proposed)** | collaboration_mcp |
| **Provider / vendor** | Slack / community |
| **Documentation URL** | **Unknown** canonical MCP |
| **License** | Service terms |
| **Hosting model** | Vendor |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P1 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Post messages, read channels.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Notifications (optional) |
| User-visible result enabled | Ops notifications — not first paying workflow. |
| Required for first paying customer? | later / conditional |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

chat.postMessage — write

---

## 4. Authentication

OAuth bot token

---

## 5. Trust boundary

Message content leakage

---

## 6. Controls (required gateway)

Channel allowlist; no DMs; approval for customer-facing posts

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Slack rate limits

---

## 8. Security

Medium

---

## 9. Comparison to existing connectors

Telegram is CWF publish channel — Slack not in golden path

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
| **Rationale** | Not on CWF.1 path; avoid notification side channel before core accepted. |
| **Required gateway controls** | Read-only webhook/alerts adapter |
| **Defer unblock condition** | Ops alerting slice |
| **Conditions for pilot** | Internal admin alerts only |
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

- api.slack.com — general
