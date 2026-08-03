# RFC-CONN-001 — Connector Gateway & Private Registry

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-CONN-001 |
| **Status** | **Accepted** |
| **Approved by Owner** | 2026-07-23 |
| **Phase** | SKILL-R0.2 → SKILL-00.9 acceptance |
| **Depends on** | [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md), [SKILL-CONN-glossary](SKILL-CONN-glossary.md) |
| **Blocks** | Higgsfield pilot, per-tenant XmlRiver/Firecrawl hardening, SKILL-01 connector read model |
| **Related legacy** | `app/mcp/registry.py`, `app/business_tools/providers/`, [integration_registry.md](../integration_registry.md) |

**Change history**

| Date | Change |
|------|--------|
| 2026-07-23 | Draft (SKILL-R0.2) — gateway architecture |
| 2026-07-23 | **Accepted (SKILL-00.9)** — OD-002 credential bindings; OD-004 Higgsfield defer; OQ-401/OQ-402 resolved |

---

## Context

SKILL-R0.1 audited 16 MCP/connector candidates. Key conclusions:

- **XmlRiver** and **Firecrawl** — **Adapt** as existing native baselines; need tenant credential RFC and gateway hardening.
- **Higgsfield** — **Adapt** pilot only; mandatory gateway; tool schemas **unknown** until sandbox `tools/list`.
- **Playwright MCP** — **Defer** pending benchmark and read-only sandbox profile.
- **Telegram MCP** — **Reject** — duplicates frozen native publish (AI.70–75); bypasses approval.
- **Ad MCPs** (Google/Meta/Yandex) — **Reject** for direct MCP activation.
- **Smithery / hosted MCP proxies** — **Reject** as production trust roots.
- **Official MCP Registry** — **Adapt** as **discovery only**, not private registry authority.

Today, XmlRiver and Firecrawl are integrated as read-only business tools with deployment-level credentials. This RFC defines the **target Connector Gateway architecture** without implementing it.

---

## Problem

MCP ecosystem patterns encourage:

- Server-level installation trust (insufficient)
- Bundled tools with mixed read/write/destructive surfaces
- Hosted proxies holding tenant secrets (supply-chain risk)
- Skills invoking external endpoints directly

Marketsynth requires a **private Connector Registry** and **gateway** that normalizes all external I/O through policy, approval, evidence, and tenant-scoped credentials.

---

## Goals

1. Define Connector entities, lifecycle, and gateway pipeline.
2. Mandate **tool-level allowlists** and tool classifications.
3. Preserve native Telegram publication as authoritative.
4. Encode SKILL-R0.1 Adopt/Adapt/Reject/Defer per connector class.
5. Specify observability, idempotency, and failure handling requirements.

---

## Non-goals

- Installing MCP servers or Smithery connectors
- Higgsfield OAuth implementation
- Per-tenant credential vault UI
- Billing metering implementation
- Changing native Telegram publish path (AI.70–75)
- Playwright sandbox (deferred)

---

## Decision

### Architecture pipeline

```
External service / MCP server
  → Connector Adapter (normalize protocol + errors)
  → Connector Gateway (authZ, policy, budget, rate)
  → Tool Registry (private, versioned tools)
  → Policy Engine (deny-by-default)
  → Approval (writes / spend / publish)
  → Execution (idempotent where supported)
  → Evidence (lineage + audit log)
```

**Skills never call external services directly** — only declared Connector Tools via gateway.

### Core entities

| Entity | Description |
|--------|-------------|
| **Connector** | Logical adapter to one external service family (e.g. `connector.firecrawl`) |
| **Connector Version** | Immutable semver release of adapter + tool surface mapping |
| **Connector Tool** | Single operation (e.g. `firecrawl.scrape`) with classification |
| **Credential Binding** | Tenant-scoped secret reference (not in Skill packages) |
| **Tenant Binding** | Which tenants may use which Connector Version |
| **Tool Policy** | Allow/deny, approval rules, input/output limits per tool |
| **Budget Policy** | Spend/credit caps (billing-sensitive tools) |
| **Rate Policy** | Throttle and concurrency limits |
| **Execution Record** | Durable log: tenant, tool, idempotency key, outcome, cost estimate |
| **Health State** | `healthy`, `degraded`, `unavailable` per Connector Version |

### Credential binding model (Owner Decision 002)

**Accepted ownership chain:**

```
Tenant
  → Credential Binding (tenant-scoped; sole secret owner)
  → Project references Credential Binding (no separate project secrets by default)
  → Connector Gateway resolves binding at invoke time
```

**Rules:**

- **Credential Binding = tenant-scoped.** Secrets belong to the tenant, not to projects, Skills, or Connectors.
- **Projects reference** an allowed tenant credential binding — they do **not** store separate secrets unless an explicit future owner exception RFC defines a narrow case.
- **Skills never own credentials** — manifest may reference allowed tool IDs only.
- **Connectors never store credentials** — adapter code receives a binding reference; vault holds secrets.
- Avoid per-project secret proliferation to prevent key chaos and rotation failure.

### Connector lifecycle {#lifecycle}

States:

```
candidate → quarantined → audited → approved → active → deprecated → archived
                                    ↓
                              degraded / suspended
                                    ↓
                                 rejected
```

| State | Meaning |
|-------|---------|
| `candidate` | Identified in audit; not wired |
| `quarantined` | MCP server or API under inspection (e.g. Higgsfield OAuth probe) |
| `audited` | Tool surface mapped; policies drafted |
| `approved` | Cleared for limited activation |
| `active` | Gateway routes production traffic |
| `degraded` | Partial failure / elevated latency / rate limit |
| `suspended` | Emergency stop |
| `deprecated` | Superseded; wind-down |
| `archived` | Historical reads only |
| `rejected` | Permanent block (Telegram MCP, ad MCPs, Smithery prod) |

Valid transitions mirror RFC-SKILL-001 discipline: no skip from `quarantined` to `active`.

### Tool classification (mandatory)

Every Connector Tool MUST declare one primary class:

| Class | Approval default | Examples |
|-------|------------------|----------|
| `read` | Log only | XmlRiver search, Firecrawl scrape |
| `write` | Human/policy approval unless exempt | CRM update — Defer |
| `destructive` | Always approval | Delete resource |
| `billing_sensitive` | Approval + budget cap | Higgsfield generate |
| `publication` | Approval + native path check | **Native Telegram only** |

**Rules:**

- Read and write tools **separated** at registry level (no opaque "mixed" tool without decomposition).
- Destructive tools require explicit approval policy — none on CWF P0 path.
- Billing-sensitive tools require budget policy + preflight quote where available.
- Publication tools: **Telegram MCP rejected**; native `PublicationPackageJob` remains authoritative.

### Required policies

| Policy | Requirement |
|--------|-------------|
| Server-level allowlist | **Insufficient alone** |
| Tool-level allowlist | **Mandatory** — Skills reference tool IDs, not servers |
| Credentials | Tenant-scoped; never in Skill packages; never in hosted proxy trust root |
| Write actions | Approval unless explicitly exempted in policy record |
| Connector failures | Observable: health state, structured errors, execution records |
| Idempotency | Required where upstream supports; gateway generates/stores idempotency keys |
| Retries | Must not duplicate side effects on write/billing tools |
| Evidence | Every execution emits lineage suitable for audit (URL fetched, query, cost, tool version) |
| External hosted proxies | **Not trust roots** — Smithery class rejected for production secrets |

### Connector classes & SKILL-R0.1 posture

| Class | P0 candidates | Audit decision |
|-------|---------------|----------------|
| **research** | XmlRiver, Firecrawl | **Adapt** — baseline hardening |
| **content_generation** | Higgsfield | **Adapt** — pilot only after `tools/list` + legal |
| **publication** | Native Telegram | Authoritative; Telegram MCP **Reject** |
| **analytics** | Metrica | Native adapter preferred; MCP **Defer** |
| **crm** | amoCRM, Bitrix, HubSpot | **Defer** |
| **advertising** | Google/Meta/Yandex ad MCPs | **Reject** direct MCP |
| **storage** | Google Drive, Notion | **Defer** |
| **development** | GitHub MCP | **Defer**, dev-only |

**Playwright MCP:** **Defer** — if activated later, only as `research` class with read-only tool subset + sandbox; benchmark vs Firecrawl first ([browser-research-comparison](../research/mcp/browser-research-comparison.md)).

**Discovery:** Official MCP Registry and catalogs (Smithery, VoltAgent) may feed **candidate** queue only — not production activation.

### Gateway request flow

```
1. Resolve Connector Tool by id + version (private registry)
2. Verify tenant binding + credential binding present
3. Evaluate tool policy (deny-by-default)
4. Check budget/rate policies
5. If write|destructive|billing_sensitive|publication → approval gate
6. Execute via adapter with sanitized inputs
7. Sanitize outputs (injection-safe excerpts)
8. Write execution record + evidence lineage
9. Update health metrics
```

### Baseline connectors (existing code)

| Connector | Current integration | Target gateway action |
|-----------|--------------------|-----------------------|
| XmlRiver | `app/business_tools/providers/xmlriver_search.py`, `app/mcp/registry.py` | Register as `connector.xmlriver` v1; tool `xmlriver.search` (read); tenant creds RFC |
| Firecrawl | `app/business_tools/providers/firecrawl_fetch.py` | Register as `connector.firecrawl` v1; tool `firecrawl.scrape` (read); SSRF review |
| Higgsfield | Not integrated | `quarantined` until sandbox audit |

Hybrid research routing (architecture inference from SKILL-R0.1):

```
Query → xmlriver.search → URL candidates → operator selects → firecrawl.scrape → source candidate
```

Playwright slot reserved as deferred gap-filler only.

### Higgsfield pilot prerequisites (Owner Decision 004 — Defer)

**Status:** **Defer.** No production contract, no implementation, no async/idempotency assumptions in SKILL-01.

Before `quarantined` → `audited` (future phase only):

1. Sandbox `tools/list` with schema capture
2. OAuth token storage model (tenant vault)
3. Content rights / commercial use legal review
4. Billing preflight + budget policy
5. **OQ-402 validation:** confirm idempotency key support, async job ID, retry/billing behavior, safe resume semantics
6. Single dry-run with audit log template (SKILL-R0.1 recommendation)

### Rejected connectors (hard)

| ID | Connector | Reason |
|----|-----------|--------|
| MCP-005 | Telegram MCP | Bypasses native publish + approval |
| MCP-009 | Google Ads MCP | Ungated spend |
| MCP-010 | Meta Ads MCP | Ungated spend |
| MCP-011 | Yandex Direct MCP | Ungated spend |
| META | Smithery hosted proxy | Supply-chain; not trust root |

These MUST NOT appear as `active` in private registry.

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Install MCP servers per tenant | Unbounded tool surface; credential sprawl |
| Smithery as hosted gateway | SKILL-R0.1 reject; Jun 2025 incident class |
| Skills call Firecrawl/XmlRiver directly forever | No central policy, approval, or lineage |
| Server-level "trusted MCP" flag | Insufficient — tool poisoning |
| Telegram MCP for "convenience" | Duplicates frozen native path |

---

## Security implications

- Deny-by-default gateway is primary control plane for external I/O.
- Tool-level allowlist prevents undeclared write/spend/publish.
- Tenant credential isolation prevents cross-tenant API key reuse.
- Output sanitization reduces prompt injection from scraped content.

Cross-ref: [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Tenant implications

- **Credential Binding is tenant-scoped (OD-002).** Projects reference bindings; they do not own secrets.
- Each tenant binds own credentials for commercial APIs (XmlRiver, Firecrawl) when tenant vault ships (SKILL-03+).
- Deployment-level keys (current state) migrate to tenant bindings in SKILL-03+.
- One tenant's connector failure must not mark global connector `suspended` unless shared infra fault.

---

## Evidence implications

- Read tools emit candidate lineage (URLs, queries) — not automatic Evidence admission.
- Firecrawl excerpts remain `candidates_only_not_evidence` until admission gate.
- Execution records support Citation Contract audits.

---

## Approval implications

- Write/destructive/billing/publication tools stop at approval gate unless documented exemption.
- Native Telegram publish retains PublicationPackageJob approval — MCP cannot substitute.

---

## Migration implications

1. Wrap existing XmlRiver/Firecrawl adapters behind gateway interface (SKILL-01 read model first).
2. Map `app/mcp/registry.py` entries to Connector Tool records conceptually.
3. `integration_registry.md` statuses evolve to Connector health states.
4. No breaking API changes in SKILL-R0.2.

---

## Owner decisions (SKILL-00.9)

| ID | Decision | Status |
|----|----------|--------|
| **OD-002** | Credential Binding tenant-scoped; Project references binding; Skills/Connectors never store credentials | **Accepted** |
| **OD-004** | Higgsfield Defer — no production contract until sandbox validation | **Accepted** |

## Resolved open questions

| ID | Resolution |
|----|------------|
| **OQ-401** | **Resolved (OD-002):** Credential Binding = tenant-scoped; Project references tenant credential — no per-project secrets by default |
| **OQ-402** | **Resolved (OD-004):** **Defer** — idempotency/async/retry/billing contract unknown until Higgsfield sandbox |

## Remaining open questions

| ID | Question |
|----|----------|
| OQ-403 | Firecrawl SSRF allowlist — platform-managed or tenant-configured? |
| OQ-404 | Connector Version pinning: tenant opt-out of auto-patch? |
| OQ-405 | Playwright read-only tool subset definition when Defer lifts |

---

## Acceptance criteria

- [x] Gateway pipeline and entities defined
- [x] Tool classifications and policy rules explicit
- [x] SKILL-R0.1 decisions preserved (Telegram MCP reject, ad reject, Smithery reject)
- [x] XmlRiver/Firecrawl baseline path documented
- [x] Higgsfield defer blockers listed (OD-004)
- [x] Terminology matches glossary
- [x] Credential binding model (OD-002) documented

---

## Next implementation phase

**SKILL-01** (see [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)):

1. Connector + Connector Tool contracts (read-only registry)
2. Gateway interface stub with deny-by-default passthrough to existing XmlRiver/Firecrawl
3. Execution record schema (nullable integration)
4. Higgsfield quarantine record + sandbox audit checklist (no connection)

**Post SKILL-01:**

- Higgsfield pilot slice after OQ blockers closed
- Playwright benchmark phase (documentation + benchmark only)

---

## Related documents

- [SKILL-CONN-glossary](SKILL-CONN-glossary.md)
- [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [Browser research comparison](../research/mcp/browser-research-comparison.md)
- [Adopt-Adapt-Reject Matrix](../research/adopt-adapt-reject-matrix.md)
- [Telegram MCP audit card](../research/mcp/candidates/05-telegram.md)
- [Higgsfield audit card](../research/mcp/candidates/03-higgsfield.md)
