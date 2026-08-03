# MCP / Connector Research — audit workspace

**Phase:** SKILL-R0  
**Scope:** connector evaluation only — **not** new MCP servers in production.

---

## What belongs here

- Completed **MCP audit cards** (one file per connector candidate)
- Allowlist / denylist rationale
- Trust boundary notes for read vs write tools
- Draft inputs for **RFC-CONN-001** (Connector / MCP Registry)

## What does NOT belong here

- Live MCP server configs in `.env` or `app/mcp/`
- Auto-import of third-party MCP marketplaces
- Connectors that bypass human approval or CWF evidence gates

---

## How to add a candidate

1. Copy [mcp-audit-card-template.md](mcp-audit-card-template.md) to  
   `docs/research/mcp/candidates/<slug>.md`
2. Fill all required sections.
3. Score using [../adopt-adapt-reject-matrix.md](../adopt-adapt-reject-matrix.md).
4. Set decision: **Adopt | Adapt | Reject | Defer**.
5. If Adopt/Adapt — queue for RFC-CONN-001; do **not** connect in runtime.

---

## Naming convention

```
candidates/<provider>-<role>.md
```

Examples:

- `candidates/firecrawl-web-fetch.md` (existing — audit for baseline)
- `candidates/xmlriver-search.md` (existing — audit for baseline)
- `candidates/maps-local-business.md` (candidate — likely Defer until CWF needs local business)

---

## Reference (existing product)

- `app/mcp/` — current read-only Search MCP + Web Fetch MCP (CMVP.1)
- [../../integration_registry.md](../../integration_registry.md)
- [../../business_tool_abstraction.md](../../business_tool_abstraction.md)

**Current production rule:** MCP is **read-only**, allowlisted, audited, tenant-scoped. Any write connector requires RFC-CONN-001 + explicit owner approval.

---

## RFC output (future)

Research cards feed:

- **RFC-CONN-001** — Connector / MCP Registry

Do not expand MCP surface in CWF.1. Maps MCP and marketplace connectors remain **research-only** until a commercial slice explicitly requires them.
