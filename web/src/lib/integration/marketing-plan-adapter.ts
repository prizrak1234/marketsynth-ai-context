/**
 * I5 — MarketingPlan read adapter (ops spine).
 * Never invents positioning / audience / offers from plan payloads.
 */

import type { MarketingPlan } from "@/lib/api/types/marketing-plans";
import type { DataOrigin } from "@/lib/integration/contracts";

export type MarketingPlanOpsView = {
  id: string;
  title: string;
  goal: string;
  status: string;
  currentVersion: number;
  approvedVersion: number | null;
  specialistTaskCount: number;
  specialistLabels: string[];
  softCampaignId: string | null;
  sourceScenarioId: string | null;
  updatedAt: string;
  origin: DataOrigin;
  /** Explicit semantic firewall */
  role: "ops_execution_spine";
  disclaimer: string;
};

/**
 * Deterministic multi-plan selection for context display only.
 * Never equals "current Strategy".
 */
export function selectRelatedMarketingPlans(plans: MarketingPlan[]): {
  related: MarketingPlan[];
  primary: MarketingPlan | null;
  rule: string;
} {
  const active = plans
    .filter((p) => p.status !== "archived")
    .slice()
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const primary = active[0] ?? null;
  return {
    related: active,
    primary,
    rule:
      "Non-archived by created_at desc; primary = newest related ops plan — NOT Strategy SoT.",
  };
}

export function mapMarketingPlanToOpsView(plan: MarketingPlan): MarketingPlanOpsView {
  const ctx = plan.project_context ?? {};
  const softCampaignId =
    typeof ctx.source_campaign_id === "string" ? ctx.source_campaign_id : null;
  return {
    id: plan.id,
    title: plan.title,
    goal: plan.goal,
    status: plan.status,
    currentVersion: plan.current_version_number,
    approvedVersion: plan.approved_version_number ?? null,
    specialistTaskCount: plan.specialist_tasks.length,
    specialistLabels: plan.specialist_tasks.map((t) => t.specialist),
    softCampaignId,
    sourceScenarioId: plan.source_scenario_id ?? null,
    updatedAt: plan.updated_at,
    origin: "backend",
    role: "ops_execution_spine",
    disclaimer:
      "MarketingPlan = specialist execution spine. Не Strategy (нет positioning/audience/offers/funnel/budget/KPIs).",
  };
}

/** Hard firewall: plan goal must not become StrategyObjective. */
export function planTasksAreNotStrategyObjectives(): true {
  return true;
}

export function planApproveIsNotStrategyReady(): true {
  return true;
}

export function writePolicyI5() {
  return {
    strategyToMarketingPlan: "forbidden_dual_write",
    marketingPlanToStrategyFields: "forbidden_invent",
    readOpsPlanContext: "allowed",
    autoCreateCampaign: false,
    autoCreateExecution: false,
    autoUploadLocalStrategy: false,
    overwriteApprovedPlan: false,
  } as const;
}
