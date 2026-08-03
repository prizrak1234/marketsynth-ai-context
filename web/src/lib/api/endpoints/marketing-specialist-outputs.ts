import { apiJson } from "@/lib/api/client";
import type {
  CreateContentAssetFromCopywriterResponse,
  MarketingSpecialistOutput,
  MarketingSpecialistOutputStatus,
  MarketingSpecialistOutputVersion,
  MarketingSpecialistType,
} from "@/lib/api/types/marketing-specialist-outputs";

export function createTaskPlaceholderSpecialistOutput(
  projectId: string,
  runId: string,
  taskIndex: number,
): Promise<MarketingSpecialistOutput> {
  return apiJson<MarketingSpecialistOutput>(
    `/projects/${projectId}/marketing-plan-execution-runs/${runId}/task-outputs/${taskIndex}/placeholder`,
    { method: "POST" },
  );
}

export function fetchMarketingSpecialistOutputs(
  projectId: string,
  params?: {
    execution_run_id?: string;
    marketing_plan_id?: string;
    specialist?: MarketingSpecialistType;
    status?: MarketingSpecialistOutputStatus;
    limit?: number;
  },
): Promise<MarketingSpecialistOutput[]> {
  const search = new URLSearchParams();
  if (params?.execution_run_id) {
    search.set("execution_run_id", params.execution_run_id);
  }
  if (params?.marketing_plan_id) {
    search.set("marketing_plan_id", params.marketing_plan_id);
  }
  if (params?.specialist) {
    search.set("specialist", params.specialist);
  }
  if (params?.status) {
    search.set("status", params.status);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<MarketingSpecialistOutput[]>(
    `/projects/${projectId}/marketing-specialist-outputs${suffix}`,
  );
}

export function fetchMarketingSpecialistOutput(
  projectId: string,
  outputId: string,
): Promise<MarketingSpecialistOutput> {
  return apiJson<MarketingSpecialistOutput>(
    `/projects/${projectId}/marketing-specialist-outputs/${outputId}`,
  );
}

export function createContentAssetFromCopywriterOutput(
  projectId: string,
  outputId: string,
): Promise<CreateContentAssetFromCopywriterResponse> {
  return apiJson<CreateContentAssetFromCopywriterResponse>(
    `/projects/${projectId}/marketing-specialist-outputs/${outputId}/create-content-asset`,
    { method: "POST" },
  );
}

export function approveMarketingSpecialistOutput(
  projectId: string,
  outputId: string,
): Promise<MarketingSpecialistOutput> {
  return apiJson<MarketingSpecialistOutput>(
    `/projects/${projectId}/marketing-specialist-outputs/${outputId}/approve`,
    { method: "POST" },
  );
}

export function archiveMarketingSpecialistOutput(
  projectId: string,
  outputId: string,
): Promise<MarketingSpecialistOutput> {
  return apiJson<MarketingSpecialistOutput>(
    `/projects/${projectId}/marketing-specialist-outputs/${outputId}/archive`,
    { method: "POST" },
  );
}

export function fetchMarketingSpecialistOutputVersions(
  projectId: string,
  outputId: string,
): Promise<MarketingSpecialistOutputVersion[]> {
  return apiJson<MarketingSpecialistOutputVersion[]>(
    `/projects/${projectId}/marketing-specialist-outputs/${outputId}/versions`,
  );
}
