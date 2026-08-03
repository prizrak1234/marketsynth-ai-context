# MCP / Connector Audit Card — Template

> Copy this file to `docs/research/mcp/candidates/<slug>.md` and fill every section.  
> Delete instructional lines marked `(instruction)` before marking **Ready for review**.

---

## Metadata

| Field | Value |
|-------|-------|
| **Card ID** | `MCP-AUDIT-____` |
| **Connector name** | |
| **MCP server role (proposed)** | e.g. `search_mcp`, `web_fetch_mcp`, `maps_mcp` |
| **Provider / vendor** | |
| **Documentation URL** | |
| **Reviewed by** | |
| **Review date** | YYYY-MM-DD |
| **Status** | draft \| ready_for_review \| decided |

---

## 1. One-line summary

(instruction) What external capability does this connector provide?

---

## 2. Commercial fit (mandatory)

| Question | Answer |
|----------|--------|
| CWF step strengthened (if any) | Research / Evidence / Verdict / Launch / Publish / none |
| User-visible result enabled | |
| Required for first paying customer? | yes / no / later |
| Alternative without new MCP | existing adapter / manual / not possible |

(instruction) Default **Defer** if not on critical path to CWF.1 completion.

---

## 3. Tool surface

| Tool name | Read / Write | Description | Allowlist candidate? |
|-----------|--------------|-------------|----------------------|
| | | | yes / no |

### Schemas and stability

- Tool schema fingerprint method:
- Breaking change history:
- Rate limits / cost model:

---

## 4. Trust boundary

| Check | Result | Notes |
|-------|--------|-------|
| Read-only compatible | yes / no | |
| Write tools present | none / gated / dangerous | |
| Auth model | API key / OAuth / other | |
| Tenant scoping possible | yes / no | |
| Audit log compatible | yes / no | maps to `mcp_tool_call_audits` |
| Timeout / retry policy | | |
| Response size limits | | |
| PII in responses | likely / unlikely | sanitization plan |

(instruction) Production baseline (CMVP.1): read-only, allowlisted, audited, timeout, retry, tenant-scoped. Deviations require RFC-CONN-001.

---

## 5. Comparison to existing connectors

| Existing | Overlap | Keep both? |
|----------|---------|------------|
| XmlRiver Search MCP | | |
| Firecrawl Fetch MCP | | |
| Native Telegram adapter (non-MCP) | | |

---

## 6. Adopt / Adapt / Reject scoring

Use [Adopt-Adapt-Reject Matrix](../adopt-adapt-reject-matrix.md).

| Dimension | Score 0–2 | Notes |
|-----------|-----------|-------|
| Commercial value | | |
| Golden path fit | | |
| Evidence integrity | | |
| Security / trust | | |
| Operational cost | | |
| Duplicate of existing | | |

**Total:** ___ / 12

---

## 7. Decision

| Decision | ☐ Adopt ☐ Adapt ☐ Reject ☐ Defer |
|----------|-----------------------------------|
| **Rationale** | |
| **If Adapt — wrapper requirements** | native adapter vs MCP; allowlist; mock policy |
| **If Defer — unblock condition** | |
| **Owner sign-off** | pending / approved / rejected |
| **Date decided** | |

---

## 8. Implementation gate (do not fill until post-RFC)

| Gate | Allowed? |
|------|----------|
| SKILL-R0 research only | ✅ always |
| RFC-CONN-001 draft | after decision Adopt/Adapt |
| Production connection | after RFC + owner approval + CWF slice need |
| CWF.1 change | **forbidden** unless separate approved slice |

---

## 9. Smoke notes (research only)

(instruction) Optional local smoke in dev sandbox — never enable in product `.env` without gate.

| Run date | Environment | Result | Audit IDs / logs |
|----------|-------------|--------|------------------|
| | local dev | | |
