/**
 * Prepare / regenerate strategy for GO and CONDITIONAL_GO projects.
 */

import { loadInvestigationForVerdict, prepareVerdictForProject } from "@/lib/verdict/mock-verdicts";
import { getCurrentVerdict } from "@/lib/verdict/storage";
import { buildMarketingStrategy } from "@/lib/strategy/build-strategy";
import { resolveStrategyAccess } from "@/lib/strategy/routing";
import {
  commitStrategyVersion,
  getCurrentStrategy,
  nextStrategyVersion,
} from "@/lib/strategy/storage";
import type { MarketingStrategy } from "@/lib/strategy/types";

export function ensureVerdict(projectId: string) {
  return getCurrentVerdict(projectId) ?? prepareVerdictForProject(projectId);
}

export function prepareStrategyForProject(
  projectId: string,
  options: { regenerate?: boolean } = {},
): MarketingStrategy {
  const verdict = ensureVerdict(projectId);
  const access = resolveStrategyAccess(verdict);
  if (!access.allow) {
    throw new Error(access.reason);
  }

  const existing = getCurrentStrategy(projectId);
  if (existing && !options.regenerate) {
    return existing;
  }

  const investigation = loadInvestigationForVerdict(projectId);
  const version = nextStrategyVersion(projectId);
  const strategy = buildMarketingStrategy(verdict, investigation, {
    version,
    supersedesStrategyId: existing?.id ?? null,
  });
  commitStrategyVersion(strategy);
  return strategy;
}
