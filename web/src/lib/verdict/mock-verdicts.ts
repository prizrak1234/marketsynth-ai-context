/**
 * Verdict scenario helpers + prepare/regenerate API for Product Alpha.
 */

import {
  buildScenarioWorkspace,
  createInvestigationForProject,
  DEMO_PROJECT_IDS,
} from "@/lib/investigation/mock-data";
import { loadInvestigationWorkspace } from "@/lib/investigation/storage";
import { getMockProject } from "@/lib/project-intake/storage";
import { buildBusinessVerdict, classifyVerdictType } from "@/lib/verdict/build-verdict";
import {
  commitVerdictVersion,
  getCurrentVerdict,
  nextVersionNumber,
} from "@/lib/verdict/storage";
import type { BusinessVerdict, VerdictScenarioId } from "@/lib/verdict/types";
import type { InvestigationScenarioId } from "@/lib/investigation/types";

export const VERDICT_SCENARIO_PROJECT: Record<VerdictScenarioId, string> = {
  conditional_go: DEMO_PROJECT_IDS.conditionally_ready,
  insufficient_data: DEMO_PROJECT_IDS.not_ready,
  go: DEMO_PROJECT_IDS.ready_for_review,
  no_go: DEMO_PROJECT_IDS.no_go,
};

const SCENARIO_TO_INV: Record<VerdictScenarioId, InvestigationScenarioId> = {
  conditional_go: "conditionally_ready",
  insufficient_data: "not_ready",
  go: "ready_for_review",
  no_go: "no_go",
};

export function loadInvestigationForVerdict(projectId: string) {
  return (
    loadInvestigationWorkspace(projectId) ??
    createInvestigationForProject(projectId, getMockProject(projectId))
  );
}

/** Prepare or return current verdict; regenerating always creates a new version. */
export function prepareVerdictForProject(
  projectId: string,
  options: { regenerate?: boolean } = {},
): BusinessVerdict {
  const existing = getCurrentVerdict(projectId);
  if (existing && !options.regenerate) {
    return existing;
  }

  const ws = loadInvestigationForVerdict(projectId);
  const version = nextVersionNumber(projectId);
  const verdict = buildBusinessVerdict(ws, {
    version,
    supersedesVerdictId: existing?.id ?? null,
    status: "draft",
  });
  commitVerdictVersion(verdict);
  return verdict;
}

export function expectedTypeForScenario(scenario: VerdictScenarioId) {
  const invId = SCENARIO_TO_INV[scenario];
  const projectId = VERDICT_SCENARIO_PROJECT[scenario];
  const ws = buildScenarioWorkspace(invId, projectId);
  return classifyVerdictType(ws);
}
