# MCP Audit — Telegram MCP (community userbot class)

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-005` |
| **Connector name** | Telegram MCP (community userbot class) |
| **MCP server role (proposed)** | publication_mcp (rejected path) |
| **Provider / vendor** | Community (e.g. mcp-telegram, jgalea/telegram-mcp) — **no official Telegram MCP** |
| **Documentation URL** | https://github.com/mcp-telegram/mcp-telegram (example); npm `mcp-telegram` |
| **License** | MIT (example repo — verify per implementation) |
| **Hosting model** | Self-hosted stdio or vendor cloud proxy (mcp-telegram.com) |
| **Reviewed by** | SKILL-R0.1 audit (Cursor) |
| **Review date** | 2026-07-23 |
| **Priority** | P0 |
| **Status** | ready_for_review |

---

## 1. One-line summary

Community MCP servers exposing full Telegram userbot/account tools (read/send/manage chats) — **not** Bot API publication adapter.

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened | Publish (CWF.1 terminal step) |
| User-visible result enabled | Would enable agent-driven Telegram actions — **conflicts** with frozen publication foundation. |
| Required for first paying customer? | no — native gated Telegram publish (AI.70–75) already exists |
| Alternative without new MCP | See comparison section |

---

## 3. Tool surface

| Representative tools | Read/Write | Risk |
|---------------------|------------|------|
| send/edit/forward messages | Write | Bypasses PublicationPackage approval |
| read all dialogs | Read | PII exposure |
| admin/moderation tools | Write | Destructive |

100+ tools claimed on npm package — **Requires technical validation** per package.

---

## 4. Authentication

MTProto user session / QR login — highly sensitive session tokens.

---

## 5. Trust boundary

User account access; cloud-hosted variants = third-party proxy risk. Conflicts with tenant isolation.

---

## 6. Controls (required gateway)

Marketsynth requires: approved package only, snapshot_hash, gated execute, message_id evidence. MCP userbot bypasses all.

Marketsynth mandatory path: External MCP → Connector Gateway → server allowlist → **tool-level allowlist** → tenant credentials → budget/rate limits → human approval for writes → evidence + audit log.

---

## 7. Operational fit

Duplicates native Telegram provider in AI.70–75 freeze.

---

## 8. Security

**Critical** — full account access, supply-chain incidents in MCP ecosystem, OAuth/session theft risk.

---

## 9. Comparison to existing connectors

| Existing | Overlap | Keep? |
|----------|---------|-------|
| Native Telegram publish (AI.70–75) | Publication execute | **Keep native** |
| PublicationPackageJob | Gated send | **Reject MCP bypass** |

---

## 10. Adopt / Adapt / Reject scoring

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | 1 | |
| Golden path fit | 0 | |
| Evidence integrity | 0 | |
| Security / trust | 0 | |
| Operational cost | 2 | |
| Duplicate of existing | 0 | |

**Total:** 3 / 12

---

## 11. Decision

| Decision | **Reject** |
|----------|----------------|
| **Rationale** | Hard reject: duplicates frozen gated publication path; uncontrolled write surface; bypasses approval, package snapshot, and message_id evidence contract. |
| **Required gateway controls** | N/A — do not install |
| **Defer unblock condition** | N/A |
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

- docs/phase_ai_75_telegram_publishing_readiness_audit.md
- https://github.com/mcp-telegram/mcp-telegram
- https://www.npmjs.com/package/mcp-telegram
