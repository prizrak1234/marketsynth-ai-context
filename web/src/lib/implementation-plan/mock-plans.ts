/**
 * Prepare / regenerate implementation plans for GO and CONDITIONAL_GO.
 */

import { prepareStrategyForProject, ensureVerdict } from "@/lib/strategy/mock-strategies";
import { getCurrentStrategy } from "@/lib/strategy/storage";
import {
  applyRejectedBudgetGate,
  buildImplementationPlan,
} from "@/lib/implementation-plan/build-plan";
import { resolveImplementationAccess } from "@/lib/implementation-plan/routing";
import {
  commitPlanVersion,
  getCurrentPlan,
  nextPlanVersion,
} from "@/lib/implementation-plan/storage";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";

export function preparePlanForProject(
  projectId: string,
  options: { regenerate?: boolean } = {},
): ImplementationPlan {
  const verdict = ensureVerdict(projectId);
  const strategy =
    getCurrentStrategy(projectId) ?? prepareStrategyForProject(projectId);
  const access = resolveImplementationAccess(verdict, strategy);
  if (!access.allow) {
    throw new Error(access.reason);
  }

  const existing = getCurrentPlan(projectId);
  if (existing && !options.regenerate) {
    return existing;
  }

  const version = nextPlanVersion(projectId);
  const plan = buildImplementationPlan(verdict, strategy, {
    version,
    supersedesPlanId: existing?.id ?? null,
  });
  commitPlanVersion(plan);
  return plan;
}

/** Test helper: GO plan with rejected acquisition budget gate. */
export function buildRejectedBudgetScenario(projectId: string): ImplementationPlan {
  const verdict = ensureVerdict(projectId);
  const strategy =
    getCurrentStrategy(projectId) ?? prepareStrategyForProject(projectId);
  const plan = buildImplementationPlan(verdict, strategy, {
    version: 1,
    supersedesPlanId: null,
  });
  return applyRejectedBudgetGate(plan);
}

export { ensureVerdict };
