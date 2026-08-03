/**
 * I4 — Decision semantics: keep categories separate.
 * Never collapse into a universal Decision union without a discriminator.
 */

export type DecisionSemanticCategory =
  | "advisory_recommendation"
  | "operational_recommendation"
  | "business_viability_verdict"
  | "human_approval_decision"
  | "execution_approval_decision"
  | "publication_approval_decision"
  | "planner_routing_decision"
  | "supervisor_quality_finding"
  | "control_center_next_action"
  | "readiness_result";

export type DecisionSemanticsRow = {
  object: string;
  category: DecisionSemanticCategory;
  meaning: string;
  scope: string;
  authority: string;
  changesState: boolean;
  authorizesAction: boolean;
  businessVerdictRelation:
    | "none"
    | "input_signal"
    | "conflict_if_confused"
    | "is_verdict"
    | "future_linkage";
};

/** Frozen audit mapping — Source of Truth for I4 docs + selfchecks. */
export const DECISION_SEMANTICS_MATRIX: readonly DecisionSemanticsRow[] = [
  {
    object: "ProductAlpha.BusinessVerdict",
    category: "business_viability_verdict",
    meaning:
      "Should this business project proceed in its current form under stated conditions and evidence?",
    scope: "project",
    authority: "commercial decision (Product Alpha local / future domain)",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "is_verdict",
  },
  {
    object: "VerdictKind (contracts stub)",
    category: "business_viability_verdict",
    meaning: "Vocabulary GO / CONDITIONAL_GO / NO_GO / INSUFFICIENT_DATA — not persisted",
    scope: "n/a",
    authority: "none (enum only)",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "future_linkage",
  },
  {
    object: "CampaignSupervisorFinding",
    category: "supervisor_quality_finding",
    meaning: "Campaign quality gap / risk signal",
    scope: "campaign",
    authority: "advisory",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "input_signal",
  },
  {
    object: "CampaignSupervisorReport.recommended_next_actions",
    category: "advisory_recommendation",
    meaning: "Suggested campaign actions from quality engine",
    scope: "campaign",
    authority: "advisory",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "conflict_if_confused",
  },
  {
    object: "CampaignControlCenter.next_action",
    category: "control_center_next_action",
    meaning: "Operational recommendation — what to click next in campaign ops",
    scope: "campaign",
    authority: "ops UX recommendation",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "conflict_if_confused",
  },
  {
    object: "CampaignAction.execute",
    category: "operational_recommendation",
    meaning: "Explicit execute of listed campaign action after user click",
    scope: "campaign",
    authority: "ops when user executes",
    changesState: true,
    authorizesAction: true,
    businessVerdictRelation: "none",
  },
  {
    object: "MarketingPlan.approve / ContentAsset.approve / Package.approve",
    category: "human_approval_decision",
    meaning: "Artifact release / plan gate — not business viability",
    scope: "artifact / plan",
    authority: "human owner via resource approve",
    changesState: true,
    authorizesAction: true,
    businessVerdictRelation: "none",
  },
  {
    object: "ExecutionApproval (REAL_EXECUTION_EXPANSION)",
    category: "execution_approval_decision",
    meaning: "Authorizes real external execute / Telegram publish under flags",
    scope: "execution subject",
    authority: "human + readiness gate",
    changesState: true,
    authorizesAction: true,
    businessVerdictRelation: "none",
  },
  {
    object: "PublicationPackage.approve",
    category: "publication_approval_decision",
    meaning: "Authorizes publication package as ready to schedule/dry-run",
    scope: "publication package",
    authority: "human owner",
    changesState: true,
    authorizesAction: true,
    businessVerdictRelation: "none",
  },
  {
    object: "AutonomousOperationPlan / planner routing",
    category: "planner_routing_decision",
    meaning: "Controlled plan steps — not business GO/NO_GO",
    scope: "campaign / plan",
    authority: "planner + human advance",
    changesState: true,
    authorizesAction: false,
    businessVerdictRelation: "conflict_if_confused",
  },
  {
    object: "InvestigationVerdictReadiness / CampaignBriefCompleteness / ExecutionReadiness",
    category: "readiness_result",
    meaning: "Meter of completeness — not viability verdict",
    scope: "investigation | brief | campaign",
    authority: "derived metric",
    changesState: false,
    authorizesAction: false,
    businessVerdictRelation: "conflict_if_confused",
  },
] as const;

export function assertNeverUniversalDecision(
  category: DecisionSemanticCategory,
): boolean {
  // Discriminator required — categories must not be collapsed
  return category !== ("universal_decision" as DecisionSemanticCategory);
}

export function categoryIsBusinessVerdict(category: DecisionSemanticCategory): boolean {
  return category === "business_viability_verdict";
}

export function categoryAuthorizesExecution(category: DecisionSemanticCategory): boolean {
  return (
    category === "execution_approval_decision" ||
    category === "publication_approval_decision"
  );
}

/** Supervisor / CC → VerdictInputSignal roles (never auto-verdict). */
export type VerdictInputSignalRole =
  | "quality_warning"
  | "risk_signal"
  | "missing_input"
  | "recommended_next_step"
  | "operational_recommendation";

export type VerdictInputSignal = {
  id: string;
  role: VerdictInputSignalRole;
  title: string;
  description: string;
  sourceObject: string;
  category: DecisionSemanticCategory;
  origin: "backend" | "derived";
  disclaimer: string;
};
