/**
 * Deterministic execution readiness — not real execution approval.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type {
  ExecutionReadinessResult,
  MarketingStrategy,
} from "@/lib/strategy/types";

export function evaluateExecutionReadiness(
  strategy: Pick<
    MarketingStrategy,
    | "objectives"
    | "segments"
    | "offers"
    | "channels"
    | "metrics"
    | "conditions"
    | "assumptions"
    | "budget"
    | "positioning"
    | "verdictType"
  >,
  verdict: BusinessVerdict,
): ExecutionReadinessResult {
  const blockers: string[] = [];
  const unresolvedConditions: string[] = [];
  const missingElements: string[] = [];

  const mandatoryOpen = strategy.conditions.filter((c) => c.blocksExecution);
  for (const c of mandatoryOpen) {
    unresolvedConditions.push(c.unresolvedCondition);
    blockers.push(`Обязательное условие: ${c.unresolvedCondition}`);
  }

  if (strategy.objectives.length === 0) {
    missingElements.push("Нет стратегических objectives");
  }
  if (!strategy.segments.some((s) => s.priority === "primary")) {
    missingElements.push("Нет primary сегмента");
  }
  if (!strategy.positioning.keyMessage.trim()) {
    missingElements.push("Positioning key message пустой");
  }
  if (!strategy.offers.some((o) => o.kind === "core" || o.kind === "validation")) {
    missingElements.push("Нет core/validation offer");
  }
  if (!strategy.channels.some((c) => c.status === "recommended" || c.status === "test")) {
    missingElements.push("Нет recommended/test каналов");
  }
  if (strategy.metrics.length < 3) {
    missingElements.push("Недостаточно decision metrics");
  }

  const budgetUnknown = strategy.budget.every(
    (b) =>
      b.amountOrRange.toLowerCase().includes("unknown") ||
      b.amountOrRange.toLowerCase().includes("insufficient"),
  );
  if (budgetUnknown && verdict.type === "GO") {
    missingElements.push("Budget clarity недостаточна для planning");
  }

  const riskAssumptions = strategy.assumptions.filter(
    (a) => a.status === "requires_validation",
  );

  if (verdict.type === "CONDITIONAL_GO" && mandatoryOpen.length > 0) {
    return {
      status: "blocked",
      blockers,
      unresolvedConditions,
      missingElements,
      nextRequiredAction:
        "Закройте обязательные условия вердикта до плана реализации.",
      notRealExecutionApproval: true,
    };
  }

  if (blockers.length > 0 || missingElements.length >= 3) {
    return {
      status: "not_ready",
      blockers,
      unresolvedConditions,
      missingElements,
      nextRequiredAction: "Дополните стратегию и снимите blockers.",
      notRealExecutionApproval: true,
    };
  }

  if (
    verdict.type === "CONDITIONAL_GO" ||
    riskAssumptions.length > 0 ||
    missingElements.length > 0 ||
    budgetUnknown
  ) {
    return {
      status: "conditionally_ready",
      blockers,
      unresolvedConditions,
      missingElements,
      nextRequiredAction:
        "Можно планировать validation workstreams; полный execution plan — после условий.",
      notRealExecutionApproval: true,
    };
  }

  return {
    status: "ready_for_planning",
    blockers: [],
    unresolvedConditions: [],
    missingElements: [],
    nextRequiredAction: "Подготовить план реализации (Phase A6 placeholder).",
    notRealExecutionApproval: true,
  };
}
