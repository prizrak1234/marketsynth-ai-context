import { apiJson } from "@/lib/api/client";
import type { MarketingPlan } from "@/lib/api/types/marketing-plans";
import type { ScenarioTemplate } from "@/lib/api/types/marketing-scenarios";

export function fetchMarketingScenarios(projectId: string): Promise<ScenarioTemplate[]> {
  return apiJson<ScenarioTemplate[]>(`/projects/${projectId}/marketing-scenarios`);
}

export function fetchMarketingScenario(
  projectId: string,
  scenarioId: string,
): Promise<ScenarioTemplate> {
  return apiJson<ScenarioTemplate>(
    `/projects/${projectId}/marketing-scenarios/${scenarioId}`,
  );
}

export function createMarketingPlanFromScenario(
  projectId: string,
  scenarioId: string,
): Promise<MarketingPlan> {
  return apiJson<MarketingPlan>(
    `/projects/${projectId}/marketing-scenarios/${scenarioId}/create-plan`,
    { method: "POST" },
  );
}
