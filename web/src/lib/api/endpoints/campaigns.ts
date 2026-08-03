import { apiJson } from "@/lib/api/client";
import type {
  CampaignAssetListItem,
  CampaignOverviewResponse,
  CampaignWorkflowResponse,
  MarketingCampaign,
  MarketingCampaignCreateBody,
  MarketingCampaignUpdateBody,
} from "@/lib/api/types/campaigns";
import type { PublicationJob } from "@/lib/api/types/publishing";

function projectCampaignsPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/campaigns${suffix}`;
}

export function fetchCampaigns(
  projectId: string,
  params?: { includeArchived?: boolean; limit?: number },
) {
  const search = new URLSearchParams();
  if (params?.includeArchived) {
    search.set("include_archived", "true");
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  return apiJson<MarketingCampaign[]>(
    `${projectCampaignsPath(projectId)}${query ? `?${query}` : ""}`,
  );
}

export function createCampaign(
  projectId: string,
  body: MarketingCampaignCreateBody,
) {
  return apiJson<MarketingCampaign>(projectCampaignsPath(projectId), {
    method: "POST",
    body,
  });
}

export function updateCampaign(
  projectId: string,
  campaignId: string,
  body: MarketingCampaignUpdateBody,
) {
  return apiJson<MarketingCampaign>(
    projectCampaignsPath(projectId, `/${campaignId}`),
    { method: "PATCH", body },
  );
}

export function archiveCampaign(projectId: string, campaignId: string) {
  return apiJson<MarketingCampaign>(
    projectCampaignsPath(projectId, `/${campaignId}/archive`),
    { method: "POST" },
  );
}

export function fetchCampaign(projectId: string, campaignId: string) {
  return apiJson<MarketingCampaign>(projectCampaignsPath(projectId, `/${campaignId}`));
}

export function fetchCampaignWorkflow(projectId: string, campaignId: string) {
  return apiJson<CampaignWorkflowResponse>(
    projectCampaignsPath(projectId, `/${campaignId}/workflow`),
  );
}

export function fetchCampaignOverview(projectId: string, campaignId: string) {
  return apiJson<CampaignOverviewResponse>(
    projectCampaignsPath(projectId, `/${campaignId}/overview`),
  );
}

export function fetchCampaignAssets(projectId: string, campaignId: string) {
  return apiJson<CampaignAssetListItem[]>(
    projectCampaignsPath(projectId, `/${campaignId}/assets`),
  );
}

export function fetchCampaignPublicationJobs(
  projectId: string,
  campaignId: string,
  params?: { limit?: number },
) {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  return apiJson<PublicationJob[]>(
    projectCampaignsPath(
      projectId,
      `/${campaignId}/publication-jobs${query ? `?${query}` : ""}`,
    ),
  );
}

