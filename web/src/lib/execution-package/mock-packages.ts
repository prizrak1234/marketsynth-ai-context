/**
 * Prepare / regenerate execution packages.
 */

import { preparePlanForProject, ensureVerdict } from "@/lib/implementation-plan/mock-plans";
import { getCurrentPlan } from "@/lib/implementation-plan/storage";
import { prepareStrategyForProject } from "@/lib/strategy/mock-strategies";
import { getCurrentStrategy } from "@/lib/strategy/storage";
import {
  buildExecutionPackage,
  refreshPackageDerived,
} from "@/lib/execution-package/build-package";
import { runDryRun, withDryRunReport } from "@/lib/execution-package/dry-run";
import { resolvePackageAccess } from "@/lib/execution-package/routing";
import {
  commitPackageVersion,
  getCurrentPackage,
  nextPackageVersion,
  replaceCurrentPackage,
} from "@/lib/execution-package/storage";
import type { ExecutionPackage } from "@/lib/execution-package/types";

export function preparePackageForProject(
  projectId: string,
  options: { regenerate?: boolean } = {},
): ExecutionPackage {
  const verdict = ensureVerdict(projectId);
  const strategy =
    getCurrentStrategy(projectId) ?? prepareStrategyForProject(projectId);
  const plan = getCurrentPlan(projectId) ?? preparePlanForProject(projectId);

  const access = resolvePackageAccess(verdict, strategy, plan);
  if (!access.allow) {
    throw new Error(access.reason);
  }

  const existing = getCurrentPackage(projectId);
  if (existing && !options.regenerate) {
    return existing;
  }

  const version = nextPackageVersion(projectId);
  const pkg = buildExecutionPackage(verdict, strategy, plan, {
    version,
    supersedesPackageId: existing?.id ?? null,
  });
  commitPackageVersion(pkg);
  return pkg;
}

export function runLocalDryRun(projectId: string): ExecutionPackage {
  const pkg = getCurrentPackage(projectId) ?? preparePackageForProject(projectId);
  const report = runDryRun({
    packageVersion: pkg.version,
    items: pkg.executionItems,
    preflight: pkg.preflightChecks,
    approvals: pkg.approvalMatrix,
    providers: pkg.providerRequirements,
    verification: pkg.verificationPlan,
    rollback: pkg.rollbackPlan,
  });
  const withReport = refreshPackageDerived(withDryRunReport(pkg, report));
  replaceCurrentPackage(withReport);
  return withReport;
}

export { ensureVerdict };
