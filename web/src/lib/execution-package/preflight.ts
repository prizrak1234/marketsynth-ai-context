/**
 * Deterministic preflight checks — local only.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";
import type {
  ApprovalMatrixRow,
  BudgetAuthorization,
  ExecutionItem,
  ExecutionScopeItem,
  PreflightCheck,
  ProviderRequirement,
  RollbackPlanEntry,
  VerificationPlanEntry,
} from "@/lib/execution-package/types";

export function runPreflightChecks(input: {
  verdict: BusinessVerdict;
  strategy: MarketingStrategy;
  plan: ImplementationPlan;
  scope: ExecutionScopeItem[];
  items: ExecutionItem[];
  providers: ProviderRequirement[];
  approvals: ApprovalMatrixRow[];
  budget: BudgetAuthorization;
  verification: VerificationPlanEntry[];
  rollback: RollbackPlanEntry[];
}): PreflightCheck[] {
  const { verdict, strategy, plan, scope, items, providers, approvals, budget, verification, rollback } =
    input;
  const checks: PreflightCheck[] = [];

  checks.push({
    id: "pf_verdict",
    category: "verdict integrity",
    title: "Verdict is GO or CONDITIONAL_GO and versioned",
    result:
      verdict.type === "GO" || verdict.type === "CONDITIONAL_GO" ? "passed" : "failed",
    severity: "critical",
    evidence: `${verdict.type} v${verdict.version}`,
    blocking: true,
    resolutionAction: "Return to Verdict Workspace",
  });

  checks.push({
    id: "pf_strategy",
    category: "strategy integrity",
    title: "Strategy available and linked",
    result: strategy.id ? "passed" : "failed",
    severity: "critical",
    evidence: `Strategy v${strategy.version}`,
    blocking: true,
    resolutionAction: "Open Strategy Workspace",
  });

  checks.push({
    id: "pf_plan",
    category: "implementation completeness",
    title: "Implementation plan has workstreams and tasks",
    result:
      plan.workstreams.length > 0 && plan.tasks.length > 0 ? "passed" : "failed",
    severity: "critical",
    evidence: `${plan.workstreams.length} workstreams / ${plan.tasks.length} tasks`,
    blocking: true,
    resolutionAction: "Complete Implementation Plan",
  });

  const openConditions = plan.conditions.filter(
    (c) => c.blocksPlanning && (c.status === "open" || c.status === "in_progress"),
  );
  checks.push({
    id: "pf_conditions",
    category: "implementation completeness",
    title: "Mandatory verdict/plan conditions",
    result: openConditions.length === 0 ? "passed" : "failed",
    severity: "critical",
    evidence:
      openConditions.length === 0
        ? "No open blocking conditions"
        : openConditions.map((c) => c.requiredAction).join("; "),
    blocking: true,
    resolutionAction: "Close mandatory conditions before external actions",
  });

  const pendingCriticalApprovals = approvals.filter(
    (a) =>
      (a.gate === "execution_approval" ||
        a.gate === "budget_approval" ||
        a.gate === "publication_approval") &&
      (a.status === "pending" || a.status === "blocked" || a.status === "rejected"),
  );
  checks.push({
    id: "pf_approvals",
    category: "approval coverage",
    title: "Critical approval coverage",
    result:
      pendingCriticalApprovals.some((a) => a.status === "rejected")
        ? "failed"
        : pendingCriticalApprovals.length > 0
          ? "warning"
          : "passed",
    severity: "high",
    evidence: pendingCriticalApprovals.map((a) => `${a.gate}:${a.status}`).join(", ") || "ok",
    blocking: pendingCriticalApprovals.some((a) => a.status === "rejected"),
    resolutionAction: "Resolve approval matrix before dry-run approval",
  });

  checks.push({
    id: "pf_budget",
    category: "budget coverage",
    title: "Budget authorization clarity",
    result:
      budget.mode === "unknown" || budget.approvalState === "blocked"
        ? "failed"
        : budget.mode === "requires_approval" || budget.approvalState === "pending"
          ? "warning"
          : "passed",
    severity: "high",
    evidence: `${budget.mode} / ${budget.approvalState}`,
    blocking: budget.mode === "unknown" || budget.approvalState === "blocked",
    resolutionAction: "Provide budget range or keep authorization blocked",
  });

  const externalProviders = providers.filter(
    (p) =>
      p.authenticationState !== "not_required" &&
      p.authenticationState !== "mock_ready" &&
      p.authenticationState !== "ready",
  );
  checks.push({
    id: "pf_providers",
    category: "provider readiness",
    title: "Provider configuration for external actions",
    result: externalProviders.length === 0 ? "passed" : "warning",
    severity: "high",
    evidence:
      externalProviders.map((p) => `${p.providerType}:${p.authenticationState}`).join(", ") ||
      "mock_ready / not_required",
    blocking: false,
    resolutionAction: "Keep provider actions blocked until mock_ready or Architecture V2.2",
  });

  const blockedPublication = items.filter(
    (i) =>
      (i.actionClass === "publication" ||
        i.actionClass === "budget_change" ||
        i.actionClass === "provider_configuration") &&
      i.status !== "excluded" &&
      i.status !== "blocked",
  );
  checks.push({
    id: "pf_assets",
    category: "asset readiness",
    title: "External mutation actions remain blocked/excluded",
    result: blockedPublication.length === 0 ? "passed" : "failed",
    severity: "critical",
    evidence:
      blockedPublication.length === 0
        ? "Publication/budget/provider config blocked or excluded"
        : blockedPublication.map((i) => i.id).join(", "),
    blocking: true,
    resolutionAction: "Exclude or block publication/budget/provider configuration items",
  });

  checks.push({
    id: "pf_data",
    category: "data readiness",
    title: "Evidence snapshot reference present",
    result: plan.evidenceSnapshotId ? "passed" : "warning",
    severity: "medium",
    evidence: plan.evidenceSnapshotId || "missing",
    blocking: false,
    resolutionAction: "Attach evidence snapshot id from investigation",
  });

  const highRiskNoRollback = items.filter((i) => {
    if (i.status === "excluded" || i.riskLevel !== "high" && i.riskLevel !== "critical") {
      return false;
    }
    const rb = rollback.find((r) => r.executionItemId === i.id);
    return !rb || rb.state === "unavailable";
  });
  checks.push({
    id: "pf_rollback",
    category: "rollback readiness",
    title: "High-risk items have rollback coverage",
    result: highRiskNoRollback.length === 0 ? "passed" : "failed",
    severity: "critical",
    evidence:
      highRiskNoRollback.length === 0
        ? "Rollback defined or not_required"
        : highRiskNoRollback.map((i) => i.id).join(", "),
    blocking: true,
    resolutionAction: "Define rollback or exclude high-risk items",
  });

  const unavailableVerification = verification.filter(
    (v) => v.verificationMethod === "unavailable" && !v.acknowledgmentRequired,
  );
  checks.push({
    id: "pf_verification",
    category: "verification readiness",
    title: "Verification methods available or acknowledged",
    result: unavailableVerification.length === 0 ? "passed" : "failed",
    severity: "high",
    evidence:
      unavailableVerification.length === 0
        ? "Verification covered"
        : unavailableVerification.map((v) => v.executionItemId).join(", "),
    blocking: unavailableVerification.length > 0,
    resolutionAction: "Acknowledge unavailable verification or change method",
  });

  const includedScope = scope.filter((s) => s.inclusion === "included");
  checks.push({
    id: "pf_scope",
    category: "tenant / project scope integrity",
    title: "Execution scope non-empty for included items",
    result: includedScope.length > 0 ? "passed" : "failed",
    severity: "critical",
    evidence: `${includedScope.length} included scope items`,
    blocking: true,
    resolutionAction: "Include at least planning-safe scope items",
  });

  checks.push({
    id: "pf_risk",
    category: "risk mitigation",
    title: "Critical open plan risks translated",
    result: plan.risks.some((r) => r.severity === "critical" && r.status === "open")
      ? "failed"
      : "passed",
    severity: "critical",
    evidence: plan.risks
      .filter((r) => r.severity === "critical" && r.status === "open")
      .map((r) => r.title)
      .join("; ") || "none open",
    blocking: true,
    resolutionAction: "Mitigate or accept critical risks before package approval",
  });

  return checks;
}
