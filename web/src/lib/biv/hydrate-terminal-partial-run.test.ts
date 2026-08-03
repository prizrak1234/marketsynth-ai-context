import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { BusinessIdeaValidationRunResponse } from "@/lib/api/types/business-idea-validation";

import { tryHydrateTerminalPartialRun } from "./hydrate-terminal-partial-run";
import {
  clearTerminalPartialResearch,
  loadTerminalPartialResearch,
  persistTerminalPartialResearch,
} from "./terminal-partial-research";

describe("terminal-partial-research storage", () => {
  it("round-trips terminal partial hint", () => {
    if (typeof window === "undefined" || !window.localStorage) {
      return;
    }
    clearTerminalPartialResearch();
    persistTerminalPartialResearch({
      projectId: "proj-1",
      userRequestId: "ur-1",
      runId: "run-1",
      savedAt: Date.now(),
    });
    const loaded = loadTerminalPartialResearch();
    assert.equal(loaded?.projectId, "proj-1");
    assert.equal(loaded?.userRequestId, "ur-1");
    assert.equal(loaded?.runId, "run-1");
    clearTerminalPartialResearch();
    assert.equal(loadTerminalPartialResearch(), null);
  });
});

describe("tryHydrateTerminalPartialRun", () => {
  it("returns partial run when backend contract matches", async () => {
    const partialRun = {
      run_id: "run-partial",
      project_id: "proj-1",
      status: "failed",
      output: {
        result_kind: "partial_research",
        research_terminal_state: "succeeded_insufficient",
      },
    } as BusinessIdeaValidationRunResponse;

    const result = await tryHydrateTerminalPartialRun({
      projectId: "proj-1",
      userRequestId: "ur-1",
      runId: "run-partial",
      fetchLatest: async () => partialRun,
    });

    assert.equal(result?.run_id, "run-partial");
  });

  it("rejects technical failure with null partial output", async () => {
    const result = await tryHydrateTerminalPartialRun({
      projectId: "proj-1",
      userRequestId: "ur-1",
      fetchLatest: async () =>
        ({
          run_id: "run-failed",
          project_id: "proj-1",
          status: "failed",
          output: null,
        }) as BusinessIdeaValidationRunResponse,
    });
    assert.equal(result, null);
  });

  it("rejects project mismatch", async () => {
    const result = await tryHydrateTerminalPartialRun({
      projectId: "proj-1",
      userRequestId: "ur-1",
      fetchLatest: async () =>
        ({
          run_id: "run-partial",
          project_id: "proj-other",
          status: "failed",
          output: {
            result_kind: "partial_research",
            research_terminal_state: "succeeded_insufficient",
          },
        }) as BusinessIdeaValidationRunResponse,
    });
    assert.equal(result, null);
  });
});
