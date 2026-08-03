# SKILL & Connector Glossary

**Phase:** SKILL-R0.2 → SKILL-00.9  
**Status:** **Accepted**  
**Approved by Owner:** 2026-07-23  
**Purpose:** Shared terminology across RFC-SKILL-001..003 and RFC-CONN-001.  
**Authority:** This glossary is normative for Skill and Connector RFCs. Where legacy docs (e.g. H2.2 `skill_registry.md`) conflict, these RFC definitions take precedence for SKILL-01+ implementation.
---

## Core terms

### Skill

A **versioned, governed capability contract** that defines what a Marketsynth operator may do: required inputs, declared outputs, allowed tools, quality gates, approval requirements, and evidence obligations. A Skill is **not** a prompt file, not a Python module, and not an executable by itself.

See: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md).

### Skill Version

An **immutable released unit** of a Skill identified by semantic version (e.g. `1.2.0`). Each version has its own manifest, content hash, lifecycle status, and audit record. Runtime execution always records both `skill_id` and `skill_version`.

### Capability

A **declarative affordance** advertised by a Skill or Connector Tool (e.g. `research.web_search`, `content.telegram_draft`, `media.image_generate`). Capabilities are used for registry lookup and runtime routing; they do not grant permissions by themselves.

### Connector

A **governed adapter** between Marketsynth and an external service or MCP server. Connectors expose normalized **Connector Tools** through the Connector Gateway. Connectors are distinct from Skills.

See: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

### Connector Tool

A **single invocable operation** exposed by a Connector (e.g. `xmlriver.search`, `firecrawl.scrape`, `higgsfield.generate_image`). Each tool has a classification (read / write / destructive / billing-sensitive / publication), policy bindings, and tenant credential requirements.

### Registry

A **platform-controlled catalog** that stores metadata, lifecycle state, policies, and provenance for Skills or Connectors. Marketsynth maintains **two registries**:

| Registry | Scope |
|----------|-------|
| **Skill Registry** | Internal and tenant-private Skills |
| **Connector Registry** | External service adapters and MCP-derived tools |

Registries are not marketplaces and are not trust roots for external packages.

### Quarantine

An **isolation state** for external candidates (imported Skill packages or Connector candidates) before audit. Quarantined objects are stored, inspectable, and **never eligible for production execution**.

### Approval

A **human or policy gate** that must be satisfied before write-class, billing-sensitive, publication, or launch-class actions proceed. Approval is a product invariant; Skills and Connectors cannot bypass it.

Related: CWF.1 Launch Pack, PublicationPackageJob (AI.70–75), paid smoke gates.

### Evidence

Durable **audit artifacts** required for knowledge-backed and verdict-class outputs: Answer + Source + Confidence (+ optional excerpt). Skills declare `required_evidence`; Connectors emit fetch/search lineage. Evidence is not optional for production-trusted research or launch decisions.

Related: Citation Contract, `research_source_collection`.

### Tenant Scope

The **visibility and eligibility boundary** for a Skill or Connector binding:

| Scope | Meaning |
|-------|---------|
| `global` | Platform-owned; visible to all tenants; only Marketsynth may publish |
| `tenant_private` | Visible and executable only within owning tenant |
| `project_scoped` | Further restricted to named project(s) within tenant |

One tenant cannot see another tenant's private Skill or Connector credentials.

### Credential Binding

A **tenant-scoped reference** to stored secrets used by Connector Gateway at invoke time. Credential Bindings are owned by the **tenant** — not by projects, Skills, or Connectors. Projects **reference** an allowed binding; they do not store separate secrets by default (Owner Decision 002).

### Project Binding

A **project-level pointer** to a tenant Credential Binding authorized for that project. Does not duplicate secrets.

### Provenance

Structured **lineage metadata** describing origin: source repository, import adapter, audit run, license, content hash, adapting engineer, and promotion decisions. Provenance is required for platform-adapted and external-candidate objects.

### Policy

A **deny-by-default ruleset** applied at registry, runtime, or tool level. Policies include allowlists, approval requirements, budget/rate limits, network egress rules, and tenant bindings. Policies override Skill instructions and Connector metadata.

### Runtime Compatibility

The set of **execution environments** a Skill Version or Connector Version may run in (e.g. `operator_dry_run`, `assistant_explicit_run`, `campaign_action`, `generation_reliability`). Incompatible Skills are not offered for activation in that runtime.

---

## Lifecycle states (Skill)

| State | Meaning |
|-------|---------|
| `candidate` | Discovered or submitted; not audited |
| `quarantined` | Imported external artifact; inspection only |
| `audited` | Static/behavioral audit complete; pending approval |
| `approved` | Owner/policy approved for activation |
| `active` | Eligible for governed execution |
| `deprecated` | Still resolvable; superseded; no new activations preferred |
| `archived` | Historical lineage only; not activatable |
| `rejected` | Permanently blocked (optional terminal state) |
| `suspended` | **Sole** temporary halt; reversible (replaces legacy `paused`) |
| `tenant_private` | Scope: visible only within owning tenant; not activatable until validated |
| `tenant_active` | Activatable within owning tenant only (Owner Decision 001) |

**No `paused` state** — use `suspended` only (Owner Decision 003).

Full transition rules: [RFC-SKILL-001 § Lifecycle](RFC-SKILL-001-skill-registry-and-lifecycle.md#lifecycle).

---

## Lifecycle states (Connector)

| State | Meaning |
|-------|---------|
| `candidate` | Identified; not integrated |
| `quarantined` | MCP/server under inspection |
| `audited` | Tool surface and policy mapped |
| `approved` | Cleared for limited activation |
| `active` | Production-eligible through gateway |
| `degraded` | Partial outage or rate-limit backoff |
| `suspended` | Emergency halt |
| `deprecated` | Superseded; wind-down |
| `archived` | Historical only |
| `rejected` | Permanently blocked |

Full transition rules: [RFC-CONN-001 § Lifecycle](RFC-CONN-001-connector-gateway-and-private-registry.md#lifecycle).

---

## Trust classes (Skill)

| Class | Description |
|-------|-------------|
| `platform-native` | Authored and audited inside Marketsynth |
| `platform-adapted` | Methodology/code adapted from external source with internal manifest |
| `tenant-private` | Tenant-owned; tenant-scoped policies |
| `external-candidate` | Imported package in quarantine; never production-trusted |
| `rejected` | Failed audit or hard reject from SKILL-R0.1 |

See: [RFC-SKILL-003 § Trust classes](RFC-SKILL-003-skill-security-and-trust-boundary.md#trust-classes).

---

## Connector classes

| Class | Examples (audit posture) |
|-------|--------------------------|
| `research` | XmlRiver, Firecrawl — **Adapt** baseline |
| `content_generation` | Higgsfield — **Adapt** pilot only |
| `publication` | Native Telegram path — authoritative; Telegram MCP **Reject** |
| `analytics` | Metrica — native adapter; MCP **Defer** |
| `crm` | amoCRM, Bitrix, HubSpot — **Defer** |
| `advertising` | Google/Meta/Yandex ad MCPs — **Reject** direct MCP |
| `storage` | Google Drive, Notion — **Defer** |
| `development` | GitHub MCP — **Defer**, dev-only |

---

## Distinctions (do not conflate)

| Term A | Term B | Rule |
|--------|--------|------|
| Skill | Connector | Separate registries, separate trust boundaries |
| Methodology reuse | Code reuse | Separate decisions; Adapt may reuse methodology without importing package |
| External source | Internal Skill | Distinct objects; external never becomes `active` directly |
| SKILL.md | manifest.yaml | Instructions vs permissions; security from manifest + registry policy |
| MCP server | Connector | Server is external; Connector is governed adapter + tool allowlist |
| Discovery registry | Private registry | Official MCP Registry / catalogs = discovery only; not production trust |

---

## Related documents

- [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md)
- [SKILL-01 Foundation Plan](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
- [SKILL-ROADMAP](SKILL-ROADMAP.md)
- [RFC-SKILL-004 — Discovery & Draft Generation (Draft)](RFC-SKILL-004-skill-discovery-and-draft-generation.md)
- [RFC-SKILL-001 — Skill Registry & Lifecycle](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-002 — Skill Package Format](RFC-SKILL-002-skill-package-format.md)
- [RFC-SKILL-003 — Security & Trust Boundary](RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [RFC-CONN-001 — Connector Gateway](RFC-CONN-001-connector-gateway-and-private-registry.md)
- [SKILL-R0.1 Candidate Audit Summary](../research/SKILL-R0.1-candidate-audit-summary.md)
- [Marketsynth Subsystem Standard](../architecture/marketsynth_subsystem_standard.md)
