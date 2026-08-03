import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buildStagesFromBackendProgress } from "@/lib/home/agency-analysis-flow";

describe("buildStagesFromBackendProgress", () => {
  it("maps completed pipeline stages to agency stages", () => {
    const stages = buildStagesFromBackendProgress({
      state: "running",
      current_stage: "extracting_evidence",
      completed_stages: [
        "normalizing_input",
        "decomposing_queries",
        "searching_direct",
        "validating_sources",
      ],
      progress_percent: 40,
    });
    assert.ok(stages.some((stage) => stage.status === "done"));
    assert.ok(stages.some((stage) => stage.status === "running"));
  });

  it("shows first stage running for queued state", () => {
    const stages = buildStagesFromBackendProgress({
      state: "queued",
      current_stage: "normalizing_input",
      completed_stages: [],
      progress_percent: 0,
    });
    assert.equal(stages[0]?.status, "running");
    assert.equal(stages[1]?.status, "pending");
  });

  it("marks all stages done on succeeded", () => {
    const stages = buildStagesFromBackendProgress({
      state: "succeeded",
      current_stage: "completed",
      completed_stages: ["completed"],
      progress_percent: 100,
    });
    assert.ok(stages.every((stage) => stage.status === "done"));
  });
});
