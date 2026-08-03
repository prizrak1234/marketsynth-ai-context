import { apiJson } from "@/lib/api/client";
import type { MarketingPlan, MarketingPlanStatus, MarketingPlanVersion } from "@/lib/api/types/marketing-plans";

export function fetchMarketingPlans(
  projectId: string,
  params?: { status?: MarketingPlanStatus; limit?: number },
): Promise<MarketingPlan[]> {
  const search = new URLSearchParams();
  if (params?.status) {
    search.set("status", params.status);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<MarketingPlan[]>(`/projects/${projectId}/marketing-plans${suffix}`);
}

export function fetchMarketingPlan(
  projectId: string,
  planId: string,
): Promise<MarketingPlan> {
  return apiJson<MarketingPlan>(`/projects/${projectId}/marketing-plans/${planId}`);
}

export function approveMarketingPlan(
  projectId: string,
  planId: string,
): Promise<MarketingPlan> {
  return apiJson<MarketingPlan>(
    `/projects/${projectId}/marketing-plans/${planId}/approve`,
    { method: "POST" },
  );
}

export function archiveMarketingPlan(
  projectId: string,
  planId: string,
): Promise<MarketingPlan> {
  return apiJson<MarketingPlan>(
    `/projects/${projectId}/marketing-plans/${planId}/archive`,
    { method: "POST" },
  );
}

export function fetchMarketingPlanVersions(
  projectId: string,
  planId: string,
): Promise<MarketingPlanVersion[]> {
  return apiJson<MarketingPlanVersion[]>(
    `/projects/${projectId}/marketing-plans/${planId}/versions`,
  );
}
