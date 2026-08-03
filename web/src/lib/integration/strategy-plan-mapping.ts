/**
 * I5 — Strategy ↔ MarketingPlan field mapping (Option B).
 * MarketingPlan does not own positioning / audience / offers / funnel / budget / KPIs.
 */

export type StrategyPlanRelationship =
  | "exact_match"
  | "partial_match"
  | "derived"
  | "backend_is_lower_level"
  | "frontend_presentation_only"
  | "semantic_conflict"
  | "absent";

export type StrategyPlanMappingRow = {
  capability: string;
  strategySide: string;
  marketingPlanSide: string;
  relationship: StrategyPlanRelationship;
  sourceOfTruth: "local_strategy" | "backend_marketing_plan" | "none" | "split";
  action: string;
};

export const STRATEGY_PLAN_FIELD_MATRIX: readonly StrategyPlanMappingRow[] = [
  {
    capability: "strategic objective",
    strategySide: "objectives[]",
    marketingPlanSide: "specialist_tasks[].objective (task prompt)",
    relationship: "semantic_conflict",
    sourceOfTruth: "local_strategy",
    action: "Do not map task objectives → StrategyObjective",
  },
  {
    capability: "market choice / summary",
    strategySide: "summary",
    marketingPlanSide: "title + goal (free text)",
    relationship: "partial_match",
    sourceOfTruth: "split",
    action: "Show plan goal as ops context only",
  },
  {
    capability: "audience segment",
    strategySide: "segments[]",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "unsupported on plan — local/unsupported",
  },
  {
    capability: "positioning",
    strategySide: "positioning",
    marketingPlanSide: "absent (strategist artifact later)",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "never invent from plan",
  },
  {
    capability: "value proposition / offer",
    strategySide: "offers[]",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "never invent",
  },
  {
    capability: "channel strategy",
    strategySide: "channels[]",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "unsupported",
  },
  {
    capability: "funnel",
    strategySide: "funnel",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "unsupported",
  },
  {
    capability: "content/asset plan",
    strategySide: "assets[]",
    marketingPlanSide: "specialist_tasks queue (not assets)",
    relationship: "backend_is_lower_level",
    sourceOfTruth: "split",
    action: "plan tasks ≠ strategy assets",
  },
  {
    capability: "budget allocation",
    strategySide: "budget",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "unsupported",
  },
  {
    capability: "KPIs",
    strategySide: "metrics[]",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "unsupported",
  },
  {
    capability: "risks / assumptions / verdict conditions",
    strategySide: "risks, assumptions, conditions",
    marketingPlanSide: "absent",
    relationship: "absent",
    sourceOfTruth: "local_strategy",
    action: "keep on Strategy/Verdict",
  },
  {
    capability: "campaign / ops plan",
    strategySide: "n/a (Implementation I6)",
    marketingPlanSide: "MarketingPlan entity",
    relationship: "backend_is_lower_level",
    sourceOfTruth: "backend_marketing_plan",
    action: "plan SoT for specialist execution spine",
  },
  {
    capability: "execution readiness",
    strategySide: "executionReadiness (FE planning)",
    marketingPlanSide: "status approved + execution runs",
    relationship: "semantic_conflict",
    sourceOfTruth: "split",
    action: "plan approve ≠ strategy readiness",
  },
  {
    capability: "approvals",
    strategySide: "local status",
    marketingPlanSide: "POST .../approve",
    relationship: "semantic_conflict",
    sourceOfTruth: "split",
    action: "separate gates — never collapse",
  },
  {
    capability: "versioning",
    strategySide: "local Strategy versions",
    marketingPlanSide: "MarketingPlanVersion snapshots",
    relationship: "partial_match",
    sourceOfTruth: "split",
    action: "link ids only; no auto-sync",
  },
  {
    capability: "project/campaign scope",
    strategySide: "project-level",
    marketingPlanSide: "project_id FK; soft campaign in context",
    relationship: "partial_match",
    sourceOfTruth: "split",
    action: "Strategy stays project-level",
  },
] as const;

export type StrategySectionAuthority = {
  section: string;
  origin: "backend_marketing_plan" | "deterministic_local" | "mock" | "unsupported";
  claim: string;
};

/** Honest defaults for composed Strategy Workspace. */
export function defaultSectionAuthorities(mode: "mock" | "backend" | "hybrid"): StrategySectionAuthority[] {
  const strategic = [
    "objectives",
    "segments",
    "positioning",
    "offers",
    "channels",
    "funnel",
    "assets",
    "budget",
    "metrics",
    "risks",
    "assumptions",
    "conditions",
  ];
  if (mode === "mock") {
    return strategic.map((section) => ({
      section,
      origin: "mock" as const,
      claim: "Product Alpha deterministic Strategy",
    }));
  }
  if (mode === "backend") {
    return strategic.map((section) => ({
      section,
      origin: "unsupported" as const,
      claim: "No backend MarketingStrategy fields on MarketingPlan",
    }));
  }
  return strategic.map((section) => ({
    section,
    origin: "deterministic_local" as const,
    claim: "Local strategic preview — not plan SoT",
  }));
}

export function marketingPlanDoesNotEqualStrategy(): true {
  return true;
}
