/**
 * Business Verdict rule self-check (tsx, no new framework).
 * Run: npx --yes tsx src/lib/verdict/build-verdict.selfcheck.ts
 */

import { buildScenarioWorkspace, DEMO_PROJECT_IDS } from "@/lib/investigation/mock-data";
import { evaluateVerdictReadiness } from "@/lib/investigation/verdict-readiness";
import {
  buildBusinessVerdict,
  classifyVerdictType,
} from "@/lib/verdict/build-verdict";
import { expectedTypeForScenario } from "@/lib/verdict/mock-verdicts";
import { verdictStorageKey } from "@/lib/verdict/storage";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const go = buildScenarioWorkspace("ready_for_review", DEMO_PROJECT_IDS.ready_for_review);
const conditional = buildScenarioWorkspace(
  "conditionally_ready",
  DEMO_PROJECT_IDS.conditionally_ready,
);
const insufficient = buildScenarioWorkspace("not_ready", DEMO_PROJECT_IDS.not_ready);
const noGo = buildScenarioWorkspace("no_go", DEMO_PROJECT_IDS.no_go);

assert(classifyVerdictType(go) === "GO", `GO expected, got ${classifyVerdictType(go)}`);
assert(
  classifyVerdictType(conditional) === "CONDITIONAL_GO",
  `CONDITIONAL_GO expected, got ${classifyVerdictType(conditional)}`,
);
assert(
  classifyVerdictType(insufficient) === "INSUFFICIENT_DATA",
  `INSUFFICIENT_DATA expected, got ${classifyVerdictType(insufficient)}`,
);
assert(classifyVerdictType(noGo) === "NO_GO", `NO_GO expected, got ${classifyVerdictType(noGo)}`);

assert(expectedTypeForScenario("go") === "GO", "scenario map go");
assert(expectedTypeForScenario("conditional_go") === "CONDITIONAL_GO", "scenario map cg");
assert(expectedTypeForScenario("no_go") === "NO_GO", "scenario map ng");
assert(
  expectedTypeForScenario("insufficient_data") === "INSUFFICIENT_DATA",
  "scenario map id",
);

// Readiness ≠ verdict: ready_for_review does not alone mean GO without economics etc.
const readinessOnly = evaluateVerdictReadiness(conditional);
assert(readinessOnly.status === "conditionally_ready", "readiness conditional");
assert(classifyVerdictType(conditional) !== "GO", "readiness must not auto-GO");

// Critical missing → insufficient
assert(
  insufficient.missingData.some((m) => m.severity === "critical" && m.resolution === "open"),
  "insufficient has critical missing",
);

// Blocking contradiction on no-go
assert(
  noGo.contradictions.some((c) => c.blocksVerdict && !c.resolved),
  "no_go has blocking contradiction",
);
assert(
  noGo.risks.some((r) => r.severity === "critical"),
  "no_go has verdict-changing risk severity",
);

const v1 = buildBusinessVerdict(go, { version: 1, supersedesVerdictId: null });
const v2 = buildBusinessVerdict(go, {
  version: 2,
  supersedesVerdictId: v1.id,
});
assert(v2.version === 2, "version increment");
assert(v2.supersedesVerdictId === v1.id, "supersedes link");
assert(v1.type === "GO" && v2.type === "GO", "GO content");

const cg = buildBusinessVerdict(conditional, { version: 1, supersedesVerdictId: null });
assert(cg.conditions.length > 0, "CONDITIONAL_GO has conditions");
assert(cg.type === "CONDITIONAL_GO", "cg type");

const ng = buildBusinessVerdict(noGo, { version: 1, supersedesVerdictId: null });
assert(ng.type === "NO_GO", "ng type");
assert(
  ng.risks.some((r) => r.sensitivity === "verdict_changing"),
  "verdict-changing risk tagged",
);

const idv = buildBusinessVerdict(insufficient, { version: 1, supersedesVerdictId: null });
assert(idv.type === "INSUFFICIENT_DATA", "id type");
assert(idv.nextStep.handoffHref === "investigation", "insufficient returns to investigation");

assert(
  verdictStorageKey("p1") !== verdictStorageKey("p2"),
  "storage isolation by project",
);
assert(
  verdictStorageKey("p1") === "marketsynth.product_alpha.verdict.v1.p1",
  "versioned key",
);

console.log("build-verdict.selfcheck: OK");
