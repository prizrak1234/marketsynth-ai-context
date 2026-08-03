/** MarketingPlan handoff API (Commercial MVP P1.2). */

import { apiJson } from "@/lib/api/client";
import type {
  BackendMarketingPlanHandoffConfirmDto,
  BackendMarketingPlanHandoffPreviewDto,
} from "@/lib/api/types/marketing-plan-handoff";

export async function previewMarketingPlanHandoff(
  projectId: string,
  planId: string,
): Promise<BackendMarketingPlanHandoffPreviewDto> {
  return apiJson<BackendMarketingPlanHandoffPreviewDto>(
    `/projects/${projectId}/implementation-plans/${planId}/marketing-plan-handoff/preview`,
    { method: "POST", body: {} },
  );
}

export async function confirmMarketingPlanHandoff(
  projectId: string,
  planId: string,
  body: {
    handoff_preview_id: string;
    mapping_fingerprint: string;
    expected_implementation_plan_version: number;
    explicit_confirmation: boolean;
    existing_plan_policy?: "create_new_draft" | "cancel";
    note?: string;
  },
): Promise<BackendMarketingPlanHandoffConfirmDto> {
  return apiJson<BackendMarketingPlanHandoffConfirmDto>(
    `/projects/${projectId}/implementation-plans/${planId}/marketing-plan-handoff/confirm`,
    { method: "POST", body },
  );
}
