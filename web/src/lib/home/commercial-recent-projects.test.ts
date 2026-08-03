import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import { unavailableLabel } from "@/lib/integration/errors";
import {
  commercialRecentProjectStatusLabel,
  DEFAULT_NEW_PROJECT_NAME,
  filterCommercialRecentProjects,
  isCommercialRecentProjectPlaceholder,
} from "./commercial-recent-projects";

function sampleProject(
  overrides: Partial<WorkspaceProjectViewModel> = {},
): WorkspaceProjectViewModel {
  return {
    id: "p1",
    name: DEFAULT_NEW_PROJECT_NAME,
    status: "paused",
    statusLabel: unavailableLabel(),
    stageLabel: unavailableLabel(),
    lastAction: unavailableLabel(),
    updatedAtLabel: "—",
    pipelineStage: "idea",
    updatedAtIso: "2026-07-30T10:00:00.000Z",
    activeCampaignCount: null,
    nextRecommendedStep: unavailableLabel(),
    controlCenterHref: null,
    origin: "backend",
    ...overrides,
  };
}

describe("commercial recent projects (RUNTIME-01G)", () => {
  it("hides empty placeholder drafts from commercial home", () => {
    assert.equal(isCommercialRecentProjectPlaceholder(sampleProject()), true);
    assert.equal(
      filterCommercialRecentProjects([sampleProject(), sampleProject({ id: "p2" })]).length,
      0,
    );
  });

  it("keeps named projects and maps unavailable stage to commercial label", () => {
    const named = sampleProject({
      id: "named",
      name: "Marketsynth",
    });
    assert.equal(isCommercialRecentProjectPlaceholder(named), false);
    assert.equal(commercialRecentProjectStatusLabel(named), "Не проверялось");
    assert.equal(
      commercialRecentProjectStatusLabel({
        ...named,
        bivLifecycleLabel: "Результат ограничен данными",
      }),
      "Результат ограничен данными",
    );
  });

  it("keeps projects with campaign signal", () => {
    const withCampaign = sampleProject({
      id: "camp",
      name: DEFAULT_NEW_PROJECT_NAME,
      activeCampaignCount: 1,
      stageLabel: "Launch",
    });
    assert.equal(isCommercialRecentProjectPlaceholder(withCampaign), false);
    assert.equal(commercialRecentProjectStatusLabel(withCampaign), "Не проверялось");
  });
});
