/**
 * Investigation readiness / evidence self-check (tsx, no new test framework).
 * Run from web/: npx --yes tsx src/lib/investigation/verdict-readiness.selfcheck.ts
 */

import { filterEvidence, DEFAULT_EVIDENCE_FILTERS } from "./evidence";
import { buildScenarioWorkspace, DEMO_PROJECT_IDS } from "./mock-data";
import { investigationStorageKey } from "./storage";
import {
  canPrepareVerdict,
  evaluateVerdictReadiness,
} from "./verdict-readiness";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const a = buildScenarioWorkspace(
  "conditionally_ready",
  DEMO_PROJECT_IDS.conditionally_ready,
);
const b = buildScenarioWorkspace("not_ready", DEMO_PROJECT_IDS.not_ready);
const c = buildScenarioWorkspace(
  "ready_for_review",
  DEMO_PROJECT_IDS.ready_for_review,
);

assert(a.verdictReadiness?.status === "conditionally_ready", "A must be conditionally_ready");
assert(b.verdictReadiness?.status === "not_ready", "B must be not_ready");
assert(c.verdictReadiness?.status === "ready_for_review", "C must be ready_for_review");

assert(!canPrepareVerdict(a.verdictReadiness!, false), "A requires acknowledgment");
assert(canPrepareVerdict(a.verdictReadiness!, true), "A with ack can prepare");
assert(!canPrepareVerdict(b.verdictReadiness!, true), "B cannot prepare even with ack");
assert(canPrepareVerdict(c.verdictReadiness!, false), "C can prepare");

assert(
  b.missingData.some((m) => m.severity === "critical" && m.resolution === "open"),
  "B has critical open missing data",
);
assert(
  b.contradictions.some((cx) => cx.blocksVerdict && !cx.resolved),
  "B has blocking contradiction",
);

const covered = evaluateVerdictReadiness(c).completedAreas;
assert(covered.includes("market"), "C covers market");
assert(covered.includes("audience"), "C covers audience");
assert(covered.includes("economics"), "C covers economics");
assert(covered.includes("risks"), "C covers risks");

const filtered = filterEvidence(a.evidence, a.sources, {
  ...DEFAULT_EVIDENCE_FILTERS,
  state: "missing",
});
assert(filtered.every((e) => e.state === "missing"), "filter by state works");

assert(
  a.verdictReadiness?.notABusinessVerdict === true,
  "must not be confused with GO/NO_GO",
);

const keyA = investigationStorageKey("proj_1");
const keyB = investigationStorageKey("proj_2");
assert(keyA !== keyB, "storage keys isolated by projectId");
assert(
  keyA === "marketsynth.product_alpha.investigation.v1.proj_1",
  "storage key versioned",
);

console.log("verdict-readiness.selfcheck: OK");
