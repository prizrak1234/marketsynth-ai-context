# Market Validation — Decision Matrix

**Phase:** SKILL-02.6A  
**Status:** Design — pending owner review  
**Scope:** Contract design only; no numeric weights, no runtime scoring

---

## Purpose

Define a **finite decision structure** so MV 0.2.0 verdicts depend on explicit dimensions, evidence references, and hard blockers — not on persuasive LLM prose alone.

Numeric production weights remain **open** until benchmark (02.6B+). Hard blockers are defined now.

---

## Pre-verdict readiness

Readiness is **not** the final verdict. It gates whether a responsible verdict may be issued.

| Status | Meaning |
|--------|---------|
| `ready_for_decision` | Required upstream refs present; dimensions assessable |
| `partially_ready` | Some dimensions assessable; gaps documented |
| `insufficient_evidence` | Cannot assess critical dimensions responsibly |
| `conflicted` | Unresolved critical contradiction across upstream sources |
| `out_of_scope` | Request outside declared market/geography/scope |

### Readiness → verdict rules

| Rule | Enforcement |
|------|-------------|
| Readiness `insufficient_evidence` or `conflicted` | Final verdict must be `insufficient_evidence` or `defer` only |
| Hard contradiction unresolved | Cannot produce `proceed` |
| Missing CIM reference | Cannot produce `proceed` |
| Unsupported target segment | Cannot produce `proceed` |
| Missing provenance on critical evidence | Cannot produce `high` confidence |
| Verdict `proceed` with zero supporting evidence refs | **Invalid output** (02.6B schema/test) |
| Verdict `stop` with zero blockers | **Invalid output** (02.6B schema/test) |
| Verdict `proceed` despite critical blocker | **Invalid output** (02.6B schema/test) |

---

## Decision dimensions

Fifteen finite dimensions. Each dimension record includes:

| Field | Type | Required |
|-------|------|----------|
| `dimension_id` | string (slug) | ✓ |
| `status` | enum (see below) | ✓ |
| `evidence_references` | string[] | ✓ (may be empty with documented gap) |
| `contradictory_evidence` | string[] | ✓ |
| `assumptions` | string[] | ✓ |
| `unknowns` | string[] | ✓ |
| `confidence` | `high\|medium\|low\|unknown` | ✓ |
| `blockers` | blocker_ref[] | ✓ |
| `notes` | string | optional |

### Dimension status enum

`strong`, `adequate`, `weak`, `unknown`, `contradicted`, `not_applicable`

### Dimension catalog

| ID | Upstream primary source | MV assessment focus |
|----|-------------------------|---------------------|
| `product_context_quality` | PMC 0.2.x | Normalized claims completeness, conflicts, readiness |
| `market_evidence_quality` | MR 0.1.x | Source quality, coverage, research status |
| `customer_evidence_quality` | CIM 0.1.x | Segment evidence, JTBD/pain support, CIM readiness |
| `demand_signal_strength` | MR + CIM | Demand signals, priority tier rationale |
| `competitor_pressure` | CA 0.1.x | Landscape pressure, differentiation gaps |
| `segment_fit` | CIM 0.1.x | Primary ICP candidates, boundaries, strategic fit |
| `reachability` | CIM 0.1.x | Channel reach, audience access |
| `budget_fit` | CIM + PMC | Budget sensitivity vs declared constraints |
| `pricing_plausibility` | PMC + MR + CIM | Pricing claims vs market/pricing signals |
| `operational_feasibility` | PMC | Operational constraints, delivery model |
| `switching_difficulty` | CIM + CA | Switching costs, incumbent lock-in |
| `evidence_coverage` | All upstream | Cross-source coverage gaps |
| `contradiction_severity` | All upstream | Unresolved conflicts severity |
| `regulatory_or_external_constraints` | PMC + MR | Legal, regulatory, external timing |
| `critical_risks` | Synthesized | Aggregate blocking risk summary |

**No arbitrary production weights** in 02.6A. Dimensions inform verdict; they do not auto-score to a number.

---

## Hard blockers

Hard blockers are **explicit stop conditions** on responsible decision-making. A hard blocker does **not always force `stop`** — remediation possibility determines verdict mapping.

### Blocker categories

| ID | Category | Description |
|----|----------|-------------|
| `HB-001` | customer_problem | No identifiable customer problem supported by evidence |
| `HB-002` | target_segment | No supported target segment in CIM |
| `HB-003` | evidence_contradiction | Critical evidence contradiction unresolved |
| `HB-004` | legal_prohibition | Illegal or prohibited business model in scope |
| `HB-005` | operational_impossibility | Impossible operational dependency |
| `HB-006` | budget_unavailable | Required budget materially unavailable |
| `HB-007` | compliance_risk | Unacceptable tenant/security/compliance risk |
| `HB-008` | demand_absent | Demand evidence absent where required for scope |
| `HB-009` | competitor_disadvantage | Unresolvable competitor disadvantage |
| `HB-010` | provenance_missing | Invalid or missing provenance for critical evidence |
| `HB-011` | unsupported_inference | Decision would rely primarily on unsupported inference |

### Blocker record shape

```yaml
blocker_id: HB-003
category: evidence_contradiction
statement: "CIM segment conflict unresolved between seg-A and seg-B"
severity: critical
evidence_references: [ev-conflict-001]
remediation_possible: true
remediation_hint: "Resolve segment boundary or exclude one segment"
```

### Blocker → verdict mapping

| Remediation | Typical verdict | Notes |
|-------------|-----------------|-------|
| None possible | `stop` | Fatal commercial flaw |
| Possible with material change | `revise` | Segment, model, pricing, geography change |
| Timing/external only | `defer` | Wait for evidence or conditions |
| Evidence gap only | `insufficient_evidence` | Cannot decide responsibly |
| Condition can clear blocker | `proceed_with_conditions` | Explicit conditions required |
| Blocker cleared + dimensions strong | `proceed` | No critical blockers remain |

**Hard blocker present + verdict `proceed`** → invalid output (02.6B test).

---

## Conditions model

For `proceed_with_conditions` only. **No free-text-only conditions.**

| Field | Required | Description |
|-------|----------|-------------|
| `condition_id` | ✓ | Stable slug |
| `category` | ✓ | e.g. `evidence`, `segment`, `pricing`, `operational`, `legal` |
| `statement` | ✓ | What must become true |
| `required_action` | ✓ | Concrete action |
| `owner` | ✓ | `owner`, `operator`, `customer`, `platform` |
| `deadline_or_gate` | ✓ | Time gate or milestone gate |
| `evidence_required` | ✓ | What evidence closes the condition |
| `blocking` | ✓ | Whether launch/advance blocked until met |
| `validation_method` | ✓ | How condition closure is verified |
| `status` | ✓ | `open`, `in_progress`, `satisfied`, `waived`, `failed` |

---

## Risk model

Finite risk domains:

`market`, `customer`, `competitor`, `pricing`, `financial`, `operational`, `legal`, `compliance`, `timing`, `channel`, `evidence`, `execution`

### Risk record shape

| Field | Required | Notes |
|-------|----------|-------|
| `risk_id` | ✓ | Stable slug |
| `domain` | ✓ | From finite list above |
| `description` | ✓ | |
| `likelihood` | ✓ | `high`, `medium`, `low`, `unknown` — **not** probability % |
| `impact` | ✓ | `critical`, `major`, `moderate`, `minor`, `unknown` |
| `severity` | ✓ | Derived label: `critical`, `elevated`, `moderate`, `low` |
| `evidence_references` | ✓ | |
| `assumptions` | ✓ | |
| `mitigations` | optional | |
| `residual_risk` | optional | Post-mitigation assessment |
| `blocking` | ✓ | Contributes to hard blocker if true |
| `owner_review_required` | ✓ | Human review flag |

Output splits risks into `critical_risks[]` (blocking or severity critical) and `noncritical_risks[]`.

---

## Confidence discipline

Finite confidence: `high`, `medium`, `low`, `unknown`

### High confidence requires

- Source-backed critical dimensions
- No unresolved critical contradiction
- Adequate cross-source coverage
- Explicit provenance on material claims
- Current-enough evidence where time-sensitive (market, pricing, regulation)

### Confidence downgrade triggers

- Primary reliance on assumptions or inferences
- Upstream `conflicted` or `insufficient_*` status
- Missing CIM segment for customer-facing verdict
- Single-source critical claim without corroboration

**No numeric confidence scores** without benchmark.

---

## Verdict decision matrix (qualitative)

This matrix guides human/operator judgment in 02.6B fixtures — not automated scoring.

| Pattern | Allowed verdicts |
|---------|------------------|
| All critical dimensions `strong`/`adequate`, no blockers | `proceed` |
| Strong overall, non-blocking gaps | `proceed_with_conditions` |
| Viable with material model/segment/pricing change | `revise` |
| Timing/readiness/external factors | `defer` |
| Fatal blocker, no remediation | `stop` |
| Cannot assess responsibly | `insufficient_evidence` |

---

## Forbidden output fields

MV must **not** emit:

- `positioning`
- `final_offer`
- `campaign`
- `execution_status`
- `publication`
- `connector_result`

MV issues **viability verdict only**. Positioning and Offer Builder are downstream consumers.

---

## Related documents

- [Version Mapping](market-validation-version-mapping.md)
- [Consumer Contracts](market-validation-consumer-contracts.md)
- [SKILL-02.6 Migration Design](../rfc/SKILL-02.6-MARKET-VALIDATION-0.2-MIGRATION-DESIGN.md)
