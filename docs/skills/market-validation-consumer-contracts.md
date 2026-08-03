# Market Validation — Consumer Contracts

**Phase:** SKILL-02.6A  
**Status:** Design — pending owner review  
**Scope:** Output contract design and downstream boundaries; no package implementation

---

## MV 0.2.0 output contract (conceptual — 02.6B)

### Identity and lineage

| Field | Required | Description |
|-------|----------|-------------|
| `validation_id` | ✓ | Stable output identifier |
| `skill_id` | ✓ | `ms.skill.market_validation` |
| `skill_version` | ✓ | `0.2.0` |
| `source_context_reference` | ✓ | PMC dependency ref (id, version, hash, status) |
| `source_research_reference` | ✓ | MR dependency ref |
| `source_competitor_reference` | ✓ | CA dependency ref |
| `source_cim_reference` | ✓ | CIM ref (schema URI, version, document hash, ICP lineage) |
| `input_hash` | ✓ | Deterministic input fingerprint |
| `output_hash` | ✓ | Deterministic output fingerprint |
| `provenance` | ✓ | Producer audit stub |

### Decision core

| Field | Required | Description |
|-------|----------|-------------|
| `decision_readiness` | ✓ | Pre-verdict readiness (not verdict) |
| `verdict` | ✓ | One of 6 finite values |
| `verdict_confidence` | ✓ | `high`, `medium`, `low`, `unknown` |
| `executive_summary` | ✓ | Human-readable summary |
| `decision_dimensions` | ✓ | Array of 15 dimension records |
| `blockers` | ✓ | Hard blocker records (may be empty if none) |
| `conditions` | ✓ | Structured conditions (required when verdict = `proceed_with_conditions`) |
| `critical_risks` | ✓ | Blocking or critical-severity risks |
| `noncritical_risks` | ✓ | Remaining risks |

### Evidence discipline

| Field | Required | Description |
|-------|----------|-------------|
| `supporting_evidence` | ✓ | Traceable items with evidence refs |
| `contradictory_evidence` | ✓ | Conflicting traceable items |
| `assumptions` | ✓ | Explicit assumptions |
| `inferences` | ✓ | Explicit inferences (not presented as facts) |
| `unknowns` | ✓ | Documented gaps |
| `conflicts` | ✓ | Unresolved upstream + synthesized conflicts |

### Guidance (not execution)

| Field | Required | Description |
|-------|----------|-------------|
| `required_changes` | ✓ | Material changes if `revise` |
| `next_validation_steps` | ✓ | Follow-up validation actions |
| `recommended_next_stage` | ✓ | e.g. `positioning`, `offer_builder`, `additional_research`, `owner_review` |
| `human_approval_required` | ✓ | Always true for launch/spend/publication transitions |

### Forbidden fields

`positioning`, `final_offer`, `campaign`, `execution_status`, `publication`, `connector_result`

---

## Upstream consumption map

| Upstream | MV consumes | MV must not redefine |
|----------|-------------|----------------------|
| PMC 0.2.x | Normalized product/market/customer claims, readiness, conflicts | Context normalization |
| MR 0.1.x | Market definition, demand signals, research status, evidence quality | Research findings |
| CA 0.1.x | Competitor inventory, differentiation gaps, competitive pressure | Competitor analysis |
| CIM 0.1.x | Segments, ICP candidates, JTBD, pains, priorities, blockers, unknowns | Customer intelligence |

CIM canonical URI: `https://schemas.marketsynth.ai/customer-intelligence/0.1.0/customer-intelligence.schema.json`

### CIM fields consumed by MV

From [CIM consumer fixture](../../packages/knowledge/customer_intelligence/0.1.0/consumers/market_validation_consumer.json):

- `primary_icp_candidates`
- `priority_assessment`
- `demand_signal`
- `evidence_quality`
- `reachability`
- `switching_difficulty`
- `customer_unknowns`
- `segment_conflicts`

Plus: budget fit, competitive pressure, readiness blockers (from CIM readiness domain).

**Invariant:** `verdict_issued_by_consumer: true` — MV issues verdict; CIM does not.

---

## Downstream consumers of MV output

### Positioning (`ms.skill.positioning` 0.1.0 — **02.7 frozen**)

**Package:** `packages/skills/ms.skill.positioning/`  
**Regression:** `tests/test_skill_02_7_positioning.py`

**May consume:**

- Selected segment references (via CIM ref, not recomputed)
- Differentiation gaps (from CA via MV synthesis)
- Verdict conditions
- Critical risks
- Evidence references
- `recommended_next_stage` when `positioning`

**May not:**

- Reinterpret `stop` as `proceed`
- Recompute JTBD, pains, objections, decision roles
- Issue viability verdict

**Gate:** Positioning should not start when verdict is `stop` or `insufficient_evidence` without explicit owner override.

---

### Offer Builder (`ms.skill.offer_builder` — 02.8)

**May consume:**

- Permitted downstream state only (`proceed`, `proceed_with_conditions` with conditions met, or explicit owner override)
- Segment priorities (via CIM ref)
- Pains, outcomes, objections (via CIM ref)
- Verdict conditions and blockers

**May not:**

- Redefine customer model
- Ignore blockers silently
- Proceed when blocking conditions are open

---

### Launch Strategy (future)

**May consume:**

- Verdict, conditions, risks, recommended next stage
- Executive summary for owner briefing

**May not:**

- Execute spend, ads, or publication
- Override `human_approval_required`

---

### Owner decision / CWF UI

**May consume:**

- Verdict + confidence + executive summary
- Conditions, blockers, next steps
- Decision branch mapping (future adapter — not 02.6A)

**May not:**

- Auto-approve launch/spend
- Silently map `defer` until CWF adapter defined

---

### CWF migration adapter (future — not 02.6A)

**May consume:**

- MV 0.2.0 output for BIV parity testing
- Version mapping table for `stop` ↔ `reject`, `defer` ↔ Unknown

**May not:**

- Modify CWF.1 runtime in 02.6A
- Replace human approval gates

---

## Consumer reference pattern

Every downstream consumer of MV must declare:

```yaml
mv_schema_uri: ms.skill.market_validation/output/0.2.0
mv_version: "0.2.0"
mv_output_hash: "<sha256>"
source_skill_id: ms.skill.market_validation
verdict_consumed: proceed_with_conditions
selected_segment_ids: [seg-remote-eng]
conditions_acknowledged: [cond-budget-validation]
blockers_ignored: []  # must be empty or explicit waiver ref
```

**Rule:** No consumer may ignore blockers silently. Empty `blockers_ignored` required unless documented waiver.

---

## MV responsibilities vs non-responsibilities

| MV does | MV does not |
|---------|-------------|
| Issue viability verdict | Generate positioning |
| Synthesize upstream evidence | Build offer |
| Document blockers, conditions, risks | Launch advertising |
| Recommend next validation stage | Create content |
| Require human approval flag for execution | Execute Connector calls |
| Preserve upstream lineage | Substitute human approval |
| Consume CIM as shared contract | Redefine customer intelligence |

---

## 02.6B test plan — fixture classes

| # | Fixture class | Validates |
|---|---------------|-----------|
| 1 | Proceed case | Strong dimensions, no blockers, evidence refs present |
| 2 | Proceed with conditions | Structured conditions array populated |
| 3 | Revise segment | HB-002 or segment_fit weak → `revise` |
| 4 | Revise pricing/model | pricing_plausibility weak → `revise` |
| 5 | Defer timing | External/timing blocker → `defer` |
| 6 | Stop fatal flaw | HB-004 or HB-009 → `stop` with blockers |
| 7 | Insufficient evidence | Readiness insufficient → verdict matches |
| 8 | Conflicted upstream | MR/CIM conflict → no `proceed` |
| 9 | Missing CIM | No source_cim_reference → schema reject |
| 10 | Missing dependency hash | Incomplete ref → schema reject |
| 11 | Unsupported high-confidence | high confidence + inference-only → invalid |
| 12 | Verdict no evidence | proceed + empty supporting_evidence → invalid |
| 13 | Stop no blocker | stop + empty blockers → invalid |
| 14 | Proceed with critical blocker | proceed + HB-* → invalid |
| 15 | Consumer compatibility | Positioning fixture reads MV without verdict recompute |
| 16 | Legacy mapping | 0.1.0 output adapter classification |

---

## Related documents

- [Version Mapping](market-validation-version-mapping.md)
- [Decision Matrix](market-validation-decision-matrix.md)
- [CIM Consumer Contracts v0.1.0](../knowledge/CIM-consumer-contracts-v0.1.0.md)
- [SKILL-02.6 Migration Design](../rfc/SKILL-02.6-MARKET-VALIDATION-0.2-MIGRATION-DESIGN.md)
