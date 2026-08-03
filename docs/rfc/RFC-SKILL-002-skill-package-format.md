# RFC-SKILL-002 — Skill Package Format

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-SKILL-002 |
| **Status** | **Accepted** |
| **Approved by Owner** | 2026-07-23 |
| **Phase** | SKILL-R0.2 → SKILL-00.9 acceptance |
| **Depends on** | [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md), [Agent Skills spec](https://agentskills.io/specification) (reference) |
| **Blocks** | SKILL-01 package validator, import adapter |

**Change history**

| Date | Change |
|------|--------|
| 2026-07-23 | Draft (SKILL-R0.2) — MSP layout and manifest schema |
| 2026-07-23 | **Accepted (SKILL-00.9)** — aligned with OD-001 tenant-private validation path |

---

## Context

SKILL-R0.1 **Adopts** the [Agent Skills specification](https://agentskills.io/specification) for **package structure patterns** — not for wholesale installation of external skills. The marketingskills corpus (MIT) and Anthropic skills repo demonstrate `SKILL.md` + resource folders, but Marketsynth requires **manifest-authoritative permissions**, Evidence gates, tenant scope, and quarantine for imports.

This RFC defines the **Marketsynth Skill Package (MSP)** format — compatible with an import adapter for external Agent Skills packages, but stricter on security and governance.

---

## Problem

Without a canonical package format:

1. Instructions (SKILL.md) would be treated as permission source — unsafe.
2. External packages could not be consistently quarantined and audited.
3. Versioning, checksums, and eval suites would be ad hoc.
4. Adapt path for MS-SKILL-001..007 lacks a target artifact shape.

---

## Goals

1. Define directory layout, manifest schema, and validation rules.
2. Separate **instruction content** from **security permissions**.
3. Specify import adapter behavior for external Agent Skills (quarantine only).
4. Enable deterministic validation before registry promotion (RFC-SKILL-001).
5. Align with subsystem standard: contracts, quality gates, tests.

---

## Non-goals

- Runtime loader implementation
- Script execution engine
- Automatic conversion of marketingskills repo
- Tenant upload UI
- Skill marketplace packaging
- Modifying existing Python specialist_skills execution

---

## Decision

### Package layout

```
skill/
├── SKILL.md                 # Instruction content (required)
├── manifest.yaml            # Authoritative metadata + permissions (required)
├── resources/               # Reference docs, examples (optional)
├── templates/               # Output templates (optional)
├── schemas/                 # JSON Schema for inputs/outputs (optional but recommended)
├── tests/                   # Eval cases + fixtures (required for platform-native active)
└── scripts/                 # Optional; DISABLED by default
```

**Root rule:** All paths MUST be relative to package root. No `..` segments. Symlinks forbidden in production packages.

#### Transitional versioning (SKILL-02.2.1+)

During native Skill rollout, **legacy frozen versions may remain at package root** while **new semver releases live in nested directories** (e.g. `0.2.0/`). See [SKILL-02-transitional-version-layout.md](SKILL-02-transitional-version-layout.md).

- Root directory is **not** “latest version”.
- Registry identity is always `skill_id + version + package_hash`.
- `latest_known_version` comes from registry semantics, not filesystem layout.
- Parent-root hashing excludes nested semver sibling directories.


#### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Registry skill_id (matches RFC-SKILL-001) |
| `name` | string | Human display name |
| `version` | semver | Immutable release version |
| `description` | string | Routing summary (≤ 500 chars recommended) |
| `owner` | string | Platform role or tenant owner reference |
| `source` | enum | `platform_native`, `platform_adapted`, `tenant_private`, `external_import` |
| `license` | string | SPDX identifier or `Proprietary` |
| `status` | enum | Lifecycle state at package build time (must match registry) |
| `capabilities` | string[] | Declared capability IDs |
| `activation_conditions` | object | Runtime, tenant, prerequisite rules |
| `required_inputs` | object | Input contract (schema ref or inline) |
| `output_schema` | object | Primary output contract |
| `required_evidence` | object | Evidence types and minimum confidence rules |
| `dependencies` | object | Skill and knowledge pack dependencies |
| `allowed_tools` | string[] | Connector Tool IDs only — empty = no tools |
| `approval_policy` | object | When human/policy approval required |
| `tenant_scope` | enum | `global` or `tenant_private` (+ optional project list) |
| `quality_threshold` | object | Eval pass criteria |
| `known_limitations` | string[] | Honest capability bounds |
| `test_suite` | object | Pointer to tests/ manifest |
| `provenance` | object | Lineage (required if source ≠ platform_native) |

#### Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `supersedes_version` | semver | Previous version replaced |
| `runtime_compatibility` | string[] | Allowed runtimes |
| `knowledge_scopes` | string[] | Governed knowledge domains |
| `network_policy` | object | Egress declarations (usually deny-all) |
| `script_policy` | object | Script enablement (default disabled) |
| `resource_limits` | object | Size/token bounds |
| `localization` | object | Locale-specific metadata |
| `tags` | string[] | Discovery tags (non-authoritative) |

#### Semantic versioning rules

- **MAJOR:** Breaking change to `required_inputs`, `output_schema`, or `allowed_tools` semantics
- **MINOR:** Backward-compatible capability or optional input additions
- **PATCH:** Instruction fixes, template tweaks, eval additions without contract change

Released versions are **immutable**. Fixes require new patch version and re-audit if permissions change.

### Content integrity

| Mechanism | Rule |
|-----------|------|
| **Content hash** | SHA-256 over canonical tarball of all files except signature block |
| **Package checksum** | Recorded in registry provenance at import/publish |
| **Manifest hash** | Included in content hash; manifest must list `files` with per-file hashes (recommended) |
| **Deterministic validation** | Same bytes → same validation outcome on any validator version pinned in audit record |

### Resource path rules

- Allowed characters: `[a-zA-Z0-9._/-]`
- Max path length: 256 chars
- Max depth: 8 levels
- Forbidden: absolute paths, `..`, Windows drive prefixes, null bytes
- **Maximum package size:** 10 MiB default (platform may raise for vetted publishers)
- **Supported file types:** `.md`, `.yaml`, `.yml`, `.json`, `.txt`, `.csv`, `.jinja2`, `.html` (templates sanitized at render), `.py` (scripts/ only, disabled by default)

### SKILL.md role

`SKILL.md` contains **operator instructions**: methodology, tone, steps, examples.

**SKILL.md is NOT authoritative for:**

- Tool permissions
- Network access
- Credential access
- Approval bypass
- Tenant scope

Security permissions **MUST** come from `manifest.yaml` + registry policy (RFC-SKILL-003).

Progressive disclosure pattern (from Agent Skills): routing uses `description` + `capabilities`; full SKILL.md loaded only at activation.

### scripts/ policy

| Default | Rule |
|---------|------|
| Disabled | `script_policy.enabled: false` unless explicit audit approval |
| No network | Scripts cannot declare network in manifest unless platform enables sandbox profile |
| No secrets | Scripts cannot access env secrets; platform injects nothing |
| Static scan | Required before `audited` promotion |
| Execution | Only in isolated runner with CPU/time limits — **SKILL-01+** |

### network_policy (default)

```yaml
network_policy:
  default: deny
  allowed_hosts: []          # empty unless audited exception
  allowed_connectors_only: true
```

All external I/O MUST go through declared Connector Tools in `allowed_tools`.

### secret_policy (default)

```yaml
secret_policy:
  skill_may_embed_secrets: false
  skill_may_reference_credential_bindings: false  # bindings live in Connector layer
```

### tests/ requirements

For `platform_native` Skills targeting `active`:

- Minimum one eval case per declared capability
- Fixtures must not contain live secrets
- Eval results stored in audit record at promotion

Adapted Skills (MS-SKILL-001..007): eval suite may start as **waived_with_rationale** in pilot with dated remediation.

### Deterministic validation pipeline

```
Package bytes
  → schema validate manifest.yaml
  → path traversal scan
  → file type allowlist
  → size limits
  → hash computation
  → script static scan (if scripts present)
  → SKILL.md sanitization check (no credential patterns)
  → cross-check allowed_tools exist in Connector Registry (or stubbed for SKILL-01)
  → output validation result { pass | fail, findings[] }
```

Validation runs at: import, pre-audit, pre-active promotion.

### External Agent Skills compatibility

| Rule | Behavior |
|------|----------|
| Import adapter | **Allowed** — converts external layout to quarantine record |
| Direct execution | **Forbidden** |
| Entry state | Always `quarantined` |
| External metadata | **Not trusted** — stored as `external_manifest_snapshot` only |
| Internal manifest | Generated only after audit; may differ materially from source |
| SKILL.md | May be copied/adapted; instructions reviewed for injection |
| External scripts | Stripped or left inert unless separate script audit |

**marketingskills / Anthropic bundled skills:** Import for audit only; **Reject** direct production install per SKILL-R0.1.

Example import flow:

```
External package (agentskills.io layout)
  → Import Adapter
  → Quarantine blob + external_manifest_snapshot
  → Audit (RFC-SKILL-003)
  → New internal manifest.yaml (platform_adapted)
  → Registry lifecycle (RFC-SKILL-001)
```

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| SKILL.md-only packages (Agent Skills default) | No permission boundary; prompt injection surface |
| Python module as Skill package | Ties skills to deploy cycle; harder tenant isolation |
| JSON-only manifest without SKILL.md | Loses progressive disclosure and operator readability |
| Blind copy of Anthropic manifest fields | Missing Evidence, tenant_scope, approval_policy |
| Git submodule as package source | Supply chain risk; non-deterministic checkout |

---

## Security implications

- Manifest-authoritative permissions prevent instruction escalation (RFC-SKILL-003).
- Path traversal and file type rules reduce archive bombs and polyglot files.
- Scripts disabled by default reduces arbitrary code execution surface.
- External import quarantine mandatory.

---

## Tenant implications

- `tenant_scope: tenant_private` packages must include tenant owner in manifest.
- Global packages require platform publisher role.
- Package validation enforces scope before registry write.

---

## Evidence implications

- `required_evidence` block mandatory for research/verdict Skills.
- Output schema should reference Evidence attachment points for Citation Contract compliance.

---

## Approval implications

- `approval_policy` enumerates triggers: `on_write_tool`, `on_publication`, `on_paid_action`, `on_launch_verdict`.
- Empty approval_policy does not imply auto-approve for write tools — registry policy defaults to require approval.

---

## Migration implications

1. H2.2 Python skill definitions export to MSP layout as `candidate` packages.
2. No runtime reads MSP until SKILL-01 validator + read model.
3. marketingskills Adapt: manual or semi-automated import → quarantine → rewrite manifest.

---

## Open questions

| ID | Question | Default proposal |
|----|----------|------------------|
| OQ-101 | Include `files[]` hash list in manifest or sidecar `manifest.lock`? | Sidecar for immutability |
| OQ-102 | Jinja2 in templates — allow or restrict to Mustache subset? | Restrict subset at first |
| OQ-103 | Max SKILL.md size? | 256 KiB |
| OQ-104 | Sign packages with platform key at publish? | Yes — SKILL-01 optional phase |
| OQ-105 | Map Agent Skills `compatibility` field — adopt name or MS-specific? | MS-specific `runtime_compatibility` |

---

## Acceptance criteria

- [x] Directory layout and required manifest fields defined
- [x] Required vs optional fields explicit
- [x] Immutability, hashing, validation pipeline specified
- [x] External import → quarantine → internal manifest path documented
- [x] SKILL.md non-authoritative for security stated clearly
- [x] Consistent terminology with glossary

---

## Next implementation phase

**SKILL-01** (see [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)):

1. `manifest.yaml` JSON Schema in repo (validation only)
2. CLI validator driven by MS-SKILL-001 Market Validation skeleton
3. Import adapter producing quarantine record (no activation)
4. Automated validation gate for tenant-private path (OD-001)

---

## Related documents

- [RFC-SKILL-001 — Registry & Lifecycle](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-003 — Security](RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [SKILL-CONN-glossary](SKILL-CONN-glossary.md)
- [Source ecosystem comparison](../research/skills/source-ecosystem-comparison.md)
- [Adopt-Adapt-Reject Matrix](../research/adopt-adapt-reject-matrix.md)
