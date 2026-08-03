# RFC-SKILL-001 — Skill Registry & Lifecycle

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-SKILL-001 |
| **Status** | **Accepted** |
| **Approved by Owner** | 2026-07-23 |
| **Phase** | SKILL-R0.2 → SKILL-00.9 acceptance |
| **Authors** | Marketsynth architecture (Cursor draft) |
| **Depends on** | [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md), [SKILL-CONN-glossary](SKILL-CONN-glossary.md) |
| **Blocks** | RFC-SKILL-002, RFC-SKILL-003, SKILL-01 Foundation |
| **Supersedes (conceptually)** | H2.2 [skill_registry.md](../skill_registry.md) for lifecycle semantics — H2.2 draft-only registry remains until SKILL-01 migration |

**Change history**

| Date | Change |
|------|--------|
| 2026-07-23 | Draft (SKILL-R0.2) — initial lifecycle and registry semantics |
| 2026-07-23 | **Accepted (SKILL-00.9)** — Owner Decisions 001, 003; OQ-003, OQ-004 resolved |

---

## Context

SKILL-R0.1 audited 16 Skill candidates and confirmed:

- External marketing skills (e.g. marketingskills) are **Adapt**, not drop-in install.
- Agent Skills specification is **Adopt** for **package format only**.
- Skills and MCP Connectors are **separate trusted contours**.
- No external Skill becomes production-trusted without registry lifecycle, audit, and owner approval.

Today, `app/specialist_skills/registry.py` holds versioned **draft-only** Python definitions with legacy statuses including `paused`. This RFC defines the **target conceptual registry** before database tables, APIs, or loaders exist. **Owner Decision 003:** `paused` is **rejected** — use `suspended` only. H2.2 `paused` maps to `suspended` on migration.

---

## Problem

Without a formal Skill Registry & Lifecycle:

1. Package format (RFC-SKILL-002) has no place to land after import.
2. Security boundaries (RFC-SKILL-003) cannot reference stable identity and status.
3. External methodology may be confused with executable production Skills.
4. Execution lineage cannot reliably record `skill_id` + `skill_version`.
5. Tenant-private Skills have no visibility model.
6. Cursor or future implementers will invent ad hoc contracts.

---

## Goals

1. Define **Skill identity**, versioning, source, owner, status, and lifecycle.
2. Specify **valid and invalid state transitions** including quarantine and audit gates.
3. Define **registry lookup semantics** (by id, version, capability, status, tenant, runtime).
4. Separate **external source objects** from **internal Marketsynth Skills**.
5. Preserve SKILL-R0.1 decisions (no direct external activation).
6. Align with [Marketsynth Subsystem Standard](../architecture/marketsynth_subsystem_standard.md) lifecycle stages.

---

## Non-goals

- Database schema, migrations, or ORM models
- API endpoints (`GET /skills`, upload UI)
- Runtime loader, executor, or prompt assembly changes
- Automatic Skill composition or marketplace
- Modifying CWF.1, CWF.1a, publication, approval, tenant, evidence, or execution behavior
- Implementing MS-SKILL-001..007 content

---

## Decision

Marketsynth SHALL maintain a **Skill Registry** as the authoritative catalog of governed Skill Versions. Every production execution that claims Skill attribution MUST reference a registry-resolved `skill_id` and `skill_version` in `active` or `deprecated` (historical replay) state.

### Skill identity model

| Concept | Definition | Constraints |
|---------|------------|-------------|
| **skill_id** | Stable logical identifier (e.g. `ms.skill.market_validation`) | Immutable; lowercase dot-separated; platform-assigned or tenant-prefixed for private |
| **Skill Version** | Released semver unit | Immutable once released; patch for fixes, minor for compatible capability adds, major for breaking I/O |
| **Skill source** | Origin class | `platform_native`, `platform_adapted`, `tenant_private`, `external_import` |
| **Skill owner** | Accountable party | Platform team for global; tenant admin for private; required for every `active` Skill |
| **Skill status** | Lifecycle state | See [Lifecycle](#lifecycle) |
| **Skill compatibility** | Runtime + connector + knowledge requirements | Declared in manifest; enforced at activation |
| **Skill dependencies** | Other Skills or knowledge packs | Resolved at audit; version-pinned for `active` |
| **Skill capabilities** | Advertised affordances | For routing only; permissions from manifest + policy |
| **Skill quality state** | Audit/eval outcome | `unscored`, `eval_passed`, `eval_failed`, `waived_with_rationale` |
| **Skill provenance** | Lineage record | Required for adapted/imported Skills |
| **Tenant visibility** | Scope of registry visibility | `global` or `tenant_private` (optional `project_scoped`) |
| **Runtime eligibility** | Allowed execution contexts | Subset of platform runtimes |

### External source vs internal Skill

Two distinct object types:

```
ExternalSkillSource          InternalSkill (registry object)
├── import artifact          ├── skill_id
├── quarantine record        ├── manifest (authoritative permissions)
├── untrusted metadata       ├── SKILL.md (instructions only)
└── audit findings           └── lifecycle status
```

**Rules:**

- External Skills **never** become `active` directly.
- Import creates `external_import` source + `quarantined` registry stub.
- After audit, platform generates a **new internal manifest**; external metadata is not trusted.
- Methodology reuse (Adapt) and code reuse are **separate decisions** — registry records both.

### Lifecycle {#lifecycle}

Required states:

```
candidate → quarantined → audited → approved → active → deprecated → archived
```

Terminal / operational states (canonical set — **no `paused`**):

- `rejected` — permanent block after audit or policy
- `suspended` — **sole** temporary halt state (from `active`, `approved`, or `tenant_active`)

**Canonical lifecycle states:** `candidate`, `quarantined`, `audited`, `approved`, `active`, `suspended`, `deprecated`, `archived`, `rejected`. No other status names are permitted in SKILL-01+ contracts.

#### State definitions

| State | Activatable? | Visible to tenant? | Purpose |
|-------|--------------|--------------------|---------|
| `candidate` | No | Platform ops only | Discovered; RFC queued |
| `quarantined` | No | Platform ops only | Imported external; inspection sandbox |
| `audited` | No | Platform ops only | Audit complete; pending owner approval |
| `approved` | No* | Platform ops + preview tenants if flagged | Cleared for promotion |
| `active` | Yes (if runtime compatible) | Per tenant scope | Production-eligible |
| `deprecated` | Yes (existing bindings only) | Per tenant scope | Superseded; resolve for lineage |
| `archived` | No | Admin/audit read | Historical resolution only |
| `rejected` | No | Audit read | Permanent block |
| `suspended` | No | Ops + affected tenants | Incident response |

\* `approved` may allow **dry-run / eval** in designated sandbox runtime only — not customer production paths.

#### Valid transitions

| From | To | Trigger |
|------|-----|---------|
| `candidate` | `quarantined` | External import received |
| `candidate` | `audited` | Native skill submitted with complete package |
| `quarantined` | `audited` | Quarantine inspection passed |
| `quarantined` | `rejected` | Audit failed / hard reject |
| `audited` | `approved` | Owner/policy sign-off |
| `audited` | `rejected` | Failed audit |
| `approved` | `active` | Promotion + runtime compatibility verified |
| `active` | `deprecated` | New version promoted or commercial sunset |
| `deprecated` | `archived` | Retention period elapsed; no pending executions |
| `active` | `suspended` | Security incident / policy hold |
| `suspended` | `active` | Incident cleared |
| `suspended` | `archived` | Permanent removal after investigation |
| `approved` | `quarantined` | Regression found pre-activation |
| any non-terminal | `rejected` | Hard reject (e.g. license, security) |

#### Invalid transitions (hard deny)

- `quarantined` → `active` (skips audit and approval)
- `candidate` → `active` (skips audit and approval)
- `external_import` metadata → `active` without internal manifest generation
- `archived` → `active` (requires new version submission as `candidate`)
- `rejected` → `active` (requires new skill_id or explicit owner exception record)
- Cross-tenant promotion without scope change audit

### Tenant-private Skill lifecycle (Owner Decision 001)

Tenant-private Skills follow a **dedicated promotion path**. They **never** become globally visible automatically.

```
External Skill
  → quarantined
  → automated validation (RFC-SKILL-002 validator + RFC-SKILL-003 static checks)
  → tenant_private (registry scope set; not activatable)
  → tenant_active (activatable within owning tenant only)
  → platform audit (optional — required only for global promotion or elevated tools)
  → global / active (platform-owned; only after explicit owner approval)
```

**Rules:**

- Tenant may use **tenant_active** Skills **only inside own tenant** — no publication, no cross-tenant visibility.
- **Limited self-serve:** automated validation suffices for tenant-scoped activation with **non-elevated** tool sets (read-class connectors only; no write/billing/publication tools).
- **Platform audit mandatory** before: (a) global/`active` promotion, (b) any elevated tool grant, (c) sharing outside tenant.
- Tenant-private Skills **cannot** declare credentials; they reference tenant Connector credential bindings only (RFC-CONN-001).

### Registry invariants

1. Every `active` Skill has an **internal owner** (user or platform role).
2. Every `active` Skill has at least one **released version**.
3. Every execution records **`skill_id` + `skill_version`** in lineage (even if Skill logic is invoked via operator).
4. **Archived** Skills remain **resolvable** for historical lineage and audits.
5. One tenant **cannot see** another tenant's `tenant_private` Skill.
6. **Global Skills** are **platform-owned only** — tenants cannot publish global entries.
7. External Skills **never** skip `quarantined`.
8. **Deprecated** versions remain addressable; registry points `latest_active` separately.

### Registry lookup semantics

Conceptual query dimensions (implementation-agnostic):

| Lookup | Input | Result | Notes |
|--------|-------|--------|-------|
| By skill_id | `ms.skill.offer_builder` | Skill record + version list | Latest active version flagged |
| By version | `(skill_id, semver)` | Immutable Skill Version | 404 if not released |
| By capability | `research.competitor_analysis` | Ranked Skill Versions in `active`/`deprecated` | Filtered by tenant scope + runtime |
| By status | `quarantined` | Ops queue | Platform-only |
| By tenant scope | `tenant_id` | Global + tenant_private Skills | Never cross-tenant |
| By runtime compatibility | `assistant_explicit_run` | Eligible active Skills | Deny if incompatible |

**Resolution order at activation:**

1. Tenant scope check
2. Status ∈ {`active`, `deprecated` (if bound)}
3. Runtime compatibility
4. Dependency satisfaction
5. Registry policy (RFC-SKILL-003)
6. Approval preconditions

### Relationship to existing H2.2 registry

| H2.2 (`app/specialist_skills/`) | RFC-SKILL-001 target |
|---------------------------------|----------------------|
| Python inline definitions | Package + manifest (RFC-SKILL-002) |
| `draft` only | Full lifecycle through `archived` |
| `SpecialistSkillCode` enum | `skill_id` string + semver |
| `execution_policy=draft_only` | Runtime eligibility matrix |
| No provenance | Required for adapted Skills |

**Migration path (SKILL-01):** Existing draft skills become `candidate` or `platform_native` packages without changing runtime until loader ships.

### Skill ↔ Connector boundary

Skills **declare** `allowed_tools` referencing **Connector Tool IDs** in the Connector Registry (RFC-CONN-001). Skills do not embed MCP servers, credentials, or network endpoints.

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Filesystem-only Skill discovery (Agent Skills auto-activation) | No lifecycle, no tenant scope, no audit trail |
| Single combined Skill+MCP registry | Conflicts with SKILL-R0.1 separate contours |
| Immediate `active` on MIT license | License ≠ security; bypasses quarantine |
| Per-project Skill copies without versioning | Breaks lineage and patch propagation |
| Marketplace with user ratings as trust | Violates deny-by-default; Smithery-class risk |

---

## Security implications

- Lifecycle gates enforce quarantine and audit before any production eligibility.
- `suspended` provides emergency kill switch without deleting lineage.
- Tenant scope prevents cross-tenant Skill exfiltration via shared registry views.
- External import path is always `quarantined` first.

Details: [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md).

---

## Tenant implications

- Tenants may own `tenant_private` → `tenant_active` Skills per Owner Decision 001 — not global publication.
- **Self-serve path:** quarantine → automated validation → tenant_active (read tools only, within tenant).
- **Platform audit** required only before global promotion or elevated tools — not for basic tenant-private use.
- Global Skills visible to all tenants remain platform-controlled.
- Credential bindings stay in Connector layer — not in Skill registry entries (Owner Decision 002).

---

## Evidence implications

- Skills declare `required_evidence` in manifest; registry stores declaration, not evidence payloads.
- Verdict-class Skills (e.g. MS-SKILL-005 Market Validation) must reference Evidence contracts at `approved` promotion.
- Historical executions on `deprecated`/`archived` Skills retain evidence linkage via `skill_id` + `skill_version`.

---

## Approval implications

- `approved` → `active` requires owner or delegated policy sign-off recorded in provenance.
- Skills with write/publication/spend capabilities require explicit `approval_policy` in manifest.
- Registry does not execute approvals — it stores eligibility preconditions.

---

## Migration implications

1. Map H2.2 `SpecialistSkillDefinition` fields to manifest schema (RFC-SKILL-002).
2. Set all current skills to `candidate` or remain `draft` until SKILL-01 loader.
3. No DB migration in SKILL-R0.2.
4. MS-SKILL-001..007 enter as `candidate` with Adapt provenance from marketingskills.

---

## Owner decisions (SKILL-00.9)

| ID | Decision | Status |
|----|----------|--------|
| **OD-001** | Tenant-private Skills: quarantine → automated validation → tenant_private → tenant_active; platform audit only before global/elevated tools | **Accepted** |
| **OD-003** | Reject `paused`; use `suspended` as sole temporary halt | **Accepted** |

## Resolved open questions

| ID | Resolution |
|----|------------|
| **OQ-003** | **Resolved (OD-001):** Limited self-serve for tenant-private Skills within tenant; platform audit before global or elevated tools |
| **OQ-004** | **Resolved (OD-003):** `paused` rejected; H2.2 `paused` → `suspended` on migration |

## Remaining open questions

| ID | Question | Owner |
|----|----------|-------|
| OQ-001 | Should `approved` allow tenant preview runs before `active`? | Product |
| OQ-002 | Retention period for `archived` versions (years?) | Legal/Ops |
| OQ-005 | Single `latest_active` pointer vs semver range constraints per campaign | Product |

---

## Acceptance criteria

- [x] Lifecycle states and transitions documented and internally consistent with glossary
- [x] External vs internal Skill distinction explicit
- [x] Registry lookup dimensions defined without SQL/API
- [x] SKILL-R0.1 Adapt/Reject decisions preserved (no direct external activation)
- [x] H2.2 migration path noted
- [x] Cross-references to RFC-SKILL-002, RFC-SKILL-003, RFC-CONN-001 resolve
- [x] Owner decisions OD-001, OD-003 applied

---

## Next implementation phase

**SKILL-01 Foundation** (see [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)):

1. Contracts in `app/schemas/contracts.py` for Skill registry types (read-only)
2. Registry read model mirroring this RFC (no execution)
3. Import adapter stub → quarantine record only
4. Lineage field additions to execution records (nullable, backward compatible)

---

## Related documents

- [SKILL-CONN-glossary](SKILL-CONN-glossary.md)
- [RFC-SKILL-002 — Package Format](RFC-SKILL-002-skill-package-format.md)
- [RFC-SKILL-003 — Security](RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [RFC-CONN-001 — Connector Gateway](RFC-CONN-001-connector-gateway-and-private-registry.md)
- [Adopt-Adapt-Reject Matrix](../research/adopt-adapt-reject-matrix.md)
- [Source ecosystem comparison](../research/skills/source-ecosystem-comparison.md)
