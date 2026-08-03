# RFC-SKILL-004 — Skill Discovery and Draft Generation

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-SKILL-004 |
| **Status** | **Draft** |
| **Phase** | SKILL-R0.3 |
| **Depends on** | [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md), [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md), [RFC-SKILL-003](RFC-SKILL-003-skill-security-and-trust-boundary.md), [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) |
| **Blocks** | SKILL-02.5 Discovery, SKILL-04 Tenant Draft Generation |
| **Does not block** | SKILL-01 Foundation |

**Change history**

| Date | Change |
|------|--------|
| 2026-07-23 | Draft (SKILL-R0.3) — Discovery + Draft Generation architecture |

---

## Context

Marketsynth builds an AI marketing agency. Operators and customers need to know **which Skill fits a task** without installing external packages or bypassing governance.

Owner decision (2026-07-23): split into two independent contours:

1. **Skill Discovery (Skill Finder)** — read-only; recommends; never installs.
2. **Skill Draft Generation (Skill Generator)** — quarantine-only; never activates.

Rejected: single autonomous agent that finds, installs, and executes external Skills.

---

## Problem

Without formal Discovery and Draft Generation:

1. Operators cannot explain why an internal Skill was chosen over an external candidate.
2. Capability gaps remain invisible until manual audit.
3. Draft authoring is slow and inconsistent.
4. Auto-generators risk permission escalation, duplicate Skills, and false confidence from similarity scores.
5. Cursor or future implementers may collapse Discovery and Generation into one unsafe flow.

---

## Goals

1. Define **Skill Discovery** contract (input/output, ranking, gap report).
2. Define **Draft Generator** contract (outputs, status limits, permissions deny-by-default).
3. Preserve SKILL-R0.1 rejects (no marketplace install, no Smithery trust root).
4. Align with tenant model (OD-001) and architectural invariants.
5. Place implementation in SKILL-02.5 (Discovery) and SKILL-04 (Draft Generation).

---

## Non-goals

- Implementation in SKILL-R0.3 or SKILL-01
- Automatic Skill activation or composition
- External repository cloning into production
- MCP installation
- Marketplace UI
- Runtime execution of discovered or generated Skills
- API/DB implementation (conceptual contracts only)

---

## Decision

### System separation

**Discovery (read-only):**

```
Capability Analyzer
  → Internal Skill Finder
  → External Candidate Discovery
  → Gap Analyzer
  → Recommendation Report
```

**Draft Generation (quarantine-only, separate):**

```
Approved Gap / explicit owner trigger
  → Draft Generator
  → Static Validator (RFC-SKILL-002)
  → Duplicate Check
  → Quarantine
  → Audit
  → Owner Decision (RFC-SKILL-001 lifecycle)
```

Discovery **must not** invoke Draft Generation automatically without explicit human-approved trigger.

---

## Skill Discovery contract

### Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_description` | string | yes | Natural-language task |
| `tenant_id` | uuid | yes | Tenant scope |
| `project_id` | uuid | no | Project context |
| `required_capabilities` | string[] | no | Pre-normalized capabilities (optional if analyzer derives) |
| `available_context` | object | no | Sanitized project/brief context |
| `required_inputs` | object | no | Expected input shape hints |
| `expected_outputs` | object | no | Expected output shape hints |
| `runtime_constraints` | string[] | no | Allowed runtimes |
| `security_constraints` | object | no | Hard filters (no write tools, etc.) |
| `cost_constraints` | object | no | Budget/latency caps |
| `latency_constraints` | object | no | Max acceptable latency |
| `requested_quality` | enum | no | draft / standard / high |
| `allowed_tenant_scope` | enum[] | no | global, tenant_private |

### Output

| Field | Type | Description |
|-------|------|-------------|
| `normalized_task` | object | Capability Analyzer output |
| `required_capabilities` | string[] | Derived or confirmed capabilities |
| `internal_matches` | Match[] | Ranked internal Skill matches |
| `external_candidates` | ExternalCandidate[] | Discovery-only external references |
| `capability_gaps` | Gap[] | Missing or partial capabilities |
| `ranking_explanation` | string | Human-readable summary |
| `recommended_action` | enum | See below |
| `confidence` | enum | high / medium / low |
| `evidence` | object[] | Discovery lineage (not verdict Evidence) |
| `unresolved_questions` | string[] | Blockers for recommendation |

**Recommended action values:**

- `use_internal_skill`
- `review_alternatives`
- `adapt_external_methodology`
- `create_draft_recommended`
- `defer`
- `reject_task`
- `human_review_required`

### Match object (internal)

Each `internal_matches[]` entry includes:

| Field | Description |
|-------|-------------|
| `skill_id` | Registry id |
| `skill_version` | Semver |
| `status` | Registry status |
| `tenant_scope` | global / tenant_private |
| `capability_fit` | Qualitative + optional score range |
| `input_fit` | compatible / partial / incompatible |
| `output_fit` | compatible / partial / incompatible |
| `runtime_compatibility` | bool + notes |
| `security_class` | trust class |
| `quality_score` | eval score if available |
| `evidence_quality` | qualitative assessment |
| `estimated_cost` | optional; open calibration (OQ-D004) |
| `known_limitations` | string[] |
| `rejection_reasons` | string[] (if filtered out but listed) |
| `ranking_explanation` | per-match rationale |

### External candidate object

| Field | Description |
|-------|-------------|
| `source_id` | Discovery registry reference |
| `source_url` | Origin URL (if applicable) |
| `candidate_name` | Display name |
| `status` | always `external-candidate` |
| `license` | SPDX or unknown |
| `content_hash` | if package snapshot exists |
| `capability_fit` | qualitative |
| `adapt_only` | always true for production path |
| `rejection_reasons` | why not install |
| `ranking_explanation` | why listed |

---

## Discovery rules (mandatory)

1. Search **active** internal Skills first.
2. Search **tenant_active** / eligible tenant-private Skills second (current tenant only).
3. Search **approved** but inactive Skills only as recommendations — not auto-execution.
4. External sources are **discovery candidates only** — never installed during Discovery.
5. External candidate **cannot outrank** adequate active internal Skill solely on popularity/stars.
6. Status filtering mandatory.
7. Tenant scope filtering mandatory.
8. Runtime compatibility filtering mandatory.
9. Security constraints are **hard filters**.
10. Ranking must be **explainable** — similarity score alone insufficient.
11. Low-confidence results require `human_review_required`.
12. **No installation** during Discovery.
13. **No permissions granted** during Discovery.
14. **No external code execution** during Discovery.

---

## Ranking model (conceptual)

### Hard filters (deny before rank)

- Status ∉ eligible set for recommendation
- Tenant scope mismatch
- Runtime incompatible
- Security constraint violation (e.g. requires write tool when forbidden)
- Suspended / rejected / archived (unless historical explain mode)

### Qualitative priority (default)

1. Active internal Skill with full capability + I/O fit
2. Active internal Skill with partial fit + documented gaps
3. Tenant-private active Skill (same tenant)
4. Approved inactive internal Skill (recommend promotion/activation path)
5. External candidate — **Adapt only** recommendation
6. Gap → draft generation recommendation

### Provisional scoring (non-binding until benchmark)

Factors (weights **not frozen** — require benchmark OQ-D001):

- capability fit
- input compatibility
- output compatibility
- workflow-stage fit (CWF golden path)
- runtime compatibility
- tenant eligibility
- security compatibility
- Evidence support potential
- quality/eval score
- version stability
- maintenance state (deprecated penalty)
- cost estimate
- latency estimate
- known limitations

Every recommendation **must** include `ranking_explanation`.

---

## External discovery

### Allowed sources

- Marketsynth private candidate registry (quarantine store)
- Official Agent Skills repositories (metadata/index)
- Audited external repositories (e.g. marketingskills — Adapt reference)
- Official vendor documentation
- Approved discovery catalogs (Official MCP Registry — **discovery only**)

### Rules

| Source | Rule |
|--------|------|
| VoltAgent awesome-agent-skills | Discovery only — not trust root |
| Smithery | **Not** production trust root — reject auto-install |
| GitHub stars / npm downloads | **Not** trust signals |
| marketingskills | Methodology discovery — Adapt only |

Record for every external candidate: source identity, license, content hash (if available). Status remains `external-candidate`. No direct installation, execution, or automatic permission mapping.

---

## Capability gap report

Machine-readable `GapReport`:

| Field | Description |
|-------|-------------|
| `task` | Normalized task |
| `missing_capabilities` | string[] |
| `partially_covered_capabilities` | object[] |
| `internal_candidates_considered` | skill_id[] |
| `external_candidates_considered` | source_id[] |
| `why_existing_skills_are_insufficient` | string |
| `proposed_resolution` | enum |
| `draft_generation_recommended` | bool |
| `human_review_required` | bool |
| `evidence` | discovery lineage |
| `risk_class` | low / medium / high |

**Proposed resolution values:**

- `use_existing_skill`
- `compose_existing_workflow` — **document only; no auto-composition in this RFC**
- `adapt_external_methodology`
- `create_platform_native_draft`
- `create_tenant_private_draft`
- `defer`
- `reject_task`

---

## Draft generation

### Trigger

Draft Generation runs only when:

- Gap report recommends `create_platform_native_draft` or `create_tenant_private_draft`, **and**
- Explicit human or owner-approved system trigger (not Discovery auto-chain).

### Generator output (allowed)

- `SKILL.md` draft
- `manifest.yaml` draft
- input schema draft
- output schema draft
- test skeleton
- fixture skeleton
- provenance record
- known limitations
- audit checklist
- dependency **proposal** (not executable binding)

### Generator prohibitions

Must **not**:

- assign `active`, `approved`, `tenant_active` status
- grant tool permissions (`allowed_tools` must be `[]` by default)
- create credential bindings
- activate connectors
- create secrets
- execute scripts
- install external dependencies
- publish globally
- bypass quarantine
- bypass owner review

### Allowed generated statuses

- `candidate`
- `quarantined`

No other status may be generated.

### Permissions policy (generated drafts)

Default manifest for generated drafts:

```yaml
allowed_tools: []
network_policy:
  default: deny
script_policy:
  enabled: false
tenant_scope: tenant_private | global  # explicit; default tenant_private for tenant-triggered
```

**Owner field:** If manifest requires owner, use generator provenance:

- `owner: Marketsynth Draft System` — **generator provenance only**, not approval owner.
- Human approval owner recorded separately in audit trail.

---

## Duplicate detection

Checks before quarantine acceptance:

| Check | Result |
|-------|--------|
| Exact `skill_id` collision | **Stop** — unresolved collision blocks generation |
| Semantic capability overlap | manual_review / extension_candidate |
| Input/output equivalence | partial_overlap / duplicate |
| Methodology similarity | manual_review |
| Alias collision | manual_review |
| Version duplication | version_candidate |
| Tenant-private vs global overlap | manual_review |
| Deprecated replacement | extension_candidate |
| Fork lineage | manual_review |

Results: `no_conflict`, `version_candidate`, `extension_candidate`, `duplicate`, `partial_overlap`, `manual_review`.

---

## Security threat model

| Threat | Mitigation |
|--------|------------|
| Malicious external SKILL.md | Quarantine; text-only parse; no execution |
| Hidden prompt instructions | Static scan; normalization; human audit |
| Prompt injection | Sanitize; Discovery does not execute instructions |
| Tool poisoning | No tools in generated drafts by default |
| Encoded payloads | Content hash; structural validation |
| Path traversal | RFC-SKILL-002 path rules |
| Scripts | Disabled by default |
| Dependency confusion | Registry resolution; no auto-install |
| License laundering | License check + legal review gate |
| Provenance falsification | Signed audit records (future OQ-D005) |
| Fake quality signals | Eval required before active; no score-only trust |
| Ranking manipulation | Explainable ranking; hard filters |
| Repository impersonation | Source verification |
| Poisoned templates | Template subset restriction |
| Secret requests in SKILL.md | Secret pattern scan — fail validation |
| Cross-tenant candidate leakage | Tenant filtering on Discovery output |

---

## Human decision gates

| # | Decision | Required for |
|---|----------|--------------|
| 1 | Approve external methodology adaptation | Adapt path |
| 2 | Approve generated draft for audit | quarantined → audited |
| 3 | Approve permissions proposal | any allowed_tools non-empty |
| 4 | Approve connector requirements | connector dependency |
| 5 | Approve tenant activation | tenant_active |
| 6 | Approve global/platform promotion | global active |
| 7 | Approve elevated tools | write/billing/publication tools |
| 8 | Approve scripts | script_policy.enabled |
| 9 | Approve publication or billing capability | gated actions |

Discovery runs **without** approval (read-only). State transitions beyond `quarantined` follow [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md).

---

## Observability and evidence

### Discovery run record

- query/task hash
- tenant scope
- candidates searched (counts + ids)
- filters applied
- ranking factors (explanation blob)
- rejected candidates + reasons
- recommendation
- confidence
- source references
- timestamp
- discovery_engine_version

### Draft generation run record

- gap_report_id
- generator_version
- source materials (refs + hashes)
- content hash of generated package
- generated file list
- validation result
- duplicate-check result
- status (`candidate` or `quarantined`)
- human decision history

Do not log secret values or prohibited full tenant prompts per privacy policy.

---

## Tenant model

| Scope | Discovery | Draft generation |
|-------|-----------|------------------|
| Global metadata | Platform-approved Skills only | Platform-native drafts → quarantine |
| Tenant | Own tenant_private Skills visible | tenant_private draft → tenant quarantine |
| External | Candidate metadata — no tenant data | Sources must not embed tenant secrets |

No tenant-generated draft may become global without platform audit (OD-001).

---

## API and UI (conceptual — future, non-binding)

Possible future endpoints (SKILL-02.5 / SKILL-04):

- `POST /skill-discovery-runs`
- `GET /skill-discovery-runs/{id}`
- `POST /skill-gap-reports/{id}/generate-draft`
- `GET /skill-drafts/{id}`
- `POST /skill-drafts/{id}/submit-for-audit`

Possible UI concepts:

- recommended Skill + alternatives
- why selected / not selected
- missing capability panel
- create draft (explicit action)
- audit status + approval history

**Not implemented** until dedicated phases.

---

## Alternatives considered

| Alternative | Decision |
|-------------|----------|
| Automatic marketplace install | **Reject** |
| LLM chooses and executes external Skill | **Reject** |
| Similarity-only vector search | **Reject** as sole ranking |
| Internal registry search only | Insufficient long-term; acceptable **initial** SKILL-02.5 MVP |
| Manual authoring only | Safe but too slow as permanent strategy |
| Combined Discovery+Generator agent | **Reject** — privilege collapse |

---

## Security implications

Discovery is lower risk (read-only) but must not leak cross-tenant metadata. Draft Generation inherits RFC-SKILL-003 quarantine path. Generated drafts default to zero permissions.

---

## Tenant implications

Tenant Discovery sees own tenant_private Skills. Generated tenant drafts remain tenant-scoped until platform audit.

---

## Evidence implications

Discovery `evidence` field is **audit lineage**, not Citation Contract Evidence. Draft generation inherits RFC-SKILL-002 `required_evidence` declarations — defaults conservative.

---

## Approval implications

Discovery does not bypass Approval. Draft Generation cannot set approval bypass flags in manifest.

---

## Migration implications

None in SKILL-R0.3. Future SKILL-02.5 adds read model queries; SKILL-04 adds generator service behind quarantine.

---

## Open questions

| ID | Question |
|----|----------|
| OQ-D001 | Ranking benchmark dataset and weight calibration |
| OQ-D002 | Quality-score calibration vs eval suite |
| OQ-D003 | Cost estimation method for Discovery matches |
| OQ-D004 | External repository refresh cadence |
| OQ-D005 | Provenance signature format for generated drafts |
| OQ-D006 | Tenant quota for drafts per month |
| OQ-D007 | Human audit SLA for generated drafts |
| OQ-D008 | Allowed source licenses for external discovery |
| OQ-D009 | Multilingual Skill generation |
| OQ-D010 | Private business context minimization in Discovery logs |
| OQ-D011 | Duplicate-detection semantic threshold |

---

## Acceptance criteria (for future owner acceptance)

- [ ] Discovery and Draft Generation documented as separate systems
- [ ] Discovery read-only rules explicit
- [ ] Draft statuses limited to candidate/quarantined
- [ ] No automatic activation path
- [ ] External install remains rejected
- [ ] Roadmap updated with SKILL-02.5 and SKILL-04 placement

---

## Next implementation phase

| Phase | Scope |
|-------|-------|
| **SKILL-02.5** | Read-only Discovery against registry read model |
| **SKILL-04** | Draft Generator + quarantine + tenant review |

**Not before:** SKILL-01.8 freeze audit complete.

---

## Related

- [SKILL-ROADMAP.md](SKILL-ROADMAP.md) — KB-02–KB-06 future programs
- [KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md](KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md) — quarantined external intake
- [packages/knowledge/external_artifacts/0.1.0/](../../packages/knowledge/external_artifacts/0.1.0/) — artifact schemas for Discovery metadata

---

## KB-SKILL-01 read model (Discovery prep)

Deterministic catalog search over imported metadata (`app/knowledge/catalog/`) feeds future Discovery ranking — **no LLM, no vector DB, no install actions** in KB-SKILL-01.7.

## KB-WPL-01.8 read model (implemented)

**KB-WPL-01.8** (2026-07-24) implements deterministic read-only discovery over the frozen
Profession/Capability/Skill/Pattern model in `app/knowledge/discovery/`. See
[KB-WPL-01.8-KNOWLEDGE-DISCOVERY-READ-MODELS.md](KB-WPL-01.8-KNOWLEDGE-DISCOVERY-READ-MODELS.md).

- Bundle: `packages/knowledge/discovery/0.1.0/`
- `runtime_authorized=false` always
- Skill Generator / draft generation **not implemented** in this phase
- RFC-SKILL-004 draft generation remains future (KB-WPL-06)
- KB-WPL-01 program closed — see [KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md](KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md)

Allowed recommended actions: `use_internal_skill`, `review_methodology`, `adapt_workflow_pattern`, `inspect_error_pattern`, `request_security_review`, `defer`, `reject`.

Never: `install`, `execute`, `activate`, `deploy`.

---

## Related (original) documents

- [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md)
- [SKILL-ROADMAP](SKILL-ROADMAP.md)
- [SKILL-R0.3 summary](SKILL-R0.3-discovery-draft-rfc-summary.md)
- [SKILL-R0.1 audit](../research/SKILL-R0.1-candidate-audit-summary.md)
