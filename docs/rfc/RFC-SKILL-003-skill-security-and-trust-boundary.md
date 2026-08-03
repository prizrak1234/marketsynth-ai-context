# RFC-SKILL-003 — Skill Security & Trust Boundary

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-SKILL-003 |
| **Status** | **Accepted** |
| **Approved by Owner** | 2026-07-23 |
| **Phase** | SKILL-R0.2 → SKILL-00.9 acceptance |
| **Depends on** | [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md), [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md), [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md) |
| **Blocks** | SKILL-01 security validator, audit runbook |

**Change history**

| Date | Change |
|------|--------|
| 2026-07-23 | Draft (SKILL-R0.2) — threat model and invariants |
| 2026-07-23 | **Accepted (SKILL-00.9)** — OD-001 tenant-private self-serve bounds; OQ-003/OQ-302 resolved |

---

## Context

SKILL-R0.1 identified systemic risks: MCP ecosystem immaturity, Telegram userbot MCPs, ad platform spend surfaces, Smithery supply-chain incidents, and prompt-injection via untrusted skill content. Marketsynth already enforces Approval, Evidence, and Source-of-Truth gates in CWF.1 — Skill security must **extend** those invariants, not create parallel bypass paths.

This RFC defines the **deny-by-default** trust model for Skills from quarantine through execution and revocation.

---

## Problem

Skills combine **instructions**, **resources**, **optional scripts**, and **tool declarations**. Without explicit trust boundaries:

1. Hidden instructions could escalate permissions at runtime.
2. Imported marketing skills could exfiltrate tenant data via undeclared tools.
3. Scripts could execute with platform credentials.
4. Dependency confusion could swap vetted packages.
5. External reputation (MIT license, GitHub stars) could be mistaken for production trust.

---

## Goals

1. Document threat model and mitigations.
2. Define trust classes and quarantine → activation audit requirements.
3. Specify hard invariants (non-negotiable).
4. Align Skill security with Connector Gateway (tools only via allowlist).
5. Preserve SKILL-R0.1 rejects (Telegram MCP, ad MCPs, Smithery trust root).

---

## Non-goals

- Implementing sandbox runtime, WAF, or SIEM
- Penetration testing or formal verification
- Changing CWF.1 approval/evidence execution code
- Credential vault implementation
- MCP server installation

---

## Decision

### Security model (deny-by-default)

```
Skill activation request
  → declared capabilities (manifest)
  → registry policy (status, tenant, runtime)
  → runtime policy (global deny-by-default)
  → tool-level allowlist (Connector Tools only)
  → tenant-scoped credentials (Connector layer)
  → approval gate (writes / spend / publish / verdict)
  → evidence log (lineage + audit record)
```

Each layer may **only restrict** — no layer may grant permissions not declared in manifest + registry.

### Threat model

| Threat | Description | Primary mitigation |
|--------|-------------|-------------------|
| **Prompt injection** | Malicious content in SKILL.md/resources steers model to unsafe actions | Sanitize; manifest permissions; tool allowlist; human approval on writes |
| **Tool poisoning** | Skill declares benign tool; runtime swaps implementation | Connector Registry versioning; gateway integrity; no dynamic tool registration from Skill |
| **Malicious scripts** | `scripts/` exfiltrates data or mines crypto | Disabled by default; static scan; isolated runner if enabled |
| **Hidden instructions** | White-on-white text, metadata fields, resource steganography | Resource scan; manifest diff vs external snapshot; eval behavioral tests |
| **Network exfiltration** | Skill reaches arbitrary URLs | `network_policy.default: deny`; connectors only |
| **Secret access** | Skill reads env or credential store | Hard invariant: Skills cannot access secrets |
| **Filesystem escape** | Path traversal in package or runtime | Package path rules; sandbox chroot — SKILL-01+ |
| **Tenant data leakage** | Cross-tenant context in shared runner | Tenant scope enforcement; isolated execution context |
| **Dependency confusion** | Wrong skill version or typosquat id | Registry resolution; semver pinning; provenance |
| **Supply-chain compromise** | Tampered upstream repo or marketplace | Quarantine; content hash; no auto-update from external |
| **Unsafe template rendering** | Jinja2 RCE or SSTI | Restricted template subset; no arbitrary code in templates |
| **Arbitrary code execution** | Python/shell in scripts | Scripts off by default; explicit audit for enablement |
| **Excessive tool permissions** | Broad MCP server install | Reject server-level trust; tool-level allowlist mandatory |

### Hard invariants

1. **Skill cannot access secrets directly.**
2. **Skill cannot define credentials** — credential bindings live in Connector layer only.
3. **Skill cannot expand its own permissions** at runtime (manifest is ceiling).
4. **Skill cannot invoke undeclared tools** — `allowed_tools` is exhaustive allowlist.
5. **Skill cannot cross tenant boundaries** — scope enforced at registry + runtime.
6. **Skill cannot bypass Approval** for gated action classes.
7. **Skill cannot bypass Evidence** for declared `required_evidence`.
8. **Skill cannot bypass SoT** — governed knowledge snapshots only where domain requires.
9. **Skill scripts are disabled unless explicitly approved** in audit record.
10. **External Skill is never production-trusted by source reputation alone** — audit + internal manifest required.

Violation of any invariant → block activation or immediate `suspended` + incident record.

### Trust classes {#trust-classes}

| Class | Source | Production default | Audit depth |
|-------|--------|-------------------|-------------|
| `platform-native` | Marketsynth-authored MSP | Eligible after standard audit | Full eval suite |
| `platform-adapted` | External methodology/code adapted | Eligible after Adapt audit + attribution | Full + provenance review |
| `tenant-private` | Tenant-submitted MSP | Eligible after automated validation → `tenant_active` within tenant (OD-001); platform audit before global/elevated | Automated + capped tools; full audit before global |
| `external-candidate` | Imported Agent Skills package | **Never** — quarantine only | Import scan |
| `rejected` | Failed audit / SKILL-R0.1 hard reject | **Never** | N/A |

**SKILL-R0.1 preserved rejects (must not appear as `active`):**

- Telegram MCP skills/tools — use native publication (AI.70–75)
- Ad platform MCP bundles (Google/Meta/Yandex Direct)
- Smithery / hosted MCP proxy as trust root
- marketingskills / Anthropic drop-in without Adapt audit

### Quarantine process

1. **Receive** external bytes → store immutable blob with hash.
2. **Isolate** — no network, no tool access, no LLM execution on live tenant data.
3. **Register** stub with status `quarantined` (RFC-SKILL-001).
4. **Queue** for static inspection.

### Static inspection (required)

| Check | Applies to |
|-------|------------|
| Manifest schema validation | All packages |
| Path traversal / file type / size | All packages |
| Secret pattern scan (API keys, tokens) | All files |
| License file presence + SPDX match | Adapted/external |
| `allowed_tools` resolution vs Connector Registry | All with tools |
| Script AST / import analysis | If scripts/ present |
| SKILL.md injection heuristics | All packages |
| Dependency version pinning review | If dependencies declared |

### Behavioral tests & evals

Before `audited` → `approved`:

- Run declared `tests/` suite against sandbox fixtures
- For verdict-class Skills: confirm insufficient evidence blocks positive output
- For tool-using Skills: confirm undeclared tool call attempts fail closed
- Record eval artifact IDs in provenance

### Approval (security gate)

Security approval recorded separately from product owner approval:

| Requirement | Approver |
|-------------|----------|
| New `platform_adapted` Skill | Security + product owner |
| Script enablement | Security mandatory |
| Network exception | Security mandatory |
| Tenant-private with write tools | Security mandatory |
| Pilot waiver on eval suite | Security + dated remediation ticket |

### Revocation & emergency suspension

| Trigger | Action |
|---------|--------|
| CVE in dependency | `suspended` all affected versions |
| Prompt injection exploit | `suspended` + eval reproducer added |
| Tool policy drift | Block activation; Connector must re-audit |
| Owner recall | `deprecated` → `archived` per RFC-SKILL-001 |

Revocation does not delete historical execution lineage.

### Required audit evidence before activation

Minimum audit bundle for `platform-native` / `platform-adapted` → `active`:

1. Static inspection report (pass)
2. Content hash + manifest hash
3. Eval suite results (pass or waived with rationale)
4. Provenance record (source URL, commit, license, adapter version)
5. Security sign-off record
6. Product owner sign-off record
7. Connector tool allowlist snapshot (ids + versions)
8. Known limitations acknowledged in manifest

---

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Trust by license (MIT = safe) | SKILL-R0.1 explicit reject |
| Runtime LLM moderation only | Insufficient for tool/spend/publish |
| Server-level MCP allowlist | SKILL-R0.1: tool-level mandatory |
| Tenant self-audit without platform review | Cross-tenant and spend risk |
| Permanent trust after first audit | No revocation path |

---

## Security implications

This RFC is the security specification. Implementation must fail closed on validator errors.

---

## Tenant implications

- Tenant-private Skills (OD-001): **automated validation** suffices for `tenant_active` within tenant with read-class tools only.
- **Platform security audit mandatory** before global promotion or elevated/write/billing/publication tools.
- Tenants cannot disable Evidence or Approval via manifest flags.
- Cross-tenant leakage tests required in platform-native eval harness.

---

## Evidence implications

- Invariant 7: Skills declaring research/verdict outputs must emit Evidence or block.
- Audit records themselves are Evidence-class artifacts for compliance.

---

## Approval implications

- Invariant 6: `approval_policy` + registry defaults; no silent writes.
- Launch verdict Skills require explicit approval mapping to CWF.1 gates.

---

## Migration implications

- H2.2 draft skills treated as pre-audit; no elevation without MSP + audit bundle.
- Existing operator runs without skill_version lineage get nullable fields until backfill.

---

## Resolved open questions

| ID | Resolution |
|----|------------|
| **OQ-003** | **Resolved (OD-001):** Limited self-serve for tenant-private; platform audit before global/elevated |
| **OQ-302** | **Resolved (OD-001):** Tenant-private may activate within tenant after automated validation — not zero audit, but no full platform audit unless elevated/global |

## Remaining open questions

| ID | Question |
|----|----------|
| OQ-301 | Automated injection red-team frequency per Skill version? |
| OQ-303 | Third-party commercial pen test before first adapted Skill active? |
| OQ-304 | Skill signing key rotation policy |

---

## Acceptance criteria

- [x] Threat model covers SKILL-R0.1 findings
- [x] Ten hard invariants listed and non-contradictory with RFC-CONN-001
- [x] Trust classes map to lifecycle states
- [x] Quarantine → audit → approval path complete
- [x] External reputation explicitly insufficient for trust
- [x] See also [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) for constitutional layer (20 invariants)

---

## Next implementation phase

**SKILL-01** (see [SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN](SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)):

1. Static validator implementing inspection checklist (no runtime)
2. Audit report schema (JSON, stored alongside quarantine blob)
3. Security sign-off template in runbook
4. Fail-closed tool resolution against Connector Registry read model

---

## Related documents

- [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md)
- [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md)
- [SKILL-CONN-glossary](SKILL-CONN-glossary.md)
- [SKILL-R0.1 summary § Critical security findings](../research/SKILL-R0.1-candidate-audit-summary.md)
- [External execution boundaries](../external_execution_boundaries.md)
