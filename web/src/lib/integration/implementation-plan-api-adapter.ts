/**
 * P1.1 — backend ImplementationPlan → Product Alpha A6 view model (summary map).
 * Nested lists stay empty in v1 adapter until section mappers expand; lineage/status preserved.
 * Does not collapse with MarketingPlan. No silent mock authority.
 */

import type { BackendImplementationPlanDto } from "@/lib/api/types/implementation-plans";
import type {
  ImplementationPlan,
  PlanStatus,
  PlanningReadinessResult,
} from "@/lib/implementation-plan/types";

function mapStatus(lifecycle: string): PlanStatus {
  if (lifecycle === "approved") return "approved";
  if (lifecycle === "under_review") return "under_review";
  if (lifecycle === "superseded") return "superseded";
  if (lifecycle === "blocked" || lifecycle === "rejected" || lifecycle === "archived") {
    return "blocked";
  }
  return "draft";
}

function mapReadiness(
  raw: string,
  reasons: string[],
): PlanningReadinessResult {
  const status =
    raw === "ready_for_handoff"
      ? "ready_for_approval"
      : raw === "conditionally_ready"
        ? "conditionally_ready"
        : raw === "blocked"
          ? "blocked"
          : "not_ready";
  return {
    status,
    blockers: reasons,
    unresolvedGates: reasons.filter((r) => r.includes("gate")),
    incompleteWorkstreams: [],
    criticalMissingInputs: reasons,
    recommendedNextAction:
      status === "ready_for_approval"
        ? "Проверить handoff preview (P1.2 создаст MarketingPlan draft)"
        : "Дополнить ImplementationPlan / Strategy conditions",
    notRealExecution: true,
  };
}

export function mapBackendImplementationPlanToProductAlpha(
  dto: BackendImplementationPlanDto,
  projectName: string,
): ImplementationPlan {
  return {
    id: dto.id,
    projectId: dto.project_id,
    projectName,
    strategyId: dto.marketing_strategy_id,
    strategyVersion: dto.marketing_strategy_version,
    verdictId: dto.business_verdict_id,
    verdictVersion: dto.business_verdict_version,
    verdictType: "CONDITIONAL_GO",
    version: dto.version,
    status: mapStatus(dto.lifecycle_status),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    updatedAtLabel: new Date(dto.updated_at).toLocaleString("ru-RU"),
    supersedesPlanId: dto.supersedes_plan_id,
    evidenceSnapshotId: dto.evidence_snapshot_id,
    localMockLabel: "",
    overview: {
      strategicObjective: dto.summary.slice(0, 240),
      implementationHorizon: dto.implementation_horizon,
      primaryWorkstreams: (dto.workstreams || [])
        .map((w) => String(w.title ?? w.id ?? ""))
        .filter(Boolean)
        .slice(0, 5),
      criticalMilestones: (dto.milestones || [])
        .map((m) => String(m.title ?? m.id ?? ""))
        .filter(Boolean)
        .slice(0, 5),
      estimatedBudgetRange: "Policy/gates only — not spend authorization",
      mandatoryConditions: (dto.conditions || [])
        .map((c) => String(c.source_id ?? c.id ?? ""))
        .filter(Boolean),
      currentBlockers: dto.readiness_reasons || [],
      readinessLabel: dto.readiness_status,
      nextManagementDecision:
        "Implementation Plan — проектный план реализации Strategy. Он не является MarketingPlan и не разрешает исполнение.",
    },
    workstreams: [],
    milestones: [],
    tasks: [],
    roles: [],
    dependencies: [],
    deliverables: [],
    budgetPlan: [],
    budgetGates: [],
    approvalGates: [],
    conditions: [],
    risks: [],
    assumptions: [],
    roadmap: [],
    readiness: mapReadiness(dto.readiness_status, dto.readiness_reasons || []),
  };
}

export function implementationPlanEqualsMarketingPlan(): false {
  return false;
}

export function planApprovalCreatesMarketingPlan(): false {
  return false;
}

export function planApprovalCreatesSpecialistTasks(): false {
  return false;
}
