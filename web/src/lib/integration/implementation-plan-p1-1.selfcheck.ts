/**
 * P1.1 ImplementationPlan adapter selfcheck.
 * Run: npx --yes tsx src/lib/integration/implementation-plan-p1-1.selfcheck.ts
 */

import {
  implementationPlanEqualsMarketingPlan,
  mapBackendImplementationPlanToProductAlpha,
  planApprovalCreatesMarketingPlan,
  planApprovalCreatesSpecialistTasks,
} from "@/lib/integration/implementation-plan-api-adapter";
import { localImplementationPlanImportPolicy } from "@/lib/integration/implementation-plan-sync";
import { mapHandoffPreview } from "@/lib/integration/implementation-handoff-preview-adapter";
import type { BackendImplementationPlanDto } from "@/lib/api/types/implementation-plans";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

assert(implementationPlanEqualsMarketingPlan() === false, "≠ MarketingPlan");
assert(planApprovalCreatesMarketingPlan() === false, "no plan create");
assert(planApprovalCreatesSpecialistTasks() === false, "no specialist");
assert(localImplementationPlanImportPolicy().autoUpload === false, "no auto upload");

{
  const dto: BackendImplementationPlanDto = {
    id: "p1",
    owner_id: "o",
    project_id: "proj",
    marketing_strategy_id: "s1",
    marketing_strategy_version: 1,
    business_verdict_id: "v1",
    business_verdict_version: 1,
    evidence_snapshot_id: "snap",
    evidence_snapshot_hash: "h".repeat(64),
    version: 1,
    lifecycle_status: "approved",
    plan_origin: "deterministic",
    title: "Plan",
    summary: "Delivery plan for approved Strategy",
    implementation_horizon: "Month 1",
    workstreams: [{ id: "ws1", title: "Validation" }],
    milestones: [],
    tasks: [],
    role_assignments: [],
    dependencies: [],
    deliverables: [],
    budget_plan: {},
    budget_gates: [],
    approval_gates: [],
    conditions: [],
    implementation_risks: [],
    assumptions: [],
    roadmap: [],
    readiness_status: "conditionally_ready",
    readiness_reasons: ["open_conditions"],
    submitted_by: null,
    submitted_at: null,
    approved_by: null,
    approved_at: "2026-01-01T00:00:00Z",
    rejection_reason: null,
    block_reason: null,
    supersedes_plan_id: null,
    creates_marketing_plan: false,
    creates_specialist_tasks: false,
    creates_campaign: false,
    creates_execution_approval: false,
    creates_publication_approval: false,
    creates_agent_run: false,
    is_marketing_plan: false,
    budget_gates_authorize_spend: false,
    approval_gates_are_local_only: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const view = mapBackendImplementationPlanToProductAlpha(dto, "Clinic");
  assert(view.status === "approved", "status");
  assert(view.strategyId === "s1", "strategy pin");
  assert(view.localMockLabel === "", "no mock label");
  assert(view.overview.nextManagementDecision.includes("не является MarketingPlan"), "copy");
}

{
  const preview = mapHandoffPreview({
    plan_id: "p1",
    plan_version: 1,
    eligible: false,
    mapped_task_count: 2,
    unsupported_task_count: 0,
    blocked_task_count: 0,
    unsupported_roles: [],
    dependency_loss: [],
    acceptance_criteria_loss: [],
    budget_gate_gaps: ["bg_acq"],
    approval_gate_gaps: [],
    readiness: "conditionally_ready",
    blockers: ["open_conditions"],
    creates_marketing_plan: false,
    creates_specialist_tasks: false,
    note: "Read-only",
  });
  assert(preview.createsMarketingPlan === false, "preview no create");
  assert(preview.ctaLabel.includes("Проверить готовность"), "cta");
  assert(preview.forbiddenCtAs.includes("Создать MarketingPlan"), "forbidden");
}

console.log("implementation-plan-p1-1.selfcheck: OK");
