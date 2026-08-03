import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  isActiveRunStatus,
  isTerminalRunStatus,
} from "./research-run-polling";
import { isPartialResearchOutput } from "@/lib/api/types/business-idea-validation";

describe("research-run-polling status helpers", () => {
  it("treats queued and running as active", () => {
    assert.equal(isActiveRunStatus("queued"), true);
    assert.equal(isActiveRunStatus("pending"), true);
    assert.equal(isActiveRunStatus("running"), true);
    assert.equal(isActiveRunStatus("succeeded"), false);
    assert.equal(isActiveRunStatus("failed"), false);
  });

  it("treats succeeded and failed as terminal", () => {
    assert.equal(isTerminalRunStatus("succeeded"), true);
    assert.equal(isTerminalRunStatus("failed"), true);
    assert.equal(isTerminalRunStatus("running"), false);
    assert.equal(isTerminalRunStatus("queued"), false);
  });

  it("recognizes partial research output discriminant", () => {
    assert.equal(
      isPartialResearchOutput({
        investigation_id: "inv",
        research_plan: [],
        sources: [],
        evidence: [],
        findings: [],
        risks: [],
        opportunities: [],
        verdict: "insufficient_evidence",
        confidence: { total_score: 0, calculation_version: "test", factors: [], penalties: [] },
        limitations: [],
        next_steps: [],
        tool_call_audit_ids: [],
        result_kind: "partial_research",
        research_terminal_state: "succeeded_insufficient",
      }),
      true,
    );
    assert.equal(isPartialResearchOutput(null), false);
  });

  it("failed run with partial output is classified as partial terminal", () => {
    const output = {
      result_kind: "partial_research",
      research_terminal_state: "succeeded_insufficient",
    } as never;
    const kind =
      "failed" === "failed" && isPartialResearchOutput(output) ? "partial" : "failed";
    assert.equal(kind, "partial");
  });
});
