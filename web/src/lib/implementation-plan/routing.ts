/**
 * Access control for Implementation Plan Workspace.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import type { ImplementationAccessDecision } from "@/lib/implementation-plan/types";
import {
  investigationHref,
  pivotHref,
  strategyHref,
  verdictHref,
} from "@/lib/strategy/routing";

export function resolveImplementationAccess(
  verdict: BusinessVerdict | null,
  strategy: MarketingStrategy | null,
): ImplementationAccessDecision {
  if (!verdict) {
    return {
      allow: false,
      redirect: "investigation",
      reason: "Нет вердикта — сначала Investigation / Verdict.",
    };
  }

  if (verdict.type === "NO_GO") {
    return {
      allow: false,
      redirect: "pivot",
      reason: "NO_GO — implementation plan не строится. Открыт Pivot.",
    };
  }

  if (verdict.type === "INSUFFICIENT_DATA") {
    return {
      allow: false,
      redirect: "investigation",
      reason: "INSUFFICIENT_DATA — вернитесь к сбору evidence.",
    };
  }

  if (!strategy) {
    return {
      allow: false,
      redirect: "strategy",
      reason: "Нет стратегии — сначала Strategy Workspace.",
    };
  }

  if (verdict.type === "GO") {
    return { allow: true, mode: "go" };
  }

  if (verdict.type === "CONDITIONAL_GO") {
    return { allow: true, mode: "conditional_go" };
  }

  return {
    allow: false,
    redirect: "strategy",
    reason: "Стратегия недоступна для этого вердикта.",
  };
}

export function implementationHref(projectId: string): string {
  return `/workspace/projects/${projectId}/implementation`;
}

export function redirectHref(
  projectId: string,
  redirect: "pivot" | "investigation" | "strategy",
): string {
  if (redirect === "pivot") return pivotHref(projectId);
  if (redirect === "investigation") return investigationHref(projectId);
  return strategyHref(projectId);
}

export { verdictHref, strategyHref };
