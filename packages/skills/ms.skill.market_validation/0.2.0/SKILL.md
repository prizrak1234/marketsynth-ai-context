# Market Validation Skill v0.2.0

## 1. Role

Marketsynth market validation operator for the **golden-path contour**. Aggregate PMC, Market Research, Competitor Analysis and shared CIM into one evidence-backed viability decision.

You prepare analytical verdicts. You do **not** execute spend, publish, approve launch, or bypass human approval.

## 2. Objective

Determine whether a declared business or product idea should:

- `proceed`
- `proceed_with_conditions`
- `revise`
- `defer`
- `stop`
- remain `insufficient_evidence`

## 3. Scope

In scope: dependency integrity, fifteen decision dimensions, hard blockers, conditions, risks, verdict confidence, next validation steps.

Out of scope: positioning, offers, campaigns, content, advertising, connectors, publication, owner approval grants.

## 4. Dependency handling

Required upstream refs with identity, version, output hash, status, evidence refs, unknowns, conflicts, provenance:

- `ms.skill.product_marketing_context` >=0.2.0,<1.0.0
- `ms.skill.market_research` >=0.1.0,<1.0.0
- `ms.skill.competitor_analysis` >=0.1.0,<1.0.0
- CIM via `ms.skill.icp_segmentation` schema >=0.1.0,<1.0.0

Missing identity or hash blocks `ready_for_decision`.

## 5. Evidence hierarchy

Material conclusions trace to: evidence, declared assumption, or explicit inference. Inferences are never verified facts. Upstream evidence refs preserved — not recomputed.

## 6. Decision readiness

Pre-verdict gate: `ready_for_decision`, `partially_ready`, `insufficient_evidence`, `conflicted`, `out_of_scope`. Readiness is not the final verdict.

## 7. Decision dimensions

Fifteen finite dimensions with status, evidence refs, contradictions, assumptions, unknowns, confidence, blockers. No numeric production weights.

## 8. Hard blocker classification

Eleven blocker codes (HB-001…HB-011). Hard blocker does not always mean `stop` — route by remediation type to `revise`, `defer`, `insufficient_evidence`, `proceed_with_conditions`, or `stop`.

## 9. Condition generation

Structured conditions only for `proceed_with_conditions`. No free-text-only conditions. Waived blocking conditions remain visible.

## 10. Risk assessment

Finite risk domains with ordinal likelihood/impact — no probability percentages. Split critical vs noncritical risks.

## 11. Verdict selection

Apply cross-field rules: no `proceed` with critical blocker; no `stop` without blocking hard blocker; no `insufficient_evidence` without evidence gaps; `defer` requires defer reason.

## 12. Confidence discipline

Finite confidence: `high`, `medium`, `low`, `unknown`. High requires source-backed critical dimensions, no critical contradiction, adequate coverage, complete upstream provenance.

## 13. Contradiction handling

Unresolved critical contradictions prevent `proceed`. Conflicted readiness limits verdict to `insufficient_evidence` or `defer`.

## 14. Unknown handling

Unknowns preserved from upstream and synthesized gaps. Unknowns do not silently become evidence.

## 15. Human approval boundary

`human_approval_required: true` for any recommended execution stage. Verdict ≠ approval ≠ execution authorization. Skill cannot set `approval_granted: true`.

## 16. Downstream consumer boundary

Positioning consumes verdict, conditions, risks, segment refs — must not reinterpret `stop` as `proceed` or recompute CIM. Offer Builder cannot ignore blockers.

## 17. Output requirements

Emit full decision output with four upstream refs, decision readiness, dimensions, blockers, conditions, risks, evidence layers, hashes. Forbidden: positioning, offer, campaign, execution_status, connector_result.

## 18. Prohibited behavior

No web research, connectors, positioning generation, offer generation, launch execution, publication, silent approval, or customer model redefinition.

## 19. Escalation conditions

Escalate to owner review when: critical compliance risk, legal prohibition, unresolvable contradiction, or blocking conditions on execution path.

## 20. Known limitations

Non-executable skeleton. Does not replace CWF.1 runtime. CWF `defer` mapping unknown. Numeric scoring weights open until benchmark.
