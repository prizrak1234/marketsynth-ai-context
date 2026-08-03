import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  intakeDraftMeetsAnalysisContextGate,
  mapIntakeDraftToAnalysisContextFields,
} from "./intake-draft-to-analysis-context";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

function minimalReadyDraft(): ProjectIntakeDraft {
  const draft = createEmptyDraft("review");
  draft.projectBasics = {
    ...draft.projectBasics,
    name: "SaaS отчётность",
    ideaDescription: "SaaS для автоматизации отчётности малого бизнеса с подпиской",
    businessType: "saas",
    projectStage: "validating_demand",
    geography: "Россия, онлайн",
  };
  draft.product = {
    ...draft.product,
    whatIsSold: "Подписка на сервис отчётности",
    primaryProblem: "Ручная отчётность отнимает время",
    valueProposition: "Автоматизация отчётности за 990 ₽/мес",
    priceUnknown: true,
    price: { mode: "unknown" },
    deliveryUnknown: true,
  };
  draft.market = {
    ...draft.market,
    targetMarket: "Малый бизнес",
    geography: "Россия",
    competitorsUnknown: true,
  };
  draft.audience = {
    ...draft.audience,
    segments: [{ id: "s1", label: "Малый бизнес и стартапы", notes: "" }],
  };
  draft.economics = {
    ...draft.economics,
    launchBudget: { mode: "unknown" },
    monthlyMarketingBudget: { mode: "unknown" },
  };
  return draft;
}

describe("mapIntakeDraftToAnalysisContextFields", () => {
  it("maps blocking BIV fields from intake draft", () => {
    const fields = mapIntakeDraftToAnalysisContextFields(minimalReadyDraft());
    assert.match(fields.idea_description ?? "", /SaaS/);
    assert.match(fields.product_or_service ?? "", /Подписка/);
    assert.match(fields.target_customer ?? "", /Малый бизнес/);
    assert.match(fields.geography ?? "", /Россия/);
    assert.ok(fields.analysis_goal);
  });

  it("passes analysis context specificity gate", () => {
    const gate = intakeDraftMeetsAnalysisContextGate(minimalReadyDraft());
    assert.equal(gate.ok, true);
    assert.equal(gate.missing_fields.length, 0);
  });
});

describe("workspaceUrlAfterGoldenPath", () => {
  it("uses canonical backend project id in workspace route", async () => {
    const { workspaceUrlAfterGoldenPath } = await import("./intake-brief-golden-path");
    const projectId = "11111111-2222-4333-8444-555555555555";
    assert.equal(
      workspaceUrlAfterGoldenPath(projectId),
      `/workspace?project=${encodeURIComponent(projectId)}`,
    );
    assert.doesNotMatch(workspaceUrlAfterGoldenPath(projectId), /\/investigation/);
  });
});
