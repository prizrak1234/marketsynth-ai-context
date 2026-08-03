/**
 * I6 — ImplementationPlan → MarketingPlanDraftInput mapping (preview only).
 * Write conversion blocked until generic create API exists.
 */

import type { ImplementationPlan, PlanTask } from "@/lib/implementation-plan/types";
import {
  ROLE_MAPPINGS,
  type BackendSpecialistType,
  type UiAgencyRole,
} from "@/lib/integration/role-mapping";

export type MappingDisposition = "exact" | "transformed" | "excluded" | "unsupported" | "conflict";

export type MappedSpecialistTaskPreview = {
  sourceTaskId: string;
  sourceTitle: string;
  disposition: MappingDisposition;
  specialist: BackendSpecialistType | null;
  objective: string | null;
  expectedOutput: string | null;
  reason: string;
};

export type HandoffPreview = {
  sourcePlanVersion: number;
  projectId: string;
  mappedGoal: string;
  mappedTitle: string;
  included: MappedSpecialistTaskPreview[];
  excluded: MappedSpecialistTaskPreview[];
  dependencyLoss: true;
  acceptanceCriteriaAsTextOnly: true;
  expectedBackendStatus: "draft";
  sideEffects: "none";
  writeAllowed: false;
  writeBlocker: string;
  createsCampaign: false;
  createsAgentRun: false;
  createsExecutionApproval: false;
  approvesMarketingPlan: false;
};

function specialistForRole(role: string): BackendSpecialistType | null {
  const row = ROLE_MAPPINGS.find((r) => r.uiRole === (role as UiAgencyRole));
  return row?.specialistType ?? null;
}

function mapTask(task: PlanTask): MappedSpecialistTaskPreview {
  const specialist = specialistForRole(task.responsibleRole);
  if (!specialist) {
    return {
      sourceTaskId: task.id,
      sourceTitle: task.title,
      disposition: "unsupported",
      specialist: null,
      objective: null,
      expectedOutput: null,
      reason: `Role «${task.responsibleRole}» has no MarketingSpecialistType — excluded.`,
    };
  }
  if (task.dependencyIds.length > 0) {
    // Still can map text, but mark transformed with dependency loss warning
    return {
      sourceTaskId: task.id,
      sourceTitle: task.title,
      disposition: "transformed",
      specialist,
      objective: `${task.title}. ${task.description}`.slice(0, 2000),
      expectedOutput: [
        task.expectedOutput,
        task.acceptanceCriteria ? `Acceptance (local only): ${task.acceptanceCriteria}` : "",
      ]
        .filter(Boolean)
        .join("\n")
        .slice(0, 2000),
      reason:
        "Dependencies cannot persist on MarketingPlan specialist_tasks — ordering not enforced.",
    };
  }
  return {
    sourceTaskId: task.id,
    sourceTitle: task.title,
    disposition: "transformed",
    specialist,
    objective: `${task.title}. ${task.description}`.slice(0, 2000),
    expectedOutput: [
      task.expectedOutput,
      task.acceptanceCriteria ? `Acceptance (local only): ${task.acceptanceCriteria}` : "",
    ]
      .filter(Boolean)
      .join("\n")
      .slice(0, 2000),
    reason: "Text fields only — acceptance/deps/gates not first-class on MarketingPlan.",
  };
}

/**
 * Build conversion preview — never writes.
 */
export function buildMarketingPlanHandoffPreview(
  plan: ImplementationPlan,
): HandoffPreview {
  const mapped = plan.tasks.map(mapTask);
  const included = mapped.filter(
    (m) => m.disposition === "exact" || m.disposition === "transformed",
  );
  const excluded = mapped.filter(
    (m) =>
      m.disposition === "excluded" ||
      m.disposition === "unsupported" ||
      m.disposition === "conflict",
  );

  return {
    sourcePlanVersion: plan.version,
    projectId: plan.projectId,
    mappedGoal: plan.overview.strategicObjective.slice(0, 2000),
    mappedTitle: `ImplPlan v${plan.version}: ${plan.projectName}`.slice(0, 200),
    included,
    excluded,
    dependencyLoss: true,
    acceptanceCriteriaAsTextOnly: true,
    expectedBackendStatus: "draft",
    sideEffects: "none",
    writeAllowed: false,
    writeBlocker:
      "Local preview only. Durable create: POST .../marketing-plan-handoff/preview then confirm (draft-only).",
    createsCampaign: false,
    createsAgentRun: false,
    createsExecutionApproval: false,
    approvesMarketingPlan: false,
  };
}

export type SemanticsMatrixRow = {
  capability: string;
  strategy: string;
  implementationPlan: string;
  marketingPlan: string;
  relationship:
    | "exact_match"
    | "partial_match"
    | "lower_level"
    | "higher_level"
    | "derived"
    | "incompatible"
    | "absent"
    | "frontend_only";
  sourceOfTruth: string;
};

export const IMPLEMENTATION_SEMANTICS_MATRIX: readonly SemanticsMatrixRow[] = [
  {
    capability: "strategic objective",
    strategy: "objectives / summary",
    implementationPlan: "overview.strategicObjective",
    marketingPlan: "goal (free text)",
    relationship: "partial_match",
    sourceOfTruth: "split — plan goal is ops only",
  },
  {
    capability: "workstream",
    strategy: "n/a",
    implementationPlan: "workstreams[]",
    marketingPlan: "absent",
    relationship: "absent",
    sourceOfTruth: "local ImplementationPlan",
  },
  {
    capability: "milestone",
    strategy: "n/a",
    implementationPlan: "milestones[]",
    marketingPlan: "absent",
    relationship: "absent",
    sourceOfTruth: "local ImplementationPlan",
  },
  {
    capability: "task",
    strategy: "n/a",
    implementationPlan: "PlanTask (PM item)",
    marketingPlan: "specialist_tasks (work instruction)",
    relationship: "lower_level",
    sourceOfTruth: "split — different semantics",
  },
  {
    capability: "specialist assignment",
    strategy: "n/a",
    implementationPlan: "responsibleRole",
    marketingPlan: "specialist enum",
    relationship: "partial_match",
    sourceOfTruth: "subset via ROLE_MAPPINGS",
  },
  {
    capability: "dependency",
    strategy: "n/a",
    implementationPlan: "PlanDependency graph",
    marketingPlan: "absent (hardcoded specialist order only)",
    relationship: "incompatible",
    sourceOfTruth: "local ImplementationPlan",
  },
  {
    capability: "deliverable / acceptance",
    strategy: "n/a",
    implementationPlan: "deliverables + acceptanceCriteria",
    marketingPlan: "expected_output text only",
    relationship: "partial_match",
    sourceOfTruth: "lossy — criteria not first-class",
  },
  {
    capability: "budget / budget gate",
    strategy: "budget policy",
    implementationPlan: "budgetPlan + budgetGates",
    marketingPlan: "absent",
    relationship: "absent",
    sourceOfTruth: "local ImplementationPlan",
  },
  {
    capability: "approval gate",
    strategy: "n/a",
    implementationPlan: "approvalGates[] (local)",
    marketingPlan: "POST .../approve (resource)",
    relationship: "incompatible",
    sourceOfTruth: "split — never collapse",
  },
  {
    capability: "condition / risk / assumption",
    strategy: "yes",
    implementationPlan: "yes",
    marketingPlan: "absent",
    relationship: "absent",
    sourceOfTruth: "Strategy / Implementation local",
  },
  {
    capability: "roadmap",
    strategy: "n/a",
    implementationPlan: "roadmap[]",
    marketingPlan: "absent",
    relationship: "frontend_only",
    sourceOfTruth: "local ImplementationPlan",
  },
  {
    capability: "readiness",
    strategy: "strategy readiness",
    implementationPlan: "PlanningReadinessResult",
    marketingPlan: "status draft|approved|archived",
    relationship: "incompatible",
    sourceOfTruth: "split — never equate",
  },
  {
    capability: "version",
    strategy: "local versions",
    implementationPlan: "local versions",
    marketingPlan: "MarketingPlanVersion",
    relationship: "partial_match",
    sourceOfTruth: "split — link only",
  },
  {
    capability: "approval",
    strategy: "local",
    implementationPlan: "local review",
    marketingPlan: "backend resource approve",
    relationship: "incompatible",
    sourceOfTruth: "per APPROVAL_BOUNDARY_MATRIX",
  },
  {
    capability: "execution handoff",
    strategy: "blocked until I7+",
    implementationPlan: "future A7 paused",
    marketingPlan: "execution-runs API (separate)",
    relationship: "lower_level",
    sourceOfTruth: "execution services — not I6",
  },
] as const;

export function implementationPlanEqualsMarketingPlan(): false {
  return false;
}

export function i6WritePolicy() {
  return {
    mode: "controlled_handoff" as const,
    draftConversion: "explicit_preview_confirm_draft_only" as const,
    autoOnPageLoad: false,
    overwriteApprovedPlan: false,
    autoApprove: false,
    autoAgentRun: false,
    autoCampaign: false,
    autoProvider: false,
  };
}
