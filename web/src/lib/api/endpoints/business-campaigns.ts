import { apiJson } from "@/lib/api/client";
import type {
  BusinessCampaign,
  CampaignActionResult,
  CampaignControlCenter,
  CampaignControlCenterSummary,
  CampaignDashboard,
  CampaignHealthStatus,
  CampaignMetrics,
  CampaignNextActionType,
  CampaignSupervisorReport,
  CampaignWorkflowRun,
  CreateBusinessCampaignInput,
  UpdateBusinessCampaignInput,
} from "@/lib/api/types/business-campaigns";
import type { ScenarioWizardRun } from "@/lib/api/types/scenario-wizard-runs";

export function fetchBusinessCampaigns(
  projectId: string,
): Promise<BusinessCampaign[]> {
  return apiJson<BusinessCampaign[]>(`/projects/${projectId}/business-campaigns`);
}

export function fetchBusinessCampaign(
  projectId: string,
  campaignId: string,
): Promise<BusinessCampaign> {
  return apiJson<BusinessCampaign>(
    `/projects/${projectId}/business-campaigns/${campaignId}`,
  );
}

export function searchBusinessCampaigns(
  projectId: string,
  params: { q?: string; scenario_id?: string; status?: string } = {},
): Promise<BusinessCampaign[]> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.scenario_id) query.set("scenario_id", params.scenario_id);
  if (params.status) query.set("status", params.status);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiJson<BusinessCampaign[]>(
    `/projects/${projectId}/business-campaigns/search${suffix}`,
  );
}

export function createBusinessCampaign(
  projectId: string,
  body: CreateBusinessCampaignInput,
): Promise<BusinessCampaign> {
  return apiJson<BusinessCampaign>(`/projects/${projectId}/business-campaigns`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateBusinessCampaign(
  projectId: string,
  campaignId: string,
  body: UpdateBusinessCampaignInput,
): Promise<BusinessCampaign> {
  return apiJson<BusinessCampaign>(
    `/projects/${projectId}/business-campaigns/${campaignId}`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    },
  );
}

export function executeCampaignAction(
  projectId: string,
  campaignId: string,
  actionType: string,
  idempotencyKey?: string,
): Promise<CampaignActionResult> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return apiJson<CampaignActionResult>(
    `/projects/${projectId}/business-campaigns/${campaignId}/actions/${actionType}/execute`,
    {
      method: "POST",
      headers,
    },
  );
}

export function fetchBusinessCampaignSupervisorReport(
  projectId: string,
  campaignId: string,
): Promise<CampaignSupervisorReport> {
  return apiJson<CampaignSupervisorReport>(
    `/projects/${projectId}/business-campaigns/${campaignId}/supervisor-report`,
  );
}

export function createCampaignWorkflowRun(
  projectId: string,
  campaignId: string,
  templateId: string,
): Promise<CampaignWorkflowRun> {
  return apiJson<CampaignWorkflowRun>(
    `/projects/${projectId}/business-campaigns/${campaignId}/workflows/${templateId}/create-run`,
    { method: "POST" },
  );
}

export function fetchBusinessCampaignControlCenter(
  projectId: string,
  campaignId: string,
): Promise<CampaignControlCenter> {
  return apiJson<CampaignControlCenter>(
    `/projects/${projectId}/business-campaigns/${campaignId}/control-center`,
  );
}

export function fetchBusinessCampaignSummaries(
  projectId: string,
  params: {
    q?: string;
    health?: CampaignHealthStatus;
    next_action_type?: CampaignNextActionType;
    failed_only?: boolean;
    completed_only?: boolean;
  } = {},
): Promise<CampaignControlCenterSummary[]> {
  const query = new URLSearchParams({ view: "control" });
  if (params.q) query.set("q", params.q);
  if (params.health) query.set("health", params.health);
  if (params.next_action_type) query.set("next_action_type", params.next_action_type);
  if (params.failed_only) query.set("failed_only", "true");
  if (params.completed_only) query.set("completed_only", "true");
  return apiJson<CampaignControlCenterSummary[]>(
    `/projects/${projectId}/business-campaigns/search?${query.toString()}`,
  );
}

export function fetchBusinessCampaignDashboard(
  projectId: string,
  campaignId: string,
): Promise<CampaignDashboard> {
  return apiJson<CampaignDashboard>(
    `/projects/${projectId}/business-campaigns/${campaignId}/dashboard`,
  );
}

export function fetchBusinessCampaignMetrics(
  projectId: string,
  campaignId: string,
): Promise<CampaignMetrics> {
  return apiJson<CampaignMetrics>(
    `/projects/${projectId}/business-campaigns/${campaignId}/metrics`,
  );
}

export function createCampaignScenarioWizardRun(
  projectId: string,
  campaignId: string,
): Promise<ScenarioWizardRun> {
  return apiJson<ScenarioWizardRun>(
    `/projects/${projectId}/business-campaigns/${campaignId}/scenario-wizard-runs`,
    { method: "POST" },
  );
}
