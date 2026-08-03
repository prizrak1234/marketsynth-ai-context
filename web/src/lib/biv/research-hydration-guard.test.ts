import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  mapPollingAuthErrorCode,
  resolveContextApplyAction,
  shouldBlockProjectHydrate,
  shouldShowIntakeForm,
} from "./research-hydration-guard";

describe("resolveContextApplyAction", () => {
  it("returns analyzing_resume for analyzing context on cold load", () => {
    const action = resolveContextApplyAction({
      contextState: "analyzing",
      hasCompleted: true,
      confirmedByUser: true,
      runInFlight: false,
      currentPhase: "intake",
    });
    assert.equal(action.kind, "analyzing_resume");
  });

  it("returns analyzing_resume for analysis_requested context", () => {
    const action = resolveContextApplyAction({
      contextState: "analysis_requested",
      hasCompleted: false,
      confirmedByUser: true,
      runInFlight: false,
      currentPhase: "intake",
    });
    assert.equal(action.kind, "analyzing_resume");
  });

  it("blocks stale hydrate while run in flight", () => {
    const action = resolveContextApplyAction({
      contextState: "completed",
      hasCompleted: true,
      confirmedByUser: true,
      runInFlight: true,
      currentPhase: "analyzing",
    });
    assert.equal(action.kind, "noop_active_research");
  });

  it("blocks parallel stale hydrate from intake to form during analyzing phase", () => {
    const action = resolveContextApplyAction({
      contextState: "editing",
      hasCompleted: false,
      confirmedByUser: false,
      runInFlight: false,
      currentPhase: "analyzing",
    });
    assert.equal(action.kind, "noop_active_research");
  });

  it("keeps analyzing phase on noop for analyzing context during active run", () => {
    const action = resolveContextApplyAction({
      contextState: "analyzing",
      hasCompleted: true,
      confirmedByUser: true,
      runInFlight: true,
      currentPhase: "analyzing",
    });
    assert.equal(action.kind, "noop_active_research");
  });

  it("routes hydrated_unconfirmed to recovery on cold load", () => {
    const action = resolveContextApplyAction({
      contextState: "hydrated_unconfirmed",
      hasCompleted: true,
      confirmedByUser: false,
      runInFlight: false,
      currentPhase: "intake",
    });
    assert.equal(action.kind, "recovery");
  });
});

describe("shouldBlockProjectHydrate", () => {
  it("blocks hydrate during analyzing", () => {
    assert.equal(
      shouldBlockProjectHydrate({ runInFlight: false, currentPhase: "analyzing" }),
      true,
    );
  });
});

describe("shouldShowIntakeForm", () => {
  it("hides intake form when session expired during research", () => {
    assert.equal(
      shouldShowIntakeForm({
        phase: "intake",
        intakeView: "form",
        sessionExpiredDuringResearch: true,
      }),
      false,
    );
  });
});

describe("mapPollingAuthErrorCode", () => {
  it("maps session_expired", () => {
    assert.equal(mapPollingAuthErrorCode(401, "session_expired"), "session_expired");
  });

  it("maps generic authentication_required", () => {
    assert.equal(
      mapPollingAuthErrorCode(401, "authentication_required"),
      "authentication_required",
    );
  });

  it("returns null for non-auth errors", () => {
    assert.equal(mapPollingAuthErrorCode(500, "internal"), null);
  });
});
