/**
 * Strategy routing + builder self-check.
 * Run: npx --yes tsx src/lib/strategy/build-strategy.selfcheck.ts
 */

import { buildScenarioWorkspace, DEMO_PROJECT_IDS } from "@/lib/investigation/mock-data";
import { buildBusinessVerdict } from "@/lib/verdict/build-verdict";
import { buildMarketingStrategy } from "@/lib/strategy/build-strategy";
import { evaluateExecutionReadiness } from "@/lib/strategy/execution-readiness";
import { resolveStrategyAccess } from "@/lib/strategy/routing";
import { strategyStorageKey } from "@/lib/strategy/storage";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

function verdictFor(scenario: "ready_for_review" | "conditionally_ready" | "not_ready" | "no_go") {
  const id =
    scenario === "ready_for_review"
      ? DEMO_PROJECT_IDS.ready_for_review
      : scenario === "conditionally_ready"
        ? DEMO_PROJECT_IDS.conditionally_ready
        : scenario === "not_ready"
          ? DEMO_PROJECT_IDS.not_ready
          : DEMO_PROJECT_IDS.no_go;
  const ws = buildScenarioWorkspace(scenario, id);
  return { ws, verdict: buildBusinessVerdict(ws, { version: 1, supersedesVerdictId: null }) };
}

const go = verdictFor("ready_for_review");
const cg = verdictFor("conditionally_ready");
const ng = verdictFor("no_go");
const idata = verdictFor("not_ready");

assert(resolveStrategyAccess(go.verdict).allow === true, "GO allows strategy");
{
  const a = resolveStrategyAccess(go.verdict);
  assert(a.allow === true && a.mode === "go", "GO mode");
}

{
  const a = resolveStrategyAccess(cg.verdict);
  assert(a.allow === true && a.mode === "conditional_go", "CONDITIONAL allows strategy");
}

{
  const a = resolveStrategyAccess(ng.verdict);
  assert(a.allow === false, "NO_GO denies strategy");
  if (a.allow === false) {
    assert(a.redirect === "pivot", "NO_GO → pivot");
  }
}

{
  const a = resolveStrategyAccess(idata.verdict);
  assert(a.allow === false, "INSUFFICIENT denies strategy");
  if (a.allow === false) {
    assert(a.redirect === "investigation", "INSUFFICIENT → investigation");
  }
}

const goStrat = buildMarketingStrategy(go.verdict, go.ws, {
  version: 1,
  supersedesStrategyId: null,
});
assert(goStrat.verdictType === "GO", "strategy tied to GO");
assert(
  goStrat.executionReadiness.status === "ready_for_planning" ||
    goStrat.executionReadiness.status === "conditionally_ready",
  `GO readiness unexpected: ${goStrat.executionReadiness.status}`,
);

const cgStrat = buildMarketingStrategy(cg.verdict, cg.ws, {
  version: 1,
  supersedesStrategyId: null,
});
assert(cgStrat.conditions.some((c) => c.blocksExecution), "CG has blocking conditions");
assert(
  cgStrat.executionReadiness.status === "blocked" ||
    cgStrat.executionReadiness.status === "conditionally_ready",
  `CG readiness: ${cgStrat.executionReadiness.status}`,
);
assert(
  cgStrat.conditions.every((c) => c.blocksExecution) ||
    evaluateExecutionReadiness(cgStrat, cg.verdict).unresolvedConditions.length > 0,
  "mandatory conditions visible",
);

let threw = false;
try {
  buildMarketingStrategy(ng.verdict, ng.ws, { version: 1, supersedesStrategyId: null });
} catch {
  threw = true;
}
assert(threw, "NO_GO must not build strategy");

threw = false;
try {
  buildMarketingStrategy(idata.verdict, idata.ws, { version: 1, supersedesStrategyId: null });
} catch {
  threw = true;
}
assert(threw, "INSUFFICIENT must not build strategy");

// No fake exact prices when unknown
assert(
  cgStrat.offers.some((o) => o.priceMode === "unknown" || o.priceMode === "hypothesis"),
  "conditional offers avoid fake exact prices",
);
assert(
  !cgStrat.budget.some((b) => /^\d+(\.\d+)?$/.test(b.amountOrRange.trim())),
  "budget lines are ranges/unknown, not fake exact singles",
);

const v2 = buildMarketingStrategy(go.verdict, go.ws, {
  version: 2,
  supersedesStrategyId: goStrat.id,
});
assert(v2.version === 2 && v2.supersedesStrategyId === goStrat.id, "version increment");

assert(
  strategyStorageKey("a") !== strategyStorageKey("b"),
  "storage isolation",
);
assert(
  strategyStorageKey("a") === "marketsynth.product_alpha.strategy.v1.a",
  "versioned key",
);

// Strategy never upgrades verdict
assert(goStrat.verdictType === go.verdict.type, "no verdict contradiction");
assert(cgStrat.verdictType === cg.verdict.type, "no verdict contradiction cg");

console.log("build-strategy.selfcheck: OK");
