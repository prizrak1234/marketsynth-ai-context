import { apiJson } from "@/lib/api/client";
import type { ScenarioWizardRun } from "@/lib/api/types/scenario-wizard-runs";

export function fetchScenarioWizardRuns(
  projectId: string,
): Promise<ScenarioWizardRun[]> {
  return apiJson<ScenarioWizardRun[]>(`/projects/${projectId}/scenario-wizard-runs`);
}

export function fetchScenarioWizardRun(
  projectId: string,
  runId: string,
): Promise<ScenarioWizardRun> {
  return apiJson<ScenarioWizardRun>(
    `/projects/${projectId}/scenario-wizard-runs/${runId}`,
  );
}

export function createScenarioWizardRun(
  projectId: string,
  scenarioId: string,
): Promise<ScenarioWizardRun> {
  return apiJson<ScenarioWizardRun>(`/projects/${projectId}/scenario-wizard-runs`, {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
}

export function advanceScenarioWizardRun(
  projectId: string,
  runId: string,
): Promise<ScenarioWizardRun> {
  return apiJson<ScenarioWizardRun>(
    `/projects/${projectId}/scenario-wizard-runs/${runId}/advance`,
    { method: "POST" },
  );
}
