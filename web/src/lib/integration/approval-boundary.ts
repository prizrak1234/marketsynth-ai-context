/**
 * I6 — Approval categories must never flatten to a single boolean.
 */

export type ApprovalCategory =
  | "implementation_plan_local_review"
  | "marketing_plan_approval"
  | "execution_approval"
  | "publication_approval"
  | "budget_approval"
  | "verdict_local_review"
  | "specialist_output_approval"
  | "content_asset_approval";

export type ApprovalBoundaryRow = {
  category: ApprovalCategory;
  meaning: string;
  authorizesExecution: boolean;
  authorizesPublication: boolean;
  createsMarketingPlanApproval: boolean;
  createsExecutionApproval: boolean;
};

export const APPROVAL_BOUNDARY_MATRIX: readonly ApprovalBoundaryRow[] = [
  {
    category: "implementation_plan_local_review",
    meaning: "Product Alpha local review of delivery plan structure",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
  {
    category: "marketing_plan_approval",
    meaning: "Approves backend specialist work plan (status → approved); does not start runs",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: true,
    createsExecutionApproval: false,
  },
  {
    category: "execution_approval",
    meaning: "Authorizes real external operation under REAL_EXECUTION flags",
    authorizesExecution: true,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: true,
  },
  {
    category: "publication_approval",
    meaning: "Authorizes publication package path",
    authorizesExecution: false,
    authorizesPublication: true,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
  {
    category: "budget_approval",
    meaning: "Authorizes financial scope",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
  {
    category: "verdict_local_review",
    meaning: "Commercial verdict local review — not MarketingPlan/execution",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
  {
    category: "specialist_output_approval",
    meaning: "Approves a specialist artifact for downstream use",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
  {
    category: "content_asset_approval",
    meaning: "Approves content asset",
    authorizesExecution: false,
    authorizesPublication: false,
    createsMarketingPlanApproval: false,
    createsExecutionApproval: false,
  },
] as const;

/** Invariants for selfcheck */
export function implementationPlanApprovalCreatesMarketingPlanApproval(): false {
  return false;
}

export function marketingPlanApprovalCreatesExecutionApproval(): false {
  return false;
}

export function marketingPlanApprovalCreatesPublicationApproval(): false {
  return false;
}

export function verdictApprovalCreatesMarketingPlanApproval(): false {
  return false;
}

export type ReadinessKind =
  | "strategy_readiness"
  | "implementation_planning_readiness"
  | "marketing_plan_readiness"
  | "approval_readiness"
  | "execution_readiness"
  | "publication_readiness";

export type ReadinessSemanticsRow = {
  kind: ReadinessKind;
  meaning: string;
  equalsOthers: false;
  note: string;
};

export const READINESS_SEMANTICS: readonly ReadinessSemanticsRow[] = [
  {
    kind: "strategy_readiness",
    meaning: "GTM strategy completeness (local)",
    equalsOthers: false,
    note: "≠ MarketingPlan approve",
  },
  {
    kind: "implementation_planning_readiness",
    meaning: "A6 PlanningReadinessResult — notRealExecution",
    equalsOthers: false,
    note: "ready_for_approval ≠ ready_for_execution",
  },
  {
    kind: "marketing_plan_readiness",
    meaning: "Plan draft/approved/archived state",
    equalsOthers: false,
    note: "approved ≠ execution authorized",
  },
  {
    kind: "approval_readiness",
    meaning: "Whether a specific category can be approved",
    equalsOthers: false,
    note: "per-category only",
  },
  {
    kind: "execution_readiness",
    meaning: "Backend execution readiness / expansion gate",
    equalsOthers: false,
    note: "separate from plan approve",
  },
  {
    kind: "publication_readiness",
    meaning: "Package schedule/dry-run readiness",
    equalsOthers: false,
    note: "≠ MarketingPlan approve",
  },
] as const;

export function readyForApprovalImpliesReadyForExecution(): false {
  return false;
}

export function marketingPlanApprovedImpliesApprovedForExecution(): false {
  return false;
}
