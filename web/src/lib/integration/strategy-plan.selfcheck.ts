/**
 * Integration I5 selfcheck — Strategy ≠ MarketingPlan.
 * Run: npx --yes tsx src/lib/integration/strategy-plan.selfcheck.ts
 */

import type { MarketingPlan } from "@/lib/api/types/marketing-plans";
import {
  mapMarketingPlanToOpsView,
  planApproveIsNotStrategyReady,
  planTasksAreNotStrategyObjectives,
  selectRelatedMarketingPlans,
  writePolicyI5,
} from "@/lib/integration/marketing-plan-adapter";
import {
  marketingPlanDoesNotEqualStrategy,
  STRATEGY_PLAN_FIELD_MATRIX,
} from "@/lib/integration/strategy-plan-mapping";
import { resolveStrategyEligibility } from "@/lib/integration/strategy-eligibility";
import { mockVerdictOrigin } from "@/lib/integration/verdict-origin";
import { localStrategyReconciliationPolicy } from "@/lib/integration/strategy-adapter";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(marketingPlanDoesNotEqualStrategy() === true, "not equal");
  assert(planTasksAreNotStrategyObjectives() === true, "tasks ≠ objectives");
  assert(planApproveIsNotStrategyReady() === true, "approve ≠ ready");
  const policy = writePolicyI5();
  assert(policy.strategyToMarketingPlan === "forbidden_dual_write", "no dual write");
  assert(policy.autoCreateCampaign === false, "no campaign");
  assert(policy.autoCreateExecution === false, "no execution");
  assert(policy.autoUploadLocalStrategy === false, "no upload");
}

{
  const positioning = STRATEGY_PLAN_FIELD_MATRIX.find((r) => r.capability === "positioning");
  assert(positioning?.relationship === "absent", "positioning absent on plan");
  assert(positioning?.sourceOfTruth === "local_strategy", "positioning local");
  const audience = STRATEGY_PLAN_FIELD_MATRIX.find((r) => r.capability.includes("audience"));
  assert(audience?.relationship === "absent", "audience absent");
  const obj = STRATEGY_PLAN_FIELD_MATRIX.find((r) => r.capability === "strategic objective");
  assert(obj?.relationship === "semantic_conflict", "task objective conflict");
}

{
  const plans: MarketingPlan[] = [
    {
      id: "p1",
      owner_id: "o",
      project_id: "proj",
      title: "Older",
      goal: "g1",
      specialist_tasks: [{ specialist: "strategist", objective: "write", expected_output: "doc" }],
      execution_mode: "planning",
      status: "approved",
      current_version_number: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "p2",
      owner_id: "o",
      project_id: "proj",
      title: "Newer",
      goal: "g2",
      specialist_tasks: [],
      execution_mode: "planning",
      status: "draft",
      current_version_number: 1,
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-01T00:00:00Z",
    },
    {
      id: "p3",
      owner_id: "o",
      project_id: "proj",
      title: "Archived",
      goal: "g3",
      specialist_tasks: [],
      execution_mode: "planning",
      status: "archived",
      current_version_number: 1,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    },
  ];
  const sel = selectRelatedMarketingPlans(plans);
  assert(sel.primary?.id === "p2", "newest non-archived primary");
  assert(sel.related.length === 2, "archived excluded");
  assert(sel.rule.includes("NOT Strategy"), "selection disclaimer");
  const view = mapMarketingPlanToOpsView(plans[0]!);
  assert(view.role === "ops_execution_spine", "ops role");
  assert(!view.disclaimer.toLowerCase().includes("is strategy"), "not claiming is strategy");
  assert(view.specialistTaskCount === 1, "task count");
}

{
  const noGo = resolveStrategyEligibility({
    verdictType: "NO_GO",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(noGo.allow === false, "NO_GO blocks strategy even if plan exists");
  const insuf = resolveStrategyEligibility({
    verdictType: "INSUFFICIENT_DATA",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(insuf.redirect === "investigation", "INSUFFICIENT → investigation");
  const cond = resolveStrategyEligibility({
    verdictType: "CONDITIONAL_GO",
    verdictStatus: "approved",
    origin: mockVerdictOrigin(),
  });
  assert(cond.requiresVisibleConditions === true, "conditions preserved");
}

{
  assert(localStrategyReconciliationPolicy().dualWriteToMarketingPlan === false, "no dual write");
  assert(localStrategyReconciliationPolicy().autoUpload === false, "no upload");
  const ms = DOMAIN_MAPPINGS.find((d) => d.model === "MarketingStrategy");
  assert(Boolean(ms?.notes?.includes("Option B") || ms?.notes?.includes("P0.6")), "domain strategy mapping");
  const mp = DOMAIN_MAPPINGS.find((d) => d.model === "MarketingPlan");
  assert(mp?.classification === "A_direct", "plan is direct SoT for ops");
}

console.log("strategy-plan.selfcheck.ts: OK");
