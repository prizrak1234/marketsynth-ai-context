import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  pickAnalysisProjectSnapshot,
  type ProjectContextSnapshot,
} from "./pick-analysis-project";

function snapshot(
  projectId: string,
  overrides: Partial<ProjectContextSnapshot> = {},
): ProjectContextSnapshot {
  return {
    projectId,
    projectUpdatedAt: "2026-07-28T00:00:00.000Z",
    context: null,
    hasCompletedAnalysis: false,
    completedRunId: null,
    ...overrides,
  };
}

describe("pickAnalysisProjectSnapshot", () => {
  it("prefers explicit project id over completed legacy project", () => {
    const picked = pickAnalysisProjectSnapshot({
      preferredProjectIds: ["project-b"],
      snapshots: [
        snapshot("project-a", {
          projectUpdatedAt: "2026-07-28T02:00:00.000Z",
          hasCompletedAnalysis: true,
          context: {
            context_id: "ctx-a",
            state: "completed",
          } as ProjectContextSnapshot["context"],
        }),
        snapshot("project-b", {
          projectUpdatedAt: "2026-07-28T01:00:00.000Z",
          context: {
            context_id: "ctx-b",
            state: "draft_entered",
          } as ProjectContextSnapshot["context"],
        }),
      ],
    });
    assert.equal(picked?.projectId, "project-b");
  });

  it("prefers analyzing project when no explicit preference", () => {
    const picked = pickAnalysisProjectSnapshot({
      snapshots: [
        snapshot("completed", {
          hasCompletedAnalysis: true,
          context: { state: "completed" } as ProjectContextSnapshot["context"],
        }),
        snapshot("running", {
          context: { state: "analyzing" } as ProjectContextSnapshot["context"],
        }),
      ],
    });
    assert.equal(picked?.projectId, "running");
  });

  it("prefers newest completed project among completed candidates", () => {
    const picked = pickAnalysisProjectSnapshot({
      snapshots: [
        snapshot("older", {
          projectUpdatedAt: "2026-07-27T00:00:00.000Z",
          hasCompletedAnalysis: true,
        }),
        snapshot("newer", {
          projectUpdatedAt: "2026-07-28T00:00:00.000Z",
          hasCompletedAnalysis: true,
        }),
      ],
    });
    assert.equal(picked?.projectId, "newer");
  });

  it("prefers hydrated_unconfirmed over completed legacy project", () => {
    const picked = pickAnalysisProjectSnapshot({
      snapshots: [
        snapshot("completed-legacy", {
          projectUpdatedAt: "2026-07-28T02:00:00.000Z",
          hasCompletedAnalysis: true,
          context: {
            context_id: "ctx-completed",
            state: "completed",
            confirmed_by_user: true,
          } as ProjectContextSnapshot["context"],
        }),
        snapshot("needs-recovery", {
          projectUpdatedAt: "2026-07-28T01:00:00.000Z",
          context: {
            context_id: "ctx-hydrated",
            state: "hydrated_unconfirmed",
            confirmed_by_user: false,
          } as ProjectContextSnapshot["context"],
        }),
      ],
    });
    assert.equal(picked?.projectId, "needs-recovery");
  });
});
