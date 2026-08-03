# SKILL-R0.2 — RFC Drafting Summary

**Phase:** SKILL-R0.2 — RFC Drafting (+ SKILL-00.9 acceptance)  
**Date:** 2026-07-23  
**Status:** Complete (documentation only)  
**Prior phase:** [SKILL-R0.1 Candidate Audit](../research/SKILL-R0.1-candidate-audit-summary.md)  
**Owner UX note:** CWF.1a conditionally accepted; UX polish → CWF.1a.1 (parallel, non-blocking).

---

## SKILL-00.9 — Owner Architecture Review (2026-07-23)

**Outcome:** All four RFCs **Accepted**. Owner decisions applied. **SKILL-01 Foundation authorized** (documentation gate passed — implementation may begin).

| RFC | Status | Approved |
|-----|--------|----------|
| RFC-SKILL-001 | **Accepted** | 2026-07-23 |
| RFC-SKILL-002 | **Accepted** | 2026-07-23 |
| RFC-SKILL-003 | **Accepted** | 2026-07-23 |
| RFC-CONN-001 | **Accepted** | 2026-07-23 |

**New artifacts:** [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) · [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md) · [SKILL-ROADMAP](SKILL-ROADMAP.md)

### Owner decisions applied

| ID | Decision | Resolution |
|----|----------|------------|
| **OD-001** | Tenant-private Skills | Quarantine → automated validation → tenant_private → tenant_active (within tenant); platform audit only before global or elevated tools |
| **OD-002** | Credential bindings | Tenant-scoped; Project references binding; Skills/Connectors never store credentials |
| **OD-003** | `paused` status | **Rejected** — use `suspended` only |
| **OD-004** | Higgsfield | **Defer** — no production contract until sandbox (OQ-402 deferred) |
| **OD-005** | Implementation strategy | **Top-down** — MS-SKILL-001 Market Validation drives contracts/validator/registry (see SKILL-ROADMAP) |

### Resolved open questions (SKILL-00.9)

| ID | Resolution |
|----|------------|
| OQ-003 | OD-001 — limited tenant self-serve |
| OQ-004 | OD-003 — `paused` rejected |
| OQ-302 | OD-001 — automated validation for tenant-private within tenant |
| OQ-401 | OD-002 — tenant-scoped credentials |
| OQ-402 | OD-004 — Defer until Higgsfield sandbox |

### Remaining deferred open questions

OQ-001, OQ-002, OQ-005, OQ-101..105, OQ-301, OQ-303, OQ-304, OQ-403..405 — see individual RFCs; none block SKILL-01 Foundation.

---
## 1. RFCs created

| Document | Purpose |
|----------|---------|
| [RFC-SKILL-001 — Skill Registry & Lifecycle](RFC-SKILL-001-skill-registry-and-lifecycle.md) | Identity, lifecycle, lookup semantics, external vs internal Skill |
| [RFC-SKILL-002 — Skill Package Format](RFC-SKILL-002-skill-package-format.md) | MSP layout, manifest schema, validation, Agent Skills import adapter |
| [RFC-SKILL-003 — Security & Trust Boundary](RFC-SKILL-003-skill-security-and-trust-boundary.md) | Threat model, invariants, quarantine/audit, trust classes |
| [RFC-CONN-001 — Connector Gateway & Private Registry](RFC-CONN-001-connector-gateway-and-private-registry.md) | Gateway pipeline, tool policy, connector lifecycle, P0 baselines |
| [SKILL-CONN-glossary](SKILL-CONN-glossary.md) | Shared terminology across all RFCs |

**Drafting order applied:** RFC-SKILL-001 (registry) before RFC-SKILL-002 (format) in dependency terms — format references registry states; both drafted in R0.2 per owner directive.

---

## 2. Core decisions

| # | Decision |
|---|----------|
| D1 | **Two registries:** Skill Registry ≠ Connector Registry — separate lifecycles and trust boundaries |
| D2 | **Deny-by-default** at registry, gateway, tool, and runtime layers |
| D3 | **External Skills never `active` directly** — quarantine → audit → internal manifest |
| D4 | **manifest.yaml is permission SoT;** SKILL.md is instructions only |
| D5 | **Tool-level allowlist mandatory;** server-level MCP trust insufficient |
| D6 | **Agent Skills spec Adopted for package patterns only** — not production install |
| D7 | **marketingskills Adapt** — methodology internalization with Evidence/Approval |
| D8 | **XmlRiver + Firecrawl Adapt** as research baseline connectors through gateway |
| D9 | **Telegram MCP Reject;** native publication (AI.70–75) authoritative |
| D10 | **Ad MCPs + Smithery production Reject** |
| D11 | **Higgsfield Adapt pilot only** after sandbox audit blockers cleared |
| D12 | **Playwright Defer** until Firecrawl benchmark + read-only profile |
| D13 | **Every execution records `skill_id` + `skill_version`** when Skill-attributed |
| D14 | **Global Skills platform-owned;** tenant-private Skills isolated per tenant |
| D15 | **Scripts disabled by default** in Skill packages |

---

## 3. Shared invariants (cross-RFC)

1. Skills cannot access secrets or define credentials.
2. Skills cannot expand permissions or invoke undeclared tools.
3. Skills cannot cross tenant boundaries or bypass Approval/Evidence/SoT.
4. External reputation (MIT, stars, marketplace listing) ≠ production trust.
5. Connectors route all external I/O; Skills reference Connector Tool IDs only.
6. Write / destructive / billing / publication tools require approval unless documented exemption.
7. Quarantined objects are never production-eligible.
8. Archived versions remain resolvable for lineage.
9. Hosted MCP proxies are not credential trust roots.
10. Telegram publication stays on native frozen path.

Full list: [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) (20 invariants) · [RFC-SKILL-003 § Hard invariants](RFC-SKILL-003-skill-security-and-trust-boundary.md#hard-invariants).

---

## 4. Open questions (consolidated)

### Resolved (SKILL-00.9)

| ID | Resolution |
|----|------------|
| OQ-003 | OD-001 — tenant-private self-serve within tenant; platform audit before global/elevated |
| OQ-004 | OD-003 — `paused` rejected; use `suspended` |
| OQ-302 | OD-001 — automated validation for tenant-private path |
| OQ-401 | OD-002 — tenant-scoped Credential Binding; Project references binding |
| OQ-402 | OD-004 — Higgsfield Defer until sandbox |

### Remaining (deferred — do not block SKILL-01)

| ID | RFC | Question |
|----|-----|----------|
| OQ-001 | SKILL-001 | `approved` tenant preview runs before `active`? |
| OQ-002 | SKILL-001 | `archived` retention period |
| OQ-005 | SKILL-001 | `latest_active` pointer vs semver ranges per campaign |
| OQ-101 | SKILL-002 | `manifest.lock` sidecar for file hashes |
| OQ-102 | SKILL-002 | Template engine subset |
| OQ-103 | SKILL-002 | Max SKILL.md size |
| OQ-104 | SKILL-002 | Package signing at publish |
| OQ-105 | SKILL-002 | Agent Skills compatibility field mapping |
| OQ-301 | SKILL-003 | Injection red-team frequency |
| OQ-303 | SKILL-003 | Third-party pen test before first adapted Skill |
| OQ-304 | SKILL-003 | Signing key rotation |
| OQ-403 | CONN-001 | Firecrawl SSRF allowlist ownership |
| OQ-404 | CONN-001 | Connector version pinning policy |
| OQ-405 | CONN-001 | Playwright read-only subset when Defer lifts |

---

## 5. Conflicts found in current architecture

| Conflict | Current state | RFC resolution | Migration |
|----------|---------------|----------------|-----------|
| **C1: Dual skill systems** | H2.2 `app/specialist_skills/` Python registry vs future MSP packages | MSP becomes target; Python defs export as `candidate` packages | SKILL-01 export script |
| **C2: Skill vs marketing skills** | `app/marketing/skills/` frozen marketing layer vs specialist skills | RFC scope: specialist/governed Skills; marketing skills remain frozen unless owner slice | No change in R0.2 |
| **C3: MCP registry vs business tools** | `app/mcp/registry.py` + direct provider modules | Connector Gateway wraps adapters; registry becomes private Connector Registry | SKILL-01 gateway stub |
| **C4: Deployment-level API keys** | XmlRiver/Firecrawl use env credentials | Tenant-scoped credential bindings per RFC-CONN-001 | Post SKILL-01 credentials RFC |
| **C5: H2.2 lifecycle subset** | `draft|active|paused|deprecated|archived` only | Full lifecycle; **`paused` → `suspended`** (OD-003) | Map `draft`→`candidate` |
| **C6: No skill_version in lineage** | Execution records may lack Skill version | Nullable fields until SKILL-01 | Backfill optional |
| **C7: integration_registry vs connector health** | `configured|ready|degraded|blocked` | Align terminology in SKILL-01 docs | Documentation bridge |

No conflicts require CWF.1 / CWF.1a code changes.

---

## 6. SKILL-01 Foundation scope (authorized)

**See:** [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md) · [SKILL-ROADMAP](SKILL-ROADMAP.md)

**Strategy:** Top-down — MS-SKILL-001 Market Validation skeleton **first**, then contracts/validator/registry derived from it.

### In scope

| Sub-phase | Deliverable |
|-----------|-------------|
| SKILL-01.0 | MS-SKILL-001 Market Validation MSP skeleton (driver) |
| SKILL-01.1 | Contracts in `contracts.py` |
| SKILL-01.2 | Manifest validator CLI |
| SKILL-01.3 | Registry read model |
| SKILL-01.4 | Quarantine import adapter |
| SKILL-01.5 | Connector Gateway interfaces + XmlRiver/Firecrawl passthrough |
| SKILL-01.6 | Audit report schema |
| SKILL-01.7 | Lineage metadata |
| SKILL-01.8 | Freeze audit |

### Out of scope

Execution engine, dynamic loader, marketplace, GitHub install, tenant upload UI, Skill composer, Higgsfield, Playwright, Telegram MCP, ads, CRM, DB migrations (unless trivial nullable lineage), API, frontend.

~~### Suggested implementation order~~

~~1. Contracts + glossary alignment tests~~  
~~...~~

*(Superseded by top-down order in SKILL-01 plan.)*

---

## 7. Explicitly deferred items

| Item | Defer until | Reason |
|------|-------------|--------|
| Higgsfield pilot | Sandbox `tools/list` + legal + OAuth model | SKILL-R0.1 blockers |
| Playwright MCP | Firecrawl benchmark complete | SKILL-R0.1 Defer |
| Ad platform connectors | Native gated adapters RFC | Hard reject for MCP |
| CRM connectors (amoCRM, etc.) | CRM RFC + DPA | P1 Defer |
| Skill marketplace / tenant upload UI | Post commercial proof | Product reject |
| Automatic Skill composition | SKILL-03+ | Complexity |
| UX polish (CWF.1a typography/cards) | Owner slice after Skills foundation | Owner feedback — non-blocking |
| Database persistence for registry | After owner accepts RFCs | R0.2 conceptual only |
| MS-SKILL-013 AI SEO | KPI proof | SKILL-R0.1 Defer |
| MS-SKILL-016 Ad Creative | Ad connector policy | SKILL-R0.1 Defer |

---

## 8. SKILL-R0.1 decision preservation checklist

| Audit decision | Preserved in RFCs |
|----------------|-------------------|
| Agent Skills spec → Adopt format only | RFC-SKILL-002 |
| marketingskills → Adapt, no drop-in | RFC-SKILL-001, RFC-SKILL-003 |
| Telegram MCP → Reject | RFC-CONN-001 |
| XmlRiver/Firecrawl → Adapt baseline | RFC-CONN-001 |
| Higgsfield → Adapt pilot only | RFC-CONN-001 |
| Playwright → Defer | RFC-CONN-001, glossary |
| Ad MCPs → Reject | RFC-CONN-001 |
| Smithery → Reject prod trust | RFC-CONN-001, RFC-SKILL-003 |
| MCP Registry → discovery only | RFC-CONN-001 |
| Skills ≠ MCP contours | All RFCs + glossary |

---

## 9. Verification results (SKILL-00.9)

| Check | Result |
|-------|--------|
| All 4 RFC status **Accepted** | **Pass** |
| OQ-003, 401, 402, 004 resolved | **Pass** |
| No `paused` state in glossary/RFCs | **Pass** |
| ARCHITECTURAL-INVARIANTS created | **Pass** |
| SKILL-01 plan + ROADMAP created | **Pass** |
| Top-down strategy documented | **Pass** |
| Production code unchanged | **Pass** |

## 10. Verification results (SKILL-R0.2)

| Check | Result |
|-------|--------|
| All 4 RFC drafts exist | **Pass** |
| Shared glossary exists | **Pass** |
| Lifecycle defined (Skill + Connector) | **Pass** |
| Package format defined | **Pass** |
| Security invariants defined | **Pass** |
| Connector gateway defined | **Pass** |
| Internal RFC links resolve | **Pass** (relative paths within `docs/rfc/`) |
| Terminology consistent | **Pass** (normative glossary) |
| No SKILL-R0.1 contradiction | **Pass** |
| Telegram MCP remains rejected | **Pass** |
| External Skill direct install rejected | **Pass** |
| Production code unchanged | **Pass** |
| CWF.1 unchanged | **Pass** |
| CWF.1a unchanged | **Pass** |
| No MCP installed | **Pass** |
| No dependency file changed | **Pass** |
| No executable Skill added | **Pass** |

---

## 11. Runtime unchanged confirmation

| Artifact | Modified |
|----------|----------|
| `app/` Python code | **No** |
| `web/` frontend | **No** |
| Database / Alembic | **No** |
| `pyproject.toml` / deps | **No** |
| MCP servers | **No** |
| CWF.1 / CWF.1a behavior | **No** |

SKILL-R0.2 + SKILL-00.9 are **documentation-only**.

---

## 12. Recommended next actions

1. **Begin SKILL-01.0** — MS-SKILL-001 Market Validation MSP skeleton (driver artifact).
2. **Freeze each SKILL-01.x sub-phase** before proceeding (see implementation plan).
3. **Parallel:** CWF.1a.1 Visual Polish (typography, cards, icons) — separate track.
4. **Future doc-only:** Higgsfield sandbox `tools/list` capture when ops ready (OD-004).

~~## 11. Recommended owner actions~~

~~1. **Review RFC drafts**~~ — **Done (SKILL-00.9)**

---

## Related documents

- [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md)
- [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
- [SKILL-ROADMAP](SKILL-ROADMAP.md)
- [SKILL-R0.1 Candidate Audit Summary](../research/SKILL-R0.1-candidate-audit-summary.md)
- [Adopt-Adapt-Reject Matrix](../research/adopt-adapt-reject-matrix.md)
- [Marketsynth Subsystem Standard](../architecture/marketsynth_subsystem_standard.md)
- [CWF.1a Intent Entry UX](../product/CWF.1a-intent-entry-ux.md)
