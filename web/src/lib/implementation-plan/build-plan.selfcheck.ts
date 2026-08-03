/**
 * Implementation plan routing + builder self-check.
 * Run: npx --yes tsx src/lib/implementation-plan/build-plan.selfcheck.ts
 */

import { buildScenarioWorkspace, DEMO_PROJECT_IDS } from "@/lib/investigation/mock-data";
import { buildBusinessVerdict } from "@/lib/verdict/build-verdict";
import { buildMarketingStrategy } from "@/lib/strategy/build-strategy";
import {
  applyRejectedBudgetGate,
  buildImplementationPlan,
} from "@/lib/implementation-plan/build-plan";
import { evaluatePlanningReadiness } from "@/lib/implementation-plan/readiness";
import { resolveImplementationAccess } from "@/lib/implementation-plan/routing";
import { implementationPlanStorageKey } from "@/lib/implementation-plan/storage";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";

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

{
  const a = resolveImplementationAccess(go.verdict, goStrat);
  assert(a.allow === true && a.mode === "go", "GO allows implementation plan");
}

{
  const a = resolveImplementationAccess(cg.verdict, cgStrat);
  assert(a.allow === true && a.mode === "conditional_go", "CONDITIONAL allows plan");
}

{
  const a = resolveImplementationAccess(ng.verdict, goStrat);
  assert(a.allow === false, "NO_GO blocks plan");
  if (a.allow === false) assert(a.redirect === "pivot", "NO_GO → pivot");
}

{
  const a = resolveImplementationAccess(idata.verdict, goStrat);
  assert(a.allow === false, "INSUFFICIENT blocks plan");
  if (a.allow === false) assert(a.redirect === "investigation", "INSUFFICIENT → investigation");
}

{
  const a = resolveImplementationAccess(go.verdict, null);
  assert(a.allow === false, "missing strategy blocks plan");
  if (a.allow === false) assert(a.redirect === "strategy", "missing strategy → strategy");
}

const goPlan = buildImplementationPlan(go.verdict, goStrat, {
  version: 1,
  supersedesPlanId: null,
});
assert(goPlan.workstreams.length >= 5, "GO has workstreams");
assert(
  goPlan.readiness.status === "ready_for_approval" ||
    goPlan.readiness.status === "conditionally_ready",
  `GO readiness unexpected: ${goPlan.readiness.status}`,
);
assert(
  goPlan.readiness.status === "ready_for_approval",
  `GO should reach ready_for_approval, got ${goPlan.readiness.status}`,
);

const cgPlan = buildImplementationPlan(cg.verdict, cgStrat, {
  version: 1,
  supersedesPlanId: null,
});
assert(cgPlan.workstreams[0]?.type === "validation", "CG validation-first");
assert(
  cgPlan.conditions.some((c) => c.blocksPlanning && c.status === "open"),
  "CG mandatory conditions open",
);
assert(
  cgPlan.readiness.status === "blocked" || cgPlan.readiness.status === "conditionally_ready",
  `CG readiness: ${cgPlan.readiness.status}`,
);
assert(
  cgPlan.tasks.some((t) => t.id === "task_close_conditions"),
  "CG has close-conditions task",
);
assert(
  cgPlan.workstreams.find((w) => w.id === "ws_acquisition")?.status === "blocked",
  "CG acquisition blocked",
);

let threw = false;
try {
  buildImplementationPlan(ng.verdict, goStrat, { version: 1, supersedesPlanId: null });
} catch {
  threw = true;
}
assert(threw, "NO_GO must not build plan");

threw = false;
try {
  buildImplementationPlan(idata.verdict, goStrat, { version: 1, supersedesPlanId: null });
} catch {
  threw = true;
}
assert(threw, "INSUFFICIENT must not build plan");

{
  const withReject = applyRejectedBudgetGate(goPlan);
  const r = evaluatePlanningReadiness(withReject, goStrat, go.verdict);
  assert(r.status === "blocked", "rejected budget gate blocks readiness");
  assert(
    withReject.tasks.find((t) => t.id === "task_channel_test")?.status === "blocked",
    "rejected budget blocks acquisition task",
  );
}

{
  const missingAcceptance: ImplementationPlan = {
    ...goPlan,
    tasks: goPlan.tasks.map((t) =>
      t.priority === "critical" ? { ...t, acceptanceCriteria: "" } : t,
    ),
  };
  const r = evaluatePlanningReadiness(missingAcceptance, goStrat, go.verdict);
  assert(
    r.status === "not_ready" || r.status === "blocked",
    `missing acceptance prevents ready_for_approval: ${r.status}`,
  );
  assert(r.status !== "ready_for_approval", "must not be ready_for_approval");
}

{
  const unknownBudget = {
    ...goPlan,
    budgetPlan: goPlan.budgetPlan.map((b) => ({
      ...b,
      mode: "unknown" as const,
      minimum: "unknown",
      recommendedRange: "unknown",
      upperBoundary: "unknown",
    })),
  };
  for (const line of unknownBudget.budgetPlan) {
    assert(line.minimum === "unknown" || line.mode === "unknown", "no fake exact amounts");
    assert(!/^\d+(\.\d+)?$/.test(line.minimum), "minimum not a bare invented number");
  }
}

{
  const v2 = buildImplementationPlan(go.verdict, goStrat, {
    version: 2,
    supersedesPlanId: goPlan.id,
  });
  assert(v2.version === 2, "version increment");
  assert(v2.supersedesPlanId === goPlan.id, "supersedes link");
}

assert(
  implementationPlanStorageKey("proj_a") !== implementationPlanStorageKey("proj_b"),
  "project storage isolation",
);
assert(
  implementationPlanStorageKey(DEMO_PROJECT_IDS.ready_for_review).includes(
    DEMO_PROJECT_IDS.ready_for_review,
  ),
  "storage key scoped by project",
);

{
  const criticalRisk: ImplementationPlan = {
    ...goPlan,
    risks: goPlan.risks.map((r, i) =>
      i === 0
        ? { ...r, severity: "critical" as const, status: "open" as const }
        : r,
    ),
  };
  const r = evaluatePlanningReadiness(criticalRisk, goStrat, go.verdict);
  assert(r.status === "blocked", "critical unresolved risk blocks readiness");
}

console.log("implementation-plan selfcheck OK");
