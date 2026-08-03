/**
 * Access control for Execution Package Workspace.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";
import type { PackageAccessDecision } from "@/lib/execution-package/types";
import {
  investigationHref,
  pivotHref,
  strategyHref,
  verdictHref,
} from "@/lib/strategy/routing";
import { implementationHref } from "@/lib/implementation-plan/routing";

export function resolvePackageAccess(
  verdict: BusinessVerdict | null,
  strategy: MarketingStrategy | null,
  plan: ImplementationPlan | null,
): PackageAccessDecision {
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
      reason: "NO_GO — execution package не создаётся. Открыт Pivot.",
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

  if (!plan) {
    return {
      allow: false,
      redirect: "implementation",
      reason: "Нет implementation plan — сначала Implementation Plan Workspace.",
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
    redirect: "implementation",
    reason: "Execution package недоступен для этого вердикта.",
  };
}

export function executionPackageHref(projectId: string): string {
  return `/workspace/projects/${projectId}/execution-package`;
}

export function redirectPackageHref(
  projectId: string,
  redirect: "pivot" | "investigation" | "strategy" | "implementation",
): string {
  if (redirect === "pivot") return pivotHref(projectId);
  if (redirect === "investigation") return investigationHref(projectId);
  if (redirect === "strategy") return strategyHref(projectId);
  return implementationHref(projectId);
}

export { verdictHref, strategyHref, implementationHref };
