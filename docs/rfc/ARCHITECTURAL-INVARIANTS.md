# Architectural Invariants — Skills & Connectors

**Phase:** SKILL-00.9 — Owner Decisions & RFC Acceptance  
**Status:** Accepted  
**Approved by Owner:** 2026-07-23  
**Authority:** Constitutional layer for all Skill and Connector implementation.  
**Supersedes:** Ad hoc security assumptions; complements [Marketsynth Subsystem Standard](../architecture/marketsynth_subsystem_standard.md).

These invariants are **non-negotiable**. Implementation MUST fail closed when an invariant cannot be satisfied.

---

## Invariant 1 — No direct external execution

**Skill never executes directly from external source.**

External packages enter quarantine. Production execution requires an internal Marketsynth Skill Version in registry with audited manifest.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Invariant 2 — Registry is Source of Truth

**Registry is Source of Truth** for Skill identity, version, status, tenant scope, and eligibility.

Filesystem discovery, marketplace listings, and agent auto-selection are not authoritative.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md).

---

## Invariant 3 — Manifest owns permissions

**Manifest owns permissions. SKILL.md never owns permissions.**

Security permissions derive from `manifest.yaml` + registry policy + runtime policy — never from instruction prose alone.

Ref: [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md).

---

## Invariant 4 — External ≠ Internal

**External Skill ≠ Marketsynth Skill.**

They are distinct objects with separate provenance. Adapt produces a new internal Skill; it does not rename or trust the external artifact.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md).

---

## Invariant 5 — Execution lineage

**Every execution stores `skill_id` and `skill_version`.**

When Skill attribution applies, lineage MUST be durable and resolvable for audit — including historical replay on `deprecated` versions.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md).

---

## Invariant 6 — Tenant isolation

**Tenant isolation mandatory.**

One tenant cannot see, invoke, or infer another tenant's private Skills, credentials, or execution records.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Invariant 7 — Connector Gateway mandatory

**Connector Gateway mandatory** for all external service I/O.

Skills do not call external APIs, MCP servers, or URLs directly.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 8 — Tool allowlist mandatory

**Tool allowlist mandatory** at tool granularity.

Server-level MCP allowlist alone is insufficient. Skills may invoke only declared Connector Tool IDs.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Invariant 9 — Approval cannot be bypassed

**Approval cannot be bypassed** for gated action classes (write, destructive, billing-sensitive, publication, launch verdict).

Skills and Connectors declare preconditions; runtime enforces them.

Ref: [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md), CWF.1 Launch Pack.

---

## Invariant 10 — Evidence cannot be bypassed

**Evidence cannot be bypassed** where Skill or workflow declares `required_evidence` or Citation Contract applies.

Insufficient governed knowledge or source material MUST block verdict-class outputs.

Ref: [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md), Knowledge Governance ADR.

---

## Invariant 11 — No Skill-owned secrets

**No Skill owns secrets.**

Skills cannot embed, reference, or define credentials. Credential bindings are tenant-scoped and live outside Skill packages.

Ref: [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md), [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 12 — No Connector-owned tenant identity

**No Connector owns tenant identity.**

Connectors store adapter metadata and tool policies — not tenant secrets. Tenant identity and credential bindings are platform-managed references.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 13 — Scripts disabled by default

**Skill scripts disabled by default.**

`scripts/` execution requires explicit audit approval and sandbox profile. Default is inert.

Ref: [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Invariant 14 — Reputation ≠ Trust

**External reputation ≠ Trust.**

MIT license, GitHub stars, marketplace presence, or vendor brand do not grant production eligibility.

Ref: [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md), [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md).

---

## Invariant 15 — Quarantine before Adapt

**Quarantine required before Adapt.**

Every external Skill or Connector candidate enters quarantine before audit, internal manifest generation, or promotion.

Ref: [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 16 — No marketplace installation

**Marketplace installation forbidden** in product paths.

No auto-install from Smithery, GitHub, or catalog browse into production. Discovery may inform audit queue only.

Ref: [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md), [SKILL-ROADMAP](SKILL-ROADMAP.md).

---

## Invariant 17 — Native Telegram authoritative

**Native Telegram publication remains authoritative.**

Telegram MCP and userbot patterns are rejected. Publication flows through frozen native path (AI.70–75).

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 18 — Write tools require approval

**Write tools require approval** unless an explicit, audited policy exemption exists per tool and tenant.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 19 — Billing tools require approval

**Billing tools require approval** and budget policy before execution.

No ungated spend surfaces via MCP bundles or Skill tool expansion.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Invariant 20 — External actions emit Evidence

**Every external action generates Evidence** suitable for audit lineage.

Connector executions emit execution records with source/query/cost/tool version. Evidence admission gates remain separate for verdict-class outputs.

Ref: [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md).

---

## Related documents

- [SKILL-CONN-glossary](SKILL-CONN-glossary.md)
- [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md)
- [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md)
- [SKILL-01 Foundation Plan](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
