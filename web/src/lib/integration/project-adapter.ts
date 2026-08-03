/**
 * Project API → WorkspaceProjectViewModel adapter.
 * Does not invent pipeline stages / next steps when absent.
 */

import type { Project } from "@/lib/api/endpoints/projects";
import type { CampaignControlCenterSummary } from "@/lib/api/types/business-campaigns";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import { unavailableLabel } from "@/lib/integration/errors";

function formatUpdatedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return unavailableLabel();
  }
}

/**
 * Map a backend Project into a Workspace card view model.
 * Status/stage are honest placeholders when backend has no pipeline enum.
 */
export function mapProjectToWorkspaceView(
  project: Project,
  options: {
    campaignSummaries?: CampaignControlCenterSummary[];
  } = {},
): WorkspaceProjectViewModel {
  const summaries = options.campaignSummaries ?? [];
  const activeCampaigns = summaries.filter(
    (s) => s.campaign.status === "active" || s.campaign.status === "draft",
  );
  const primary = summaries[0] ?? null;
  const nextStep = primary?.next_action_type
    ? primary.next_action_type.replace(/_/g, " ")
    : unavailableLabel();

  const campaignsProvided = options.campaignSummaries !== undefined;
  const controlCenterHref =
    primary != null
      ? `/agents/chat?projectId=${encodeURIComponent(project.id)}&campaignId=${encodeURIComponent(primary.campaign.id)}`
      : null;

  return {
    id: project.id,
    name: project.name,
    status: "paused",
    statusLabel: unavailableLabel(),
    stageLabel: unavailableLabel(),
    lastAction:
      primary != null
        ? `Campaign: ${primary.campaign.name} · health ${primary.health.status}`
        : unavailableLabel(),
    updatedAtLabel: formatUpdatedAt(project.updated_at),
    pipelineStage: "idea",
    updatedAtIso: project.updated_at,
    activeCampaignCount: campaignsProvided ? activeCampaigns.length : null,
    nextRecommendedStep: nextStep,
    controlCenterHref,
    origin: "backend",
  };
}

/**
 * When campaign summaries were not fetched, keep count null (= unavailable).
 */
export function mapProjectWithoutCampaigns(project: Project): WorkspaceProjectViewModel {
  return {
    ...mapProjectToWorkspaceView(project, {}),
    activeCampaignCount: null,
    nextRecommendedStep: unavailableLabel(),
    lastAction: unavailableLabel(),
    controlCenterHref: null,
  };
}
