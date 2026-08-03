/**
 * Integration I6 selfcheck — ImplementationPlan ≠ MarketingPlan; approval boundaries.
 * Run: npx --yes tsx src/lib/integration/implementation-handoff.selfcheck.ts
 */

import {
  APPROVAL_BOUNDARY_MATRIX,
  READINESS_SEMANTICS,
  implementationPlanApprovalCreatesMarketingPlanApproval,
  marketingPlanApprovalCreatesExecutionApproval,
  marketingPlanApprovalCreatesPublicationApproval,
  marketingPlanApprovedImpliesApprovedForExecution,
  readyForApprovalImpliesReadyForExecution,
  verdictApprovalCreatesMarketingPlanApproval,
} from "@/lib/integration/approval-boundary";
import { writeBlockedNoCreateApi } from "@/lib/integration/handoff-errors";
import {
  IMPLEMENTATION_SEMANTICS_MATRIX,
  buildMarketingPlanHandoffPreview,
  i6WritePolicy,
  implementationPlanEqualsMarketingPlan,
} from "@/lib/integration/implementation-marketing-plan-mapping";
import { futureExecutionChainDocumented } from "@/lib/integration/implementation-plan-adapter";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(implementationPlanEqualsMarketingPlan() === false, "ImplPlan ≠ MP");
  const policy = i6WritePolicy();
  assert(policy.mode === "controlled_handoff", "controlled handoff");
  assert(policy.draftConversion === "explicit_preview_confirm_draft_only", "draft only");
  assert(policy.autoOnPageLoad === false, "no auto convert");
  assert(policy.overwriteApprovedPlan === false, "no overwrite");
  assert(policy.autoApprove === false, "no auto approve");
  assert(policy.autoAgentRun === false, "no agent run");
  assert(policy.autoCampaign === false, "no campaign");
  assert(policy.autoProvider === false, "no provider");
  assert(writeBlockedNoCreateApi().kind === "write_blocked", "local preview blocker");
  assert(
    writeBlockedNoCreateApi().actionHint.includes("черновик"),
    "handoff CTA hint",
  );
}

{
  assert(implementationPlanApprovalCreatesMarketingPlanApproval() === false, "local≠mp");
  assert(marketingPlanApprovalCreatesExecutionApproval() === false, "mp≠exec");
  assert(marketingPlanApprovalCreatesPublicationApproval() === false, "mp≠pub");
  assert(verdictApprovalCreatesMarketingPlanApproval() === false, "verdict≠mp");
  assert(readyForApprovalImpliesReadyForExecution() === false, "ready≠exec");
  assert(marketingPlanApprovedImpliesApprovedForExecution() === false, "approved≠exec");
  for (const row of APPROVAL_BOUNDARY_MATRIX) {
    if (row.category === "implementation_plan_local_review") {
      assert(row.createsMarketingPlanApproval === false, "impl local");
      assert(row.createsExecutionApproval === false, "impl no exec");
    }
    if (row.category === "marketing_plan_approval") {
      assert(row.authorizesExecution === false, "mp no exec auth");
      assert(row.createsExecutionApproval === false, "mp no exec approval create");
    }
  }
  for (const r of READINESS_SEMANTICS) {
    assert(r.equalsOthers === false, `readiness ${r.kind} isolated`);
  }
}

{
  const workstream = IMPLEMENTATION_SEMANTICS_MATRIX.find((r) => r.capability === "workstream");
  assert(workstream?.relationship === "absent", "workstream absent on MP");
  const dep = IMPLEMENTATION_SEMANTICS_MATRIX.find((r) => r.capability === "dependency");
  assert(dep?.relationship === "incompatible", "deps incompatible");
  const approval = IMPLEMENTATION_SEMANTICS_MATRIX.find((r) => r.capability === "approval");
  assert(approval?.relationship === "incompatible", "approval incompatible");
}

{
  const plan = {
    id: "ip1",
    projectId: "proj",
    projectName: "Demo",
    version: 2,
    status: "draft",
    verdictType: "GO",
    verdictVersion: 1,
    strategyVersion: 1,
    evidenceSnapshotId: "ev",
    updatedAtLabel: "now",
    localMockLabel: "mock",
    overview: {
      summary: "s",
      strategicObjective: "Grow leads",
      scope: "scope",
      outOfScope: [],
    },
    workstreams: [],
    milestones: [],
    tasks: [
      {
        id: "t1",
        title: "Content calendar",
        description: "Build calendar",
        workstreamId: "ws1",
        milestoneId: "ms1",
        responsibleRole: "Content Strategist",
        status: "pending",
        priority: "high",
        dependencyIds: ["t0"],
        expectedOutput: "Calendar doc",
        acceptanceCriteria: "Must pass review",
        approvalRequired: true,
        deliverableIds: [],
      },
      {
        id: "t2",
        title: "CEO review",
        description: "Gate",
        workstreamId: "ws1",
        milestoneId: "ms1",
        responsibleRole: "CEO",
        status: "pending",
        priority: "medium",
        dependencyIds: [],
        expectedOutput: "Sign-off",
        acceptanceCriteria: "Signed",
        approvalRequired: true,
        deliverableIds: [],
      },
    ],
    deliverables: [],
    dependencies: [],
    budgetPlan: null,
    budgetGates: [],
    approvalGates: [],
    conditions: [],
    risks: [],
    assumptions: [],
    roadmap: [],
    readiness: { status: "ready_for_approval", blockers: [], notRealExecution: true },
  } as unknown as ImplementationPlan;

  const preview = buildMarketingPlanHandoffPreview(plan);
  assert(preview.writeAllowed === false, "preview no write");
  assert(preview.expectedBackendStatus === "draft", "draft only");
  assert(preview.sideEffects === "none", "no side effects");
  assert(preview.createsCampaign === false, "no campaign");
  assert(preview.createsAgentRun === false, "no agent run");
  assert(preview.createsExecutionApproval === false, "no exec approval");
  assert(preview.approvesMarketingPlan === false, "no auto approve");
  assert(preview.dependencyLoss === true, "dep loss flagged");
  assert(preview.included.some((i) => i.sourceTaskId === "t1"), "content mapped");
  assert(preview.excluded.some((e) => e.sourceTaskId === "t2"), "CEO excluded");
  assert(
    preview.excluded.find((e) => e.sourceTaskId === "t2")?.disposition === "unsupported",
    "CEO unsupported role",
  );
}

{
  const row = DOMAIN_MAPPINGS.find((d) => d.model === "ImplementationPlan");
  assert(row?.notes.includes("I6 Option B") === true, "domain I6");
  const chain = futureExecutionChainDocumented();
  assert(chain[0] === "Implementation Plan", "chain start");
  assert(chain.includes("execution approval"), "chain has exec approval");
  assert(!chain.includes("BotFazer"), "no BotFazer string");
}

console.log("implementation-handoff.selfcheck.ts: OK");
