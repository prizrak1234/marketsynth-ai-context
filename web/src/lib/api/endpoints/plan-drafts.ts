import { apiJson } from "@/lib/api/client";
import type {
  CampaignPlanDraft,
  CampaignPlanDraftCreateBody,
  PlanDraftGenerateAssetsResponse,
} from "@/lib/api/types/plan-drafts";

function planDraftPath(
  projectId: string,
  campaignId: string,
  draftId = "",
  suffix = "",
) {
  const base = `/projects/${projectId}/campaigns/${campaignId}/plan-drafts`;
  if (!draftId) {
    return `${base}${suffix}`;
  }
  return `${base}/${draftId}${suffix}`;
}

export function fetchCampaignPlanDrafts(
  projectId: string,
  campaignId: string,
  params?: { includeArchived?: boolean },
) {
  const search = new URLSearchParams({ limit: "100" });
  if (params?.includeArchived) {
    search.set("include_archived", "true");
  }
  return apiJson<CampaignPlanDraft[]>(
    `${planDraftPath(projectId, campaignId)}?${search.toString()}`,
  );
}

export function fetchCampaignPlanDraft(
  projectId: string,
  campaignId: string,
  draftId: string,
) {
  return apiJson<CampaignPlanDraft>(
    planDraftPath(projectId, campaignId, draftId),
  );
}

export function createCampaignPlanDraft(
  projectId: string,
  campaignId: string,
  body: CampaignPlanDraftCreateBody,
) {
  return apiJson<CampaignPlanDraft>(planDraftPath(projectId, campaignId), {
    method: "POST",
    body,
  });
}

export function archiveCampaignPlanDraft(
  projectId: string,
  campaignId: string,
  draftId: string,
) {
  return apiJson<CampaignPlanDraft>(
    planDraftPath(projectId, campaignId, draftId, "/archive"),
    { method: "POST" },
  );
}

export function generateAssetsFromPlanDraft(
  projectId: string,
  campaignId: string,
  draftId: string,
) {
  return apiJson<PlanDraftGenerateAssetsResponse>(
    planDraftPath(projectId, campaignId, draftId, "/generate-assets"),
    { method: "POST" },
  );
}
