/** ImplementationPlan API endpoints (Commercial MVP P1.1). */

import { apiJson } from "@/lib/api/client";
import type {
  BackendImplementationHandoffPreviewDto,
  BackendImplementationPlanDto,
} from "@/lib/api/types/implementation-plans";

export async function fetchImplementationPlans(
  projectId: string,
  opts?: { limit?: number },
): Promise<BackendImplementationPlanDto[]> {
  const limit = opts?.limit ?? 50;
  return apiJson<BackendImplementationPlanDto[]>(
    `/projects/${projectId}/implementation-plans?limit=${limit}`,
  );
}

export async function fetchLatestImplementationPlan(
  projectId: string,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/latest`,
  );
}

export async function buildImplementationPlanDraft(
  projectId: string,
  marketingStrategyId: string,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/build-draft`,
    {
      method: "POST",
      body: { marketing_strategy_id: marketingStrategyId },
    },
  );
}

export async function fetchImplementationHandoffPreview(
  projectId: string,
  planId: string,
): Promise<BackendImplementationHandoffPreviewDto> {
  return apiJson<BackendImplementationHandoffPreviewDto>(
    `/projects/${projectId}/implementation-plans/${planId}/handoff-preview`,
  );
}

export async function submitImplementationPlanReview(
  projectId: string,
  planId: string,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/${planId}/submit-review`,
    { method: "POST" },
  );
}

export async function approveImplementationPlan(
  projectId: string,
  planId: string,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/${planId}/approve`,
    { method: "POST" },
  );
}

export async function fetchImplementationPlan(
  projectId: string,
  planId: string,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/${planId}`,
  );
}

export async function patchImplementationPlan(
  projectId: string,
  planId: string,
  body: Record<string, unknown>,
): Promise<BackendImplementationPlanDto> {
  return apiJson<BackendImplementationPlanDto>(
    `/projects/${projectId}/implementation-plans/${planId}`,
    { method: "PATCH", body },
  );
}

/**
 * Clears local planning gates / open conditions so a draft can reach
 * ready_for_handoff (mirrors Commercial MVP P1.3 freeze test patch).
 * Does not approve, handoff, or create MarketingPlan.
 */
export async function prepareImplementationPlanForHandoff(
  projectId: string,
  planId: string,
): Promise<BackendImplementationPlanDto> {
  const plan = await fetchImplementationPlan(projectId, planId);
  const filtered = plan.tasks.filter((t) =>
    [
      "Research Director",
      "Chief Marketing Strategist",
      "Content Strategist",
      "Copywriter",
      "Analyst",
      "Market Analyst",
      "Risk Officer",
    ].includes(String(t.responsible_role ?? "")),
  );
  const mappable = filtered.length > 0 ? filtered : plan.tasks;
  const tasks = mappable.map((t) => ({
    ...t,
    dependency_ids: [],
    approval_required: false,
    approval_gate_id: null,
    mapping_eligibility: "transformable",
    blocked_reason: null,
  }));
  return patchImplementationPlan(projectId, planId, {
    conditions: [],
    implementation_risks: [],
    dependencies: [],
    budget_gates: (plan.budget_gates ?? []).map((g) => ({
      ...g,
      lifecycle_status: "not_required",
    })),
    approval_gates: (plan.approval_gates ?? []).map((g) => ({
      ...g,
      lifecycle_status: "not_required",
    })),
    tasks,
  });
}
