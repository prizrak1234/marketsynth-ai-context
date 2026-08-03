/**
 * Execution package routing + builder + dry-run self-check.
 * Run: npx --yes tsx src/lib/execution-package/build-package.selfcheck.ts
 */

import { buildScenarioWorkspace, DEMO_PROJECT_IDS } from "@/lib/investigation/mock-data";
import { buildBusinessVerdict } from "@/lib/verdict/build-verdict";
import { buildMarketingStrategy } from "@/lib/strategy/build-strategy";
import { buildImplementationPlan } from "@/lib/implementation-plan/build-plan";
import { buildExecutionPackage, refreshPackageDerived } from "@/lib/execution-package/build-package";
import { runDryRun, withDryRunReport } from "@/lib/execution-package/dry-run";
import { evaluatePackageReadiness } from "@/lib/execution-package/readiness";
import { resolvePackageAccess } from "@/lib/execution-package/routing";
import { executionPackageStorageKey } from "@/lib/execution-package/storage";
import { runPreflightChecks } from "@/lib/execution-package/preflight";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

function pair(scenario: "ready_for_review" | "conditionally_ready" | "not_ready" | "no_go") {
  const id =
    scenario === "ready_for_review"
      ? DEMO_PROJECT_IDS.ready_for_review
      : scenario === "conditionally_ready"
        ? DEMO_PROJECT_IDS.conditionally_ready
        : scenario === "not_ready"
          ? DEMO_PROJECT_IDS.not_ready
          : DEMO_PROJECT_IDS.no_go;
  const ws = buildScenarioWorkspace(scenario, id);
  const verdict = buildBusinessVerdict(ws, { version: 1, supersedesVerdictId: null });
  return { id, ws, verdict };
}

const go = pair("ready_for_review");
const cg = pair("conditionally_ready");
const ng = pair("no_go");
const idata = pair("not_ready");

const goStrat = buildMarketingStrategy(go.verdict, go.ws, {
  version: 1,
  supersedesStrategyId: null,
});
const cgStrat = buildMarketingStrategy(cg.verdict, cg.ws, {
  version: 1,
  supersedesStrategyId: null,
});
const goPlan = buildImplementationPlan(go.verdict, goStrat, {
  version: 1,
  supersedesPlanId: null,
});
const cgPlan = buildImplementationPlan(cg.verdict, cgStrat, {
  version: 1,
  supersedesPlanId: null,
});

{
  const a = resolvePackageAccess(go.verdict, goStrat, goPlan);
  assert(a.allow === true && a.mode === "go", "GO allows package");
}
{
  const a = resolvePackageAccess(cg.verdict, cgStrat, cgPlan);
  assert(a.allow === true && a.mode === "conditional_go", "CG allows package");
}
{
  const a = resolvePackageAccess(ng.verdict, goStrat, goPlan);
  assert(a.allow === false, "NO_GO blocks");
  if (a.allow === false) assert(a.redirect === "pivot", "NO_GO → pivot");
}
{
  const a = resolvePackageAccess(idata.verdict, goStrat, goPlan);
  assert(a.allow === false, "INSUFFICIENT blocks");
  if (a.allow === false) assert(a.redirect === "investigation", "→ investigation");
}
{
  const a = resolvePackageAccess(go.verdict, null, goPlan);
  assert(a.allow === false, "missing strategy blocks");
  if (a.allow === false) assert(a.redirect === "strategy", "→ strategy");
}
{
  const a = resolvePackageAccess(go.verdict, goStrat, null);
  assert(a.allow === false, "missing plan blocks");
  if (a.allow === false) assert(a.redirect === "implementation", "→ implementation");
}

const goPkg = buildExecutionPackage(go.verdict, goStrat, goPlan, {
  version: 1,
  supersedesPackageId: null,
});
assert(goPkg.executionItems.length > 0, "GO has items");
assert(
  goPkg.executionItems.every(
    (i) =>
      i.actionClass !== "publication" ||
      i.status === "excluded" ||
      i.status === "blocked",
  ),
  "publication not executable",
);
assert(
  goPkg.readiness.status === "ready_for_approval" ||
    goPkg.readiness.status === "approved_for_dry_run",
  `GO readiness unexpected: ${goPkg.readiness.status}`,
);

const cgPkg = buildExecutionPackage(cg.verdict, cgStrat, cgPlan, {
  version: 1,
  supersedesPackageId: null,
});
assert(cgPkg.blockers.some((b) => b.origin.includes("condition")), "CG blockers");
assert(
  cgPkg.readiness.status === "blocked" || cgPkg.readiness.status === "conditionally_ready",
  `CG readiness: ${cgPkg.readiness.status}`,
);
assert(
  cgPkg.executionItems.find((i) => i.id === "ex_campaign_plan")?.status === "blocked",
  "CG acquisition blocked",
);

let threw = false;
try {
  buildExecutionPackage(ng.verdict, goStrat, goPlan, { version: 1, supersedesPackageId: null });
} catch {
  threw = true;
}
assert(threw, "NO_GO must not build package");

{
  const failed = goPkg.preflightChecks.map((c) =>
    c.id === "pf_verdict" ? { ...c, result: "failed" as const, blocking: true } : c,
  );
  const r = evaluatePackageReadiness({
    verdictType: "GO",
    preflight: failed,
    blockers: [],
    budgetMode: "range",
    budgetState: "pending",
    approvals: goPkg.approvalMatrix,
    providers: goPkg.providerRequirements,
    verificationGaps: [],
    rollbackGaps: [],
    dryRun: null,
    packageStatus: "draft",
  });
  assert(r.status === "blocked", "failed critical preflight blocks");
}

{
  const rejected = goPkg.approvalMatrix.map((a) =>
    a.gate === "execution_approval" ? { ...a, status: "rejected" as const } : a,
  );
  const report = runDryRun({
    packageVersion: 1,
    items: goPkg.executionItems,
    preflight: goPkg.preflightChecks,
    approvals: rejected,
    providers: goPkg.providerRequirements,
    verification: goPkg.verificationPlan,
    rollback: goPkg.rollbackPlan,
  });
  assert(
    report.result === "blocked" || report.approvalGaps.some((g) => g.includes("rejected")),
    "missing/rejected approval affects dry-run",
  );
  assert(report.externalActionsPerformed === false, "dry run never external");
}

{
  const providerBlocked = goPkg.executionItems.filter(
    (i) => i.actionClass === "provider_configuration",
  );
  assert(
    providerBlocked.every((i) => i.status === "excluded" || i.status === "blocked"),
    "missing provider config blocks external actions",
  );
}

{
  const unverified = goPkg.verificationPlan.filter((v) => v.verificationMethod === "unavailable");
  assert(
    unverified.every((v) => v.acknowledgmentRequired),
    "unavailable verification acknowledged or excluded",
  );
}

{
  const highRiskItems = goPkg.executionItems.map((i) =>
    i.id === "ex_validation"
      ? { ...i, riskLevel: "critical" as const, status: "ready" as const }
      : i,
  );
  const highRiskRollback = goPkg.rollbackPlan.map((r) =>
    r.executionItemId === "ex_validation" ? { ...r, state: "unavailable" as const } : r,
  );
  const checks = runPreflightChecks({
    verdict: go.verdict,
    strategy: goStrat,
    plan: goPlan,
    scope: goPkg.executionScope,
    items: highRiskItems,
    providers: goPkg.providerRequirements,
    approvals: goPkg.approvalMatrix,
    budget: goPkg.budgetAuthorization,
    verification: goPkg.verificationPlan,
    rollback: highRiskRollback,
  });
  assert(
    checks.some((c) => c.id === "pf_rollback" && c.result === "failed"),
    "high-risk without rollback fails preflight",
  );
}

{
  const unknownBudgetPlan = {
    ...goPlan,
    budgetPlan: goPlan.budgetPlan.map((b) => ({
      ...b,
      mode: "unknown" as const,
      minimum: "unknown",
      recommendedRange: "unknown",
      upperBoundary: "unknown",
    })),
    overview: { ...goPlan.overview, estimatedBudgetRange: "unknown" },
  };
  const pkg = buildExecutionPackage(go.verdict, goStrat, unknownBudgetPlan, {
    version: 1,
    supersedesPackageId: null,
  });
  assert(pkg.budgetAuthorization.mode === "unknown", "unknown budget mode");
  assert(
    pkg.budgetAuthorization.approvalState === "blocked",
    "unknown budget blocks authorization",
  );
}

{
  const report = runDryRun({
    packageVersion: goPkg.version,
    items: goPkg.executionItems,
    preflight: goPkg.preflightChecks,
    approvals: goPkg.approvalMatrix,
    providers: goPkg.providerRequirements,
    verification: goPkg.verificationPlan,
    rollback: goPkg.rollbackPlan,
  });
  assert(report.externalActionsPerformed === false, "no external action");
  const approved = refreshPackageDerived(
    withDryRunReport({ ...goPkg, status: "approved" }, report),
  );
  assert(
    approved.readiness.status === "approved_for_dry_run" ||
      approved.readiness.status === "ready_for_approval",
    `GO dry-run readiness: ${approved.readiness.status}`,
  );
}

{
  const v2 = buildExecutionPackage(go.verdict, goStrat, goPlan, {
    version: 2,
    supersedesPackageId: goPkg.id,
  });
  assert(v2.version === 2, "version increment");
  assert(v2.supersedesPackageId === goPkg.id, "supersedes");
}

assert(
  executionPackageStorageKey("a") !== executionPackageStorageKey("b"),
  "storage isolation",
);

console.log("execution-package selfcheck OK");
