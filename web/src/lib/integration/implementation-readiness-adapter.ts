/**
 * P1.1 — readiness adapter; distinct from MarketingPlan/execution readiness.
 */

export function implementationReadinessIsNotExecutionReadiness(): true {
  return true;
}

export function implementationReadinessIsNotMarketingPlanReadiness(): true {
  return true;
}

export function readyForHandoffMeansPreviewOnly(): string {
  return "ready_for_handoff = eligible to preview MarketingPlan mapping; not execution/budget/publication approval.";
}
