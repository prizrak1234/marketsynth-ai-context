import { apiJson } from "@/lib/api/client";
import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";

export function fetchMarketingStrategies(projectId: string) {
  return apiJson<BackendMarketingStrategyDto[]>(
    `/projects/${projectId}/marketing-strategies`,
  );
}

export function fetchLatestMarketingStrategy(projectId: string) {
  return apiJson<BackendMarketingStrategyDto>(
    `/projects/${projectId}/marketing-strategies/latest`,
  );
}

export function buildMarketingStrategyDraft(
  projectId: string,
  businessVerdictId: string,
) {
  return apiJson<BackendMarketingStrategyDto>(
    `/projects/${projectId}/marketing-strategies/build-draft`,
    {
      method: "POST",
      body: { business_verdict_id: businessVerdictId },
    },
  );
}

export function submitMarketingStrategyReview(projectId: string, strategyId: string) {
  return apiJson<BackendMarketingStrategyDto>(
    `/projects/${projectId}/marketing-strategies/${strategyId}/submit-review`,
    { method: "POST" },
  );
}

export function approveMarketingStrategy(projectId: string, strategyId: string) {
  return apiJson<BackendMarketingStrategyDto>(
    `/projects/${projectId}/marketing-strategies/${strategyId}/approve`,
    { method: "POST" },
  );
}
