/**
 * P1.2 MarketingPlan handoff adapter selfcheck.
 * Run: npx --yes tsx src/lib/integration/marketing-plan-handoff-p1-2.selfcheck.ts
 */

import { mapMarketingPlanHandoffPreview } from "@/lib/integration/marketing-plan-handoff-preview-adapter";
import { mapMarketingPlanLineageFromContext } from "@/lib/integration/marketing-plan-lineage-adapter";
import type { BackendMarketingPlanHandoffPreviewDto } from "@/lib/api/types/marketing-plan-handoff";

function assert(cond: unknown, msg: string): void {
  if (!cond) throw new Error(msg);
}

const dto: BackendMarketingPlanHandoffPreviewDto = {
  handoff_id: "h1",
  implementation_plan_id: "p1",
  implementation_plan_version: 2,
  mapping_version: "implementation_to_marketing_plan.v1",
  mapping_fingerprint: "abc",
  project_id: "proj",
  proposed_title: "Plan",
  proposed_goal: "Goal",
  included_tasks: [],
  transformed_tasks: [
    {
      implementation_task_id: "t1",
      title: "Research",
      classification: "transformable",
      reason: "degraded ac",
      mapped_specialist: "researcher",
      mapped_objective: "Do research",
      mapped_expected_output: "Notes",
      acceptance_criteria_mode: "degraded_into_expected_output",
      dependency_mode: "none",
      responsible_role: "Research Director",
    },
  ],
  excluded_tasks: [],
  unsupported_tasks: [
    {
      implementation_task_id: "t2",
      title: "Owner decide",
      classification: "unsupported",
      reason: "Client Owner",
      mapped_specialist: null,
      mapped_objective: null,
      mapped_expected_output: null,
      acceptance_criteria_mode: "none",
      dependency_mode: "none",
      responsible_role: "Client Owner",
    },
  ],
  blocked_tasks: [],
  role_mapping_notes: ["Research Director → researcher"],
  dependency_warnings: ["deps degraded"],
  acceptance_criteria_warnings: ["folded"],
  gate_blockers: [],
  existing_marketing_plans: [{ id: "mp1", title: "Old", status: "draft", version: 1 }],
  duplicate_handoff_id: null,
  eligible: true,
  blockers: [],
  warnings: [],
  side_effects: [],
  creates_marketing_plan_draft: false,
  creates_marketing_plan_approval: false,
  creates_agent_run: false,
  creates_campaign: false,
  dispatches_specialist_tasks: false,
};

const view = mapMarketingPlanHandoffPreview(dto);
assert(view.ctaCheckLabel.includes("Проверить готовность"), "cta check");
assert(view.ctaConfirmLabel.includes("черновик"), "cta confirm");
assert(view.createsApproval === false, "no approval");
assert(view.createsAgentRun === false, "no agent run");
assert(view.transformed.length === 1, "transformed");
assert(view.unsupported.length === 1, "unsupported");

const lineage = mapMarketingPlanLineageFromContext({
  handoff_id: "h1",
  source_implementation_plan_id: "p1",
  mapping_version: "implementation_to_marketing_plan.v1",
});
assert(lineage.handoffId === "h1", "lineage handoff");
assert(lineage.labelRu.includes("draft"), "lineage label");

console.log("marketing-plan-handoff-p1-2.selfcheck: OK");
