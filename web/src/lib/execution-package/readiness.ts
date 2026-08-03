/**
 * Execution package readiness — not real execution.
 */

import type {
  DryRunReport,
  ExecutionPackage,
  PackageReadinessResult,
  PreflightCheck,
} from "@/lib/execution-package/types";

export function evaluatePackageReadiness(input: {
  verdictType: string;
  preflight: PreflightCheck[];
  blockers: { description: string }[];
  budgetMode: string;
  budgetState: string;
  approvals: { gate: string; status: string }[];
  providers: { providerType: string; authenticationState: string }[];
  verificationGaps: string[];
  rollbackGaps: string[];
  dryRun: DryRunReport | null;
  packageStatus: ExecutionPackage["status"];
}): PackageReadinessResult {
  const blockingReasons: string[] = [];
  const warnings: string[] = [];
  const missingApprovals: string[] = [];
  const missingProviderSetup: string[] = [];

  for (const c of input.preflight) {
    if (c.result === "failed" && c.blocking) {
      blockingReasons.push(c.title);
    } else if (c.result === "warning") {
      warnings.push(c.title);
    }
  }

  for (const b of input.blockers) {
    blockingReasons.push(b.description);
  }

  for (const a of input.approvals) {
    if (
      a.gate === "publication_approval" ||
      a.gate === "provider_configuration_approval"
    ) {
      if (a.status === "rejected") {
        missingApprovals.push(`${a.gate}: ${a.status}`);
      }
      continue;
    }
    if (
      (a.gate === "execution_approval" || a.gate === "budget_approval") &&
      (a.status === "rejected" || a.status === "blocked")
    ) {
      missingApprovals.push(`${a.gate}: ${a.status}`);
    } else if (
      (a.gate === "execution_approval" || a.gate === "budget_approval") &&
      a.status === "pending"
    ) {
      warnings.push(`Pending approval: ${a.gate}`);
    }
  }

  for (const p of input.providers) {
    if (
      p.authenticationState !== "not_required" &&
      p.authenticationState !== "mock_ready" &&
      p.authenticationState !== "ready"
    ) {
      missingProviderSetup.push(`${p.providerType}: ${p.authenticationState}`);
    }
  }

  if (input.budgetMode === "unknown" || input.budgetState === "blocked") {
    blockingReasons.push("Budget authorization unknown/blocked");
  }

  if (input.budgetState === "rejected") {
    blockingReasons.push("Budget authorization rejected");
  }

  if (input.dryRun?.result === "blocked") {
    blockingReasons.push("Dry-run result blocked");
  }

  const verificationGaps = input.verificationGaps;
  const rollbackGaps = input.rollbackGaps;

  if (blockingReasons.length > 0) {
    return {
      status: "blocked",
      blockingReasons,
      warnings,
      missingApprovals,
      missingProviderSetup,
      verificationGaps,
      rollbackGaps,
      nextRequiredAction: "Закройте blocking preflight / conditions / budget gaps.",
      notRealExecution: true,
    };
  }

  if (input.verdictType === "CONDITIONAL_GO") {
    return {
      status: "conditionally_ready",
      blockingReasons: [],
      warnings: [...warnings, ...missingApprovals],
      missingApprovals,
      missingProviderSetup,
      verificationGaps,
      rollbackGaps,
      nextRequiredAction:
        "Пакет можно собрать; утверждение dry-run — после закрытия conditions.",
      notRealExecution: true,
    };
  }

  if (missingApprovals.some((m) => m.includes("rejected") || m.includes("blocked"))) {
    return {
      status: "not_ready",
      blockingReasons: missingApprovals,
      warnings,
      missingApprovals,
      missingProviderSetup,
      verificationGaps,
      rollbackGaps,
      nextRequiredAction: "Resolve rejected/blocked approvals.",
      notRealExecution: true,
    };
  }

  if (
    input.dryRun?.result === "passed" ||
    input.dryRun?.result === "passed_with_warnings"
  ) {
    if (
      input.packageStatus === "approved" ||
      input.packageStatus === "approval_pending"
    ) {
      return {
        status: "approved_for_dry_run",
        blockingReasons: [],
        warnings: [
          ...warnings,
          ...(input.dryRun.result === "passed_with_warnings"
            ? ["Dry-run passed with warnings"]
            : []),
        ],
        missingApprovals,
        missingProviderSetup,
        verificationGaps,
        rollbackGaps,
        nextRequiredAction:
          "Dry run доступен локально. Real execution — Architecture V2.2.",
        notRealExecution: true,
      };
    }
  }

  return {
    status: "ready_for_approval",
    blockingReasons: [],
    warnings,
    missingApprovals,
    missingProviderSetup,
    verificationGaps,
    rollbackGaps,
    nextRequiredAction: "Подготовить к утверждению / Запустить dry run.",
    notRealExecution: true,
  };
}
