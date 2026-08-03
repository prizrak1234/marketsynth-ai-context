import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { deriveBivWorkspaceViewModel } from "./biv-workspace-view-model";
import {
  buildCustomerReportExportText,
  validateCustomerReportExport,
} from "./customer-report-export";

const baseReport = {
  executive_summary: {
    title: "Предварительная оценка",
    status_line: "Перспективно при подтверждении гипотез.",
    confidence_percent: 62,
    primary_risk: "Не подтверждена готовность платить.",
    primary_advantage: "Спрос на EdTech сохраняется.",
  },
  confirmed_findings: [
    {
      headline: "Спрос на онлайн-обучение сохраняется",
      explanation: "Подтверждено двумя независимыми источниками.",
      sources: [{ title: "EdTech Outlook", url: "https://example.com/edtech", domain: "example.com" }],
      category: "demand",
    },
  ],
  unconfirmed_topics: [],
  dimension_confidence: [],
  overall_confidence_percent: 62,
  coverage: { dimensions_researched: ["demand"], overall_percent: 45 },
  clarification_questions: [],
  structured_verdict: {
    confirmed_summary: [],
    unconfirmed_summary: [],
    risks: [],
    verification_needed: [],
    recommendation: "Рекомендуем пилот с фокусом на монетизацию.",
    confidence_percent: 62,
  },
};

describe("customer-report-export", () => {
  it("builds readable export without empty markdown links", () => {
    const text = buildCustomerReportExportText({
      report: baseReport,
      output: {
        run_id: "run-123",
        verdict: "proceed_with_conditions",
      } as never,
    });
    assert.equal(validateCustomerReportExport(text).includes("empty_markdown_links"), false);
    assert.match(text, /https:\/\/example.com\/edtech/);
    assert.equal(text.includes("[Смотреть рейтинг]()"), false);
  });
});

describe("biv-workspace-view-model", () => {
  it("never shows progress with completed report", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "verdict",
      intakeView: "start",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        customer_report: baseReport,
        verdict: "proceed",
        research_terminal_state: "succeeded_complete",
      } as never,
      activeRunId: "run-1",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });
    assert.equal(vm.showResearchProgress, false);
    assert.equal(vm.showCompletedReport, true);
    assert.equal(vm.canDownload, true);
  });

  it("legacy migration hides duplicate progress", () => {
    const vm = deriveBivWorkspaceViewModel({
      phase: "verdict",
      intakeView: "start",
      loading: false,
      rerunStarting: false,
      sessionExpiredDuringResearch: false,
      validationResult: {
        customer_report: null,
        verdict: "insufficient_evidence",
        research_terminal_state: "succeeded_insufficient",
      } as never,
      activeRunId: "run-1",
      researchFailure: null,
      runInFlight: false,
      confirmedContextConfirmed: true,
    });
    assert.equal(vm.showLegacyMigrationOnly, true);
    assert.equal(vm.duplicateActionsBlocked, true);
  });
});
