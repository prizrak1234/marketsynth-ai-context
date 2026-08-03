/**
 * Execution planning readiness — not real execution.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import type {
  ImplementationPlan,
  PlanningReadinessResult,
} from "@/lib/implementation-plan/types";

export function evaluatePlanningReadiness(
  plan: Pick<
    ImplementationPlan,
    | "workstreams"
    | "milestones"
    | "tasks"
    | "budgetPlan"
    | "budgetGates"
    | "approvalGates"
    | "conditions"
    | "risks"
    | "assumptions"
    | "deliverables"
    | "status"
  >,
  strategy: MarketingStrategy,
  verdict: BusinessVerdict,
): PlanningReadinessResult {
  const blockers: string[] = [];
  const unresolvedGates: string[] = [];
  const incompleteWorkstreams: string[] = [];
  const criticalMissingInputs: string[] = [];

  const openConditions = plan.conditions.filter(
    (c) => c.blocksPlanning && (c.status === "open" || c.status === "in_progress"),
  );
  for (const c of openConditions) {
    blockers.push(`Обязательное условие: ${c.requiredAction}`);
  }

  for (const g of plan.budgetGates) {
    if (g.status === "rejected" || g.status === "blocked") {
      unresolvedGates.push(`Budget gate: ${g.name} (${g.status})`);
      blockers.push(`Budget gate ${g.name} blocks dependent work`);
    } else if (g.status === "pending") {
      unresolvedGates.push(`Budget gate pending: ${g.name}`);
    }
  }

  for (const g of plan.approvalGates) {
    if (g.status === "rejected" || g.status === "blocked") {
      unresolvedGates.push(`Approval gate: ${g.title} (${g.status})`);
      if (g.status === "rejected") {
        blockers.push(`Approval rejected: ${g.title}`);
      }
    } else if (g.status === "pending") {
      unresolvedGates.push(`Approval gate pending: ${g.title}`);
    }
  }

  for (const ws of plan.workstreams) {
    if (!ws.successCriteria.trim()) {
      incompleteWorkstreams.push(`${ws.title} (missing success criteria)`);
    }
    if (ws.status === "blocked" && (ws.priority === "critical" || ws.priority === "high")) {
      incompleteWorkstreams.push(`${ws.title} (blocked)`);
    }
  }

  const tasksWithoutAcceptance = plan.tasks.filter(
    (t) =>
      (t.priority === "critical" || t.priority === "high") &&
      !t.acceptanceCriteria.trim(),
  );
  if (tasksWithoutAcceptance.length > 0) {
    criticalMissingInputs.push("Critical/high tasks without acceptance criteria");
    blockers.push("Missing acceptance criteria on critical/high tasks");
  }

  const criticalOpenRisks = plan.risks.filter(
    (r) => r.severity === "critical" && r.status === "open",
  );
  for (const r of criticalOpenRisks) {
    blockers.push(`Critical risk open: ${r.title}`);
  }

  if (plan.deliverables.length < 3) {
    criticalMissingInputs.push("Deliverables register incomplete");
  }

  if (
    strategy.executionReadiness.status === "blocked" ||
    strategy.status === "blocked"
  ) {
    blockers.push("Strategy execution readiness / status is blocked");
  }

  const budgetUnknown = plan.budgetPlan.every(
    (b) => b.mode === "unknown" || b.mode === "requires_approval",
  );

  const rejectedBudget = plan.budgetGates.some((g) => g.status === "rejected");

  if (openConditions.length > 0 || criticalOpenRisks.length > 0 || rejectedBudget) {
    return {
      status: "blocked",
      blockers,
      unresolvedGates,
      incompleteWorkstreams,
      criticalMissingInputs,
      recommendedNextAction:
        "Закройте обязательные условия, critical risks и rejected budget gates до пакета исполнения.",
      notRealExecution: true,
    };
  }

  if (
    tasksWithoutAcceptance.length > 0 ||
    criticalMissingInputs.includes("Deliverables register incomplete") ||
    strategy.executionReadiness.status === "blocked"
  ) {
    return {
      status: "not_ready",
      blockers,
      unresolvedGates,
      incompleteWorkstreams,
      criticalMissingInputs,
      recommendedNextAction: "Дополните plan artifacts и acceptance criteria.",
      notRealExecution: true,
    };
  }

  // Pending pilot/execution gates are expected placeholders — not readiness blockers for GO.
  // Conditionally_ready only for CONDITIONAL_GO, unknown budget, or validation assumptions.
  if (
    verdict.type === "CONDITIONAL_GO" ||
    budgetUnknown ||
    plan.assumptions.some((a) => a.status === "requires_validation") ||
    incompleteWorkstreams.some((w) => w.includes("blocked"))
  ) {
    return {
      status: "conditionally_ready",
      blockers,
      unresolvedGates,
      incompleteWorkstreams,
      criticalMissingInputs,
      recommendedNextAction:
        "Можно готовить validation workstreams; полный execution package — после gates.",
      notRealExecution: true,
    };
  }

  return {
    status: "ready_for_approval",
    blockers: [],
    unresolvedGates,
    incompleteWorkstreams: [],
    criticalMissingInputs: [],
    recommendedNextAction: "Подготовить пакет исполнения (Phase A7 placeholder).",
    notRealExecution: true,
  };
}
