import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { deriveBivWorkspaceViewModel } from "./biv-workspace-view-model";

const baseFailure = {
  title: "Исследование не удалось завершить",
  message: "Попробуйте повторить.",
  actionHint: "Повторить",
  internalCode: "research_failed",
};

describe("deriveBivWorkspaceViewModel", () => {
  it("shows failure panel when research failed during analyzing (no blank screen)", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: null,
      researchFailure: baseFailure,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "failed");
    assert.equal(vm.showFailurePanel, true);
    assert.equal(vm.showResearchProgress, true);
    assert.equal(vm.showControlledRecovery, false);
  });

  it("shows controlled recovery for unknown analyzing state without failure or progress", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: null,
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.showControlledRecovery, true);
    assert.equal(vm.showResearchProgress, false);
    assert.equal(vm.showCompletedReport, false);
  });

  it("blocks duplicate actions while failure panel visible", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: "run-1",
      researchFailure: baseFailure,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.duplicateActionsBlocked, true);
  });

  it("terminal partial research is not running, failure, or completed", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        run_id: "run-partial",
        result_kind: "partial_research",
        research_terminal_state: "succeeded_insufficient",
      } as never,
      activeRunId: "run-partial",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "partial_research");
    assert.equal(vm.showResearchProgress, false);
    assert.equal(vm.showFailurePanel, false);
    assert.equal(vm.showCompletedReport, false);
    assert.equal(vm.showControlledRecovery, false);
    assert.equal(vm.canRerun, true);
    assert.equal(vm.duplicateActionsBlocked, false);
    assert.equal(vm.showPartialResearchPanel, true);
  });

  it("stale ANALYZING with terminal partial still shows partial panel", () => {
    const partial = {
      run_id: "run-partial",
      result_kind: "partial_research",
      research_terminal_state: "succeeded_insufficient",
    } as never;

    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: partial,
      activeRunId: "run-partial",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "partial_research");
    assert.equal(vm.showResearchProgress, false);
    assert.equal(vm.showPartialResearchPanel, true);
  });

  it("rerun starting hides partial panel and blocks duplicate rerun", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: true,
      rerunStarting: true,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: null,
      researchFailure: null,
      runInFlight: true,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "research_starting");
    assert.equal(vm.showPartialResearchPanel, false);
  });

  it("technical failure with null output stays on failure UI", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: "run-failed",
      researchFailure: baseFailure,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "failed");
    assert.equal(vm.showFailurePanel, true);
    assert.equal(vm.showPartialResearchPanel, false);
  });

  it("running research without partial stays running UI", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: null,
      activeRunId: "run-active",
      researchFailure: null,
      runInFlight: true,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "research_running");
    assert.equal(vm.showPartialResearchPanel, false);
    assert.equal(vm.showResearchProgress, true);
  });

  it("successful verdict flow unchanged", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "verdict",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        run_id: "run-ok",
        research_terminal_state: "succeeded_complete",
        customer_report: { headline: "OK" },
      } as never,
      activeRunId: "run-ok",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "completed");
    assert.equal(vm.showCompletedReport, true);
    assert.equal(vm.showPartialResearchPanel, false);
    assert.equal(vm.canRefine, true);
  });

  it("partial research disables refine and launch-oriented refine", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "analyzing",
      intakeView: "form",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        result_kind: "partial_research",
        research_terminal_state: "succeeded_insufficient",
      } as never,
      activeRunId: "run-partial",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.canRefine, false);
    assert.equal(vm.canDownload, false);
  });

  it("shows completed report on verdict with customer_report", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "verdict",
      intakeView: "confirmed",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        run_id: "run-1",
        customer_report: { title: "Report", sections: [] },
      } as never,
      activeRunId: "run-1",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });

    assert.equal(vm.state, "completed");
    assert.equal(vm.showCompletedReport, true);
    assert.equal(vm.showControlledRecovery, false);
  });
});
