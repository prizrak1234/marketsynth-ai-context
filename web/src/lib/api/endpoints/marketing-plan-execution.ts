import { apiJson } from "@/lib/api/client";
import type {
  ExecuteMarketingSpecialistTaskResponse,
  MarketingPlanExecutionRun,
  MarketingPlanExecutionStatus,
} from "@/lib/api/types/marketing-plan-execution";

export function createMarketingPlanExecutionRun(
  projectId: string,
  planId: string,
): Promise<MarketingPlanExecutionRun> {
  return apiJson<MarketingPlanExecutionRun>(
    `/projects/${projectId}/marketing-plans/${planId}/execution-runs`,
    { method: "POST" },
  );
}

export function fetchMarketingPlanExecutionRuns(
  projectId: string,
  params?: {
    marketing_plan_id?: string;
    status?: MarketingPlanExecutionStatus;
    limit?: number;
  },
): Promise<MarketingPlanExecutionRun[]> {
  const search = new URLSearchParams();
  if (params?.marketing_plan_id) {
    search.set("marketing_plan_id", params.marketing_plan_id);
  }
  if (params?.status) {
    search.set("status", params.status);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<MarketingPlanExecutionRun[]>(
    `/projects/${projectId}/marketing-plan-execution-runs${suffix}`,
  );
}

export function startMarketingPlanExecutionRun(
  projectId: string,
  runId: string,
): Promise<MarketingPlanExecutionRun> {
  return apiJson<MarketingPlanExecutionRun>(
    `/projects/${projectId}/marketing-plan-execution-runs/${runId}/start`,
    { method: "POST" },
  );
}

export function completePlaceholderMarketingPlanExecutionRun(
  projectId: string,
  runId: string,
): Promise<MarketingPlanExecutionRun> {
  return apiJson<MarketingPlanExecutionRun>(
    `/projects/${projectId}/marketing-plan-execution-runs/${runId}/complete-placeholder`,
    { method: "POST" },
  );
}

export function executeStrategistTask(
  projectId: string,
  runId: string,
  taskIndex: number,
): Promise<ExecuteMarketingSpecialistTaskResponse> {
  return apiJson<ExecuteMarketingSpecialistTaskResponse>(
    `/projects/${projectId}/marketing-plan-execution-runs/${runId}/tasks/${taskIndex}/execute-specialist`,
    { method: "POST" },
  );
}

export function cancelMarketingPlanExecutionRun(
  projectId: string,
  runId: string,
): Promise<MarketingPlanExecutionRun> {
  return apiJson<MarketingPlanExecutionRun>(
    `/projects/${projectId}/marketing-plan-execution-runs/${runId}/cancel`,
    { method: "POST" },
  );
}
