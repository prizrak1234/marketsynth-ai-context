# SKILL-02.6A — Market Validation 0.2.0 Migration Design

| Field | Value |
|-------|-------|
| **Phase** | SKILL-02.6A |
| **Status** | **Design — pending owner review** |
| **Date** | 2026-07-23 |
| **Next** | SKILL-02.6B — `ms.skill.market_validation` 0.2.0 package |

---

## 1. Executive decision

Market Validation **0.2.0** is a **new immutable package version** — not a patch to frozen 0.1.0.

MV 0.2.0 becomes the first native Skill that **aggregates the full golden-path contour** before issuing a viability verdict:

```
PMC 0.2.x + MR 0.1.x + CA 0.1.x + CIM 0.1.x → MV 0.2.0 → viability verdict
```

**SKILL-02.6A delivers documentation and contract design only.** No package, no runtime, no CWF.1 migration.

Binding architecture:

```
ICP produces CIM → shared CIM schema defines contract → MV consumes CIM → verdict
Positioning / Offer consume MV + CIM — not the reverse
```

MV remains the **sole authorized viability verdict issuer** in the native Skill set. CIM does not issue verdict.

---

## 2. Version semantics

| Version | Identity | Status |
|---------|----------|--------|
| **0.1.0** | Frozen legacy skeleton | Immutable — hash `6c53b5b9…8133` |
| **0.2.0** | New golden-path aggregator | Design complete (02.6A); package in 02.6B |

**Rule:** `same skill_id + different version = distinct immutable package identity`. No in-place patch.

### 0.1.0 (frozen legacy)

- Standalone input (`idea_description`)
- All upstream deps declared_future or optional
- Legacy `decision` output contract mapping
- No CIM consumption
- Lineage-resolvable historical outputs

### 0.2.0 (new)

- Golden-path upstream refs required
- Explicit `output_contract_type: decision` in manifest
- Shared CIM v0.1.0 consumer
- Non-executable candidate until owner accepts execution

Detail: [market-validation-version-mapping.md](../skills/market-validation-version-mapping.md)

---

## 3. Dependency model

### Required constraints (0.2.0)

| Dependency | Constraint |
|------------|------------|
| `ms.skill.product_marketing_context` | `>=0.2.0,<1.0.0` |
| `ms.skill.market_research` | `>=0.1.0,<1.0.0` |
| `ms.skill.competitor_analysis` | `>=0.1.0,<1.0.0` |
| CIM (via `ms.skill.icp_segmentation`) | schema `>=0.1.0,<1.0.0` |

PMC 0.1.0 is **not** compatible with MV 0.2.0 (same rule as MR/CA/ICP chain).

### Required dependency payload fields

Each upstream reference must include:

`source_skill_id`, `source_skill_version`, `source_output_hash`, `source_status`, `source_evidence_references`, `source_unknowns`, `source_conflicts`, `provenance`

Missing identity or hash → **reject at package-schema level** (02.6B enforcement).

### Methodology chain (not runtime orchestration)

```
PMC 0.2.0 → MR 0.1.0 → CA 0.1.0 → ICP 0.1.0 → CIM 0.1.0 → MV 0.2.0
```

Hashes, evidence refs, unknowns, and conflicts preserved — not recomputed.

---

## 4. Verdict contract

Finite enum — **no synonyms, no hidden statuses:**

| Verdict | Semantic meaning |
|---------|------------------|
| `proceed` | Evidence supports next stage; no unresolved critical blocker |
| `proceed_with_conditions` | Progress only if explicit conditions satisfied |
| `revise` | Viable after material changes (segment, offer, model, pricing, geography, positioning assumption, execution) |
| `defer` | Wait — timing, evidence, operational readiness, or external conditions insufficient |
| `stop` | Unacceptable risk or lack of commercial rationale in scope |
| `insufficient_evidence` | No responsible verdict can be issued |

Preserved from MV 0.1.0 output schema. `output_contract_type: decision` with `verdict` discriminator per [SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md](SKILL-02-OUTPUT-CONTRACT-TAXONOMY.md).

**CIM must not contain:** `verdict`, `viable`, `unviable`, `proceed`, `stop`.

---

## 5. Decision dimensions

Fifteen finite dimensions with structured records (status, evidence refs, contradictions, assumptions, unknowns, confidence, blockers, notes):

`product_context_quality`, `market_evidence_quality`, `customer_evidence_quality`, `demand_signal_strength`, `competitor_pressure`, `segment_fit`, `reachability`, `budget_fit`, `pricing_plausibility`, `operational_feasibility`, `switching_difficulty`, `evidence_coverage`, `contradiction_severity`, `regulatory_or_external_constraints`, `critical_risks`

**No numeric production weights** until benchmark. Dimensions inform verdict; they do not auto-score.

Detail: [market-validation-decision-matrix.md](../skills/market-validation-decision-matrix.md)

---

## 6. Hard blockers

Eleven defined categories (HB-001 through HB-011):

- No identifiable customer problem
- No supported target segment
- Critical evidence contradiction
- Illegal/prohibited business model
- Impossible operational dependency
- Required budget materially unavailable
- Unacceptable compliance risk
- Demand evidence absent where required
- Unresolvable competitor disadvantage
- Missing provenance on critical evidence
- Decision based primarily on unsupported inference

**Hard blocker does not always force `stop`.** Mapping depends on remediation:

| Remediation | Verdict |
|-------------|---------|
| None | `stop` |
| Material change possible | `revise` |
| Timing/external | `defer` |
| Evidence gap only | `insufficient_evidence` |
| Clearable via conditions | `proceed_with_conditions` |

Invalid: `proceed` with critical blocker present.

---

## 7. Conditions model

Structured conditions for `proceed_with_conditions`:

`condition_id`, `category`, `statement`, `required_action`, `owner`, `deadline_or_gate`, `evidence_required`, `blocking`, `validation_method`, `status`

No free-text-only conditions.

---

## 8. Risk model

Finite domains: `market`, `customer`, `competitor`, `pricing`, `financial`, `operational`, `legal`, `compliance`, `timing`, `channel`, `evidence`, `execution`

Each risk: `risk_id`, `domain`, `description`, `likelihood`, `impact`, `severity`, `evidence_references`, `assumptions`, `mitigations`, `residual_risk`, `blocking`, `owner_review_required`

**No unsupported probability percentages.**

Output: `critical_risks[]` + `noncritical_risks[]`.

---

## 9. CWF.1 mapping

Documented without runtime change. See full table in [market-validation-version-mapping.md](../skills/market-validation-version-mapping.md).

| BIV runtime | MV 0.2.0 | Notes |
|-------------|----------|-------|
| `proceed` | `proceed` | Direct |
| `proceed_with_conditions` | `proceed_with_conditions` | Direct |
| `revise` | `revise` | Direct |
| `reject` | `stop` | Requires adapter |
| `insufficient_evidence` | `insufficient_evidence` | Direct |
| — | `defer` | **Unknown** — no BIV equivalent |

**Do not invent equivalence.** CWF.1 remains live path; MV package is non-executable until owner accepts.

---

## 10. Output contract (02.6B design)

Conceptual fields — see [market-validation-consumer-contracts.md](../skills/market-validation-consumer-contracts.md):

**Identity:** `validation_id`, `skill_id`, `skill_version`, four upstream refs, hashes, provenance

**Decision:** `decision_readiness`, `verdict`, `verdict_confidence`, `executive_summary`, `decision_dimensions`, `blockers`, `conditions`, risks

**Evidence:** `supporting_evidence`, `contradictory_evidence`, `assumptions`, `inferences`, `unknowns`, `conflicts`

**Guidance:** `required_changes`, `next_validation_steps`, `recommended_next_stage`, `human_approval_required`

**Forbidden:** `positioning`, `final_offer`, `campaign`, `execution_status`, `publication`, `connector_result`

---

## 11. Decision readiness

Pre-verdict gate — **not** the final verdict:

| Readiness | Meaning |
|-----------|---------|
| `ready_for_decision` | Upstream refs complete; dimensions assessable |
| `partially_ready` | Partial assessment possible |
| `insufficient_evidence` | Cannot assess responsibly |
| `conflicted` | Critical upstream contradiction |
| `out_of_scope` | Outside declared scope |

### Rules

- Readiness `insufficient_evidence` or `conflicted` → verdict only `insufficient_evidence` or `defer`
- Hard contradiction → no `proceed`
- Missing CIM → no `proceed`
- Unsupported segment → no `proceed`
- Missing critical provenance → no `high` confidence

---

## 12. Confidence discipline

Finite: `high`, `medium`, `low`, `unknown`

High requires: source-backed critical dimensions, no critical contradiction, adequate coverage, explicit provenance, current evidence where time-sensitive.

No numeric scores without benchmark.

---

## 13. Consumer boundaries

| Consumer | May consume from MV | Must not |
|----------|---------------------|----------|
| Positioning | Verdict conditions, risks, segment refs, evidence | Reinterpret stop→proceed; recompute CIM |
| Offer Builder | Permitted downstream state, conditions | Ignore blockers; redefine customer model |
| Launch Strategy | Verdict, conditions, next stage | Execute spend/ads |
| Owner / CWF UI | Verdict, summary, blockers | Auto-approve launch |
| CWF adapter (future) | MV output for parity | Modify CWF.1 in 02.6A |

Detail: [market-validation-consumer-contracts.md](../skills/market-validation-consumer-contracts.md)

---

## 14. Legacy compatibility

| Aspect | 0.1.0 → 0.2.0 status |
|--------|----------------------|
| Input model | **incompatible** |
| Verdict enum | **compatible** (same 6 values) |
| Output structure | **requires_adapter** |
| Historical 0.1.0 outputs | **compatible** (lineage-resolvable) |
| Automatic migration | **Not promised** |

0.2.0 has the right to be incompatible with 0.1.0 input if honestly documented.

---

## 15. 02.6B test plan

Sixteen fixture classes defined in [market-validation-consumer-contracts.md](../skills/market-validation-consumer-contracts.md):

Proceed, proceed_with_conditions, revise (segment/pricing), defer, stop, insufficient_evidence, conflicted upstream, missing CIM, missing hash, unsupported high-confidence, verdict without evidence, stop without blocker, proceed with blocker, consumer compatibility, legacy mapping.

Target test file: `tests/test_skill_02_6_market_validation_v020.py` (02.6B).

---

## 16. Accepted limitations

- No MV 0.2.0 package in 02.6A
- No runtime execution or CWF.1 migration
- No numeric scoring weights
- No Connector access, persistence, API, UI, MCP
- `defer` CWF mapping remains Unknown
- RFC-SKILL-004 remains Draft

---

## 17. Non-goals (02.6A)

MV 0.2.0 package, runtime execution, CWF.1 migration, Positioning, Offer Builder, Connector access, web research, persistence, API, UI, approval workflow, automatic scoring, ML model, Discovery, Draft Generator, MCP.

---

## 18. Verification checklist

| Check | Result |
|-------|--------|
| No package under MV 0.2.0 | ✓ |
| MV 0.1.0 unchanged | ✓ (hash verified) |
| CIM bundle unchanged | ✓ |
| No CWF.1 code changes | ✓ |
| No runtime/API/DB/UI changes | ✓ |
| RFC-SKILL-004 remains Draft | ✓ |

---

## 19. Freeze verdict (02.6A)

**DESIGN COMPLETE — pending owner review.**

After owner acceptance → **SKILL-02.6B** implements `packages/skills/ms.skill.market_validation/0.2.0/`.

After 02.6B freeze → **SKILL-02.7 Positioning** (CIM consumer, not segmentation engine).

---

## Related documents

- [Version Mapping](../skills/market-validation-version-mapping.md)
- [Decision Matrix](../skills/market-validation-decision-matrix.md)
- [Consumer Contracts](../skills/market-validation-consumer-contracts.md)
- [SKILL-02.5 CIM Freeze](SKILL-02.5-CIM-SHARED-SCHEMA-FREEZE.md)
- [CIM Consumer Contracts v0.1.0](../knowledge/CIM-consumer-contracts-v0.1.0.md)
- [ms.skill.market_validation](../skills/ms.skill.market_validation.md)
