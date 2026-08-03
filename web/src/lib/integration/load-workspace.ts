/**
 * Load Workspace projects according to Integration Mode.
 * BACKEND: never silently substitute mock business facts on failure.
 */

import { fetchProjects } from "@/lib/api/endpoints/projects";
import { fetchBusinessCampaignSummaries } from "@/lib/api/endpoints/business-campaigns";
import { canUseBackendApi } from "@/lib/api/config";
import type { WorkspaceProjectsLoadResult } from "@/lib/integration/contracts";
import { normalizeIntegrationError } from "@/lib/integration/errors";
import {
  mapProjectToWorkspaceView,
  mapProjectWithoutCampaigns,
} from "@/lib/integration/project-adapter";
import { getIntegrationMode } from "@/lib/integration/mode";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import type { WorkspaceProject } from "@/lib/workspace/types";
import { MOCK_PROJECTS } from "@/lib/workspace/mock-data";

function mockProjectsAsViewModels(): WorkspaceProjectViewModel[] {
  return MOCK_PROJECTS.map((p: WorkspaceProject) => ({
    ...p,
    updatedAtIso: null,
    activeCampaignCount: null,
    nextRecommendedStep: p.lastAction || "Mock demo next step",
    controlCenterHref: null,
    origin: "mock" as const,
  }));
}

async function loadBackendProjects(): Promise<WorkspaceProjectsLoadResult> {
  const mode = getIntegrationMode();
  if (!canUseBackendApi()) {
    return {
      state: "unauthorized",
      mode,
      projects: [],
      message: "Требуется API key для backend mode.",
      errorStatus: 401,
    };
  }

  try {
    const projects = await fetchProjects();
    if (projects.length === 0) {
      return {
        state: "empty",
        mode,
        projects: [],
        message: "Нет проектов.",
        errorStatus: null,
      };
    }

    const views: WorkspaceProjectViewModel[] = [];
    for (const project of projects) {
      try {
        const summaries = await fetchBusinessCampaignSummaries(project.id);
        views.push(mapProjectToWorkspaceView(project, { campaignSummaries: summaries }));
      } catch {
        // Campaign read failed — keep project; do not invent campaigns
        views.push(mapProjectWithoutCampaigns(project));
      }
    }

    return {
      state: "success",
      mode,
      projects: views,
      message: null,
      errorStatus: null,
    };
  } catch (err) {
    const n = normalizeIntegrationError(err);
    return {
      state: n.loadState === "empty" ? "empty" : n.loadState,
      mode,
      projects: [],
      message: n.message,
      errorStatus: n.status,
    };
  }
}

/**
 * Resolve Workspace project list for current integration mode.
 */
export async function loadWorkspaceProjects(): Promise<WorkspaceProjectsLoadResult> {
  const mode = getIntegrationMode();

  if (mode === "mock") {
    const projects = mockProjectsAsViewModels();
    return {
      state: projects.length === 0 ? "empty" : "success",
      mode,
      projects,
      message: null,
      errorStatus: null,
    };
  }

  if (mode === "backend") {
    return loadBackendProjects();
  }

  // HYBRID: backend projects when possible; labelled mock only if config/unavailable
  if (!canUseBackendApi()) {
    return {
      state: "success",
      mode,
      projects: mockProjectsAsViewModels(),
      message: "Hybrid: demo projects (API key отсутствует) — mock section.",
      errorStatus: null,
    };
  }

  const backend = await loadBackendProjects();
  if (backend.state === "success" || backend.state === "empty") {
    return { ...backend, mode };
  }

  // Failure in hybrid: do not fake progress — surface error, optional mock only as labelled demo
  return {
    state: backend.state,
    mode,
    projects: [],
    message: `${backend.message ?? "Данные недоступны"} Hybrid не подменяет ошибку mock-прогрессом.`,
    errorStatus: backend.errorStatus,
  };
}
