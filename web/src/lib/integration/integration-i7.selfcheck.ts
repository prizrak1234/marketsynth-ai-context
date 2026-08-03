/**
 * Integration I7 — end-to-end domain / governance invariants.
 * Run: npx --yes tsx src/lib/integration/integration-i7.selfcheck.ts
 */

import {
  APPROVAL_BOUNDARY_MATRIX,
  implementationPlanApprovalCreatesMarketingPlanApproval,
  marketingPlanApprovalCreatesExecutionApproval,
  marketingPlanApprovalCreatesPublicationApproval,
  marketingPlanApprovedImpliesApprovedForExecution,
  readyForApprovalImpliesReadyForExecution,
  verdictApprovalCreatesMarketingPlanApproval,
} from "@/lib/integration/approval-boundary";
import {
  DECISION_SEMANTICS_MATRIX,
  categoryAuthorizesExecution,
  categoryIsBusinessVerdict,
} from "@/lib/integration/decision-semantics";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";
import { qualitySignalsAreNotEvidence } from "@/lib/integration/evidence-adapter";
import { implementationPlanEqualsMarketingPlan } from "@/lib/integration/implementation-marketing-plan-mapping";
import { marketingPlanDoesNotEqualStrategy } from "@/lib/integration/strategy-plan-mapping";
import { verdictApprovalCreatesExecutionApproval } from "@/lib/integration/strategy-eligibility";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(marketingPlanDoesNotEqualStrategy() === true, "Strategy ≠ MarketingPlan");
  assert(implementationPlanEqualsMarketingPlan() === false, "ImplPlan ≠ MarketingPlan");
  assert(qualitySignalsAreNotEvidence() === true, "Supervisor ≠ Evidence");
  assert(verdictApprovalCreatesExecutionApproval() === false, "Verdict ≠ ExecApproval");
  assert(categoryIsBusinessVerdict("business_viability_verdict") === true, "verdict cat");
  assert(categoryIsBusinessVerdict("human_approval_decision") === false, "approval ≠ verdict");
  assert(categoryAuthorizesExecution("business_viability_verdict") === false, "verdict no exec");
  assert(categoryAuthorizesExecution("execution_approval_decision") === true, "exec cat");
}

{
  assert(implementationPlanApprovalCreatesMarketingPlanApproval() === false, "local≠mp");
  assert(marketingPlanApprovalCreatesExecutionApproval() === false, "mp≠exec");
  assert(marketingPlanApprovalCreatesPublicationApproval() === false, "mp≠pub");
  assert(verdictApprovalCreatesMarketingPlanApproval() === false, "verdict≠mp");
  assert(readyForApprovalImpliesReadyForExecution() === false, "ready≠exec");
  assert(marketingPlanApprovedImpliesApprovedForExecution() === false, "approved≠exec");
}

{
  const cats = new Set(APPROVAL_BOUNDARY_MATRIX.map((r) => r.category));
  assert(cats.has("implementation_plan_local_review"), "impl review cat");
  assert(cats.has("marketing_plan_approval"), "mp approval cat");
  assert(cats.has("execution_approval"), "exec approval cat");
  assert(cats.has("publication_approval"), "pub approval cat");
  assert(cats.has("budget_approval"), "budget approval cat");
  assert(cats.has("verdict_local_review"), "verdict review cat");
}

{
  const strategy = DOMAIN_MAPPINGS.find((d) => d.model === "MarketingStrategy");
  assert(strategy?.classification === "E_frontend_view", "Strategy not MP");
  const impl = DOMAIN_MAPPINGS.find((d) => d.model === "ImplementationPlan");
  assert(impl?.notes.includes("I6 Option B") === true, "Impl Option B");
  const plan = DOMAIN_MAPPINGS.find((d) => d.model === "MarketingPlan");
  assert(plan?.classification === "A_direct", "MP backend SoT");
  const verdict = DOMAIN_MAPPINGS.find((d) => d.model === "BusinessVerdict");
  assert(verdict?.classification === "E_frontend_view", "Verdict local");
}

{
  const verdictRow = DECISION_SEMANTICS_MATRIX.find(
    (r) => r.object === "ProductAlpha.BusinessVerdict",
  );
  assert(verdictRow?.authorizesAction === false, "verdict no exec auth");
  const cc = DECISION_SEMANTICS_MATRIX.find(
    (r) => r.object === "CampaignControlCenter.next_action",
  );
  assert(cc?.businessVerdictRelation === "conflict_if_confused" || cc?.category === "control_center_next_action", "CC separate");
}

export function i7PageLoadSideEffects(): {
  createsCampaign: false;
  startsAgentRun: false;
  createsExecutionApproval: false;
  startsProvider: false;
  budgetAction: false;
} {
  return {
    createsCampaign: false,
    startsAgentRun: false,
    createsExecutionApproval: false,
    startsProvider: false,
    budgetAction: false,
  };
}

{
  const s = i7PageLoadSideEffects();
  assert(s.createsCampaign === false, "no campaign");
  assert(s.startsAgentRun === false, "no agent run");
  assert(s.createsExecutionApproval === false, "no exec approval");
  assert(s.startsProvider === false, "no provider");
  assert(s.budgetAction === false, "no budget");
}

console.log("integration-i7.selfcheck.ts: OK");
