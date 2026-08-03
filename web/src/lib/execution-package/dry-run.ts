/**
 * Local deterministic dry-run — never calls providers.
 */

import type {
  ApprovalMatrixRow,
  DryRunReport,
  ExecutionItem,
  ExecutionPackage,
  PreflightCheck,
  ProviderRequirement,
  RollbackPlanEntry,
  VerificationPlanEntry,
} from "@/lib/execution-package/types";

export function runDryRun(input: {
  packageVersion: number;
  items: ExecutionItem[];
  preflight: PreflightCheck[];
  approvals: ApprovalMatrixRow[];
  providers: ProviderRequirement[];
  verification: VerificationPlanEntry[];
  rollback: RollbackPlanEntry[];
}): DryRunReport {
  const {
    packageVersion,
    items,
    preflight,
    approvals,
    providers,
    verification,
    rollback,
  } = input;

  const passedChecks = preflight
    .filter((c) => c.result === "passed" || c.result === "not_applicable")
    .map((c) => c.title);
  const warnings = preflight
    .filter((c) => c.result === "warning")
    .map((c) => c.title);
  const blockers = preflight
    .filter((c) => c.result === "failed" && c.blocking)
    .map((c) => c.title);

  const approvalGaps = approvals
    .filter(
      (a) =>
        a.status === "pending" ||
        a.status === "blocked" ||
        a.status === "rejected",
    )
    .filter(
      (a) =>
        a.gate === "execution_approval" ||
        a.gate === "publication_approval" ||
        a.gate === "budget_approval" ||
        a.gate === "provider_configuration_approval",
    )
    .map((a) => `${a.gate}: ${a.status}`);

  const providerGaps = providers
    .filter(
      (p) =>
        p.authenticationState === "missing" ||
        p.authenticationState === "credentials_required" ||
        p.configurationState === "configuration_required",
    )
    .map((p) => `${p.providerType}: ${p.authenticationState}`);

  const verificationGaps = verification
    .filter((v) => v.verificationMethod === "unavailable")
    .map((v) => `${v.executionItemId}: unavailable`);

  const rollbackGaps = rollback
    .filter((r) => r.state === "unavailable")
    .map((r) => `${r.executionItemId}: rollback unavailable`);

  const included = items.filter((i) => i.status !== "excluded");
  const simulatedSequence = included.map(
    (i, idx) => `${idx + 1}. [dry-run only] ${i.actionClass}: ${i.title}`,
  );

  // Missing critical approvals for dry-run approval path
  const missingDryRunApproval = approvals.some(
    (a) =>
      a.gate === "execution_approval" &&
      (a.status === "rejected" || a.status === "blocked"),
  );

  if (missingDryRunApproval) {
    blockers.push("Execution approval rejected/blocked — dry run cannot be approved");
  }

  let result: DryRunReport["result"] = "passed";
  if (blockers.length > 0 || approvalGaps.some((g) => g.includes("rejected"))) {
    result = "blocked";
  } else if (
    warnings.length > 0 ||
    approvalGaps.length > 0 ||
    providerGaps.length > 0 ||
    verificationGaps.length > 0 ||
    rollbackGaps.length > 0
  ) {
    result = "passed_with_warnings";
  }

  return {
    packageVersion,
    checkedItems: included.length + preflight.length,
    passedChecks,
    warnings,
    blockers,
    simulatedSequence,
    approvalGaps,
    providerGaps,
    verificationGaps,
    rollbackGaps,
    result,
    externalActionsPerformed: false,
    generatedAt: new Date().toISOString(),
  };
}

/** Attach dry-run report to package (immutable update). */
export function withDryRunReport(
  pkg: ExecutionPackage,
  report: DryRunReport,
): ExecutionPackage {
  return {
    ...pkg,
    dryRunReport: report,
    updatedAt: new Date().toISOString(),
  };
}
