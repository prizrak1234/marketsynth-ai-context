/**
 * Verdict-based access control for Strategy Workspace.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { StrategyAccessDecision } from "@/lib/strategy/types";

export function resolveStrategyAccess(
  verdict: BusinessVerdict | null,
): StrategyAccessDecision {
  if (!verdict) {
    return {
      allow: false,
      redirect: "investigation",
      reason: "Нет активного вердикта — сначала завершите Investigation / Verdict.",
    };
  }

  if (verdict.type === "GO") {
    return { allow: true, mode: "go" };
  }

  if (verdict.type === "CONDITIONAL_GO") {
    return { allow: true, mode: "conditional_go" };
  }

  if (verdict.type === "NO_GO") {
    return {
      allow: false,
      redirect: "pivot",
      reason:
        "Вердикт NO_GO — полноценная стратегия не строится. Открыт Pivot / Rework path.",
    };
  }

  return {
    allow: false,
    redirect: "investigation",
    reason:
      "INSUFFICIENT_DATA — вернитесь в Investigation и закройте evidence gaps до стратегии.",
  };
}

export function strategyHref(projectId: string): string {
  return `/workspace/projects/${projectId}/strategy`;
}

export function pivotHref(projectId: string): string {
  return `/workspace/projects/${projectId}/pivot`;
}

export function investigationHref(projectId: string): string {
  return `/workspace/projects/${projectId}/investigation`;
}

export function verdictHref(projectId: string): string {
  return `/workspace/projects/${projectId}/verdict`;
}
