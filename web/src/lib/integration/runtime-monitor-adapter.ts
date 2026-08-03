/**
 * Runtime Monitor loader — projection only, not a state engine.
 */

import { fetchBusinessCampaignControlCenter } from "@/lib/api/endpoints/business-campaigns";
import { fetchBusinessCampaignSummaries } from "@/lib/api/endpoints/business-campaigns";
import { hasApiKey } from "@/lib/api/config";
import type { RuntimeMonitorLoadResult } from "@/lib/integration/contracts";
import {
  mapControlCenterToRuntimeMonitor,
  unavailableRuntimeMonitor,
} from "@/lib/integration/control-center-adapter";
import { normalizeIntegrationError } from "@/lib/integration/errors";
import { getIntegrationMode } from "@/lib/integration/mode";
import { MOCK_AGENCY_SPECIALISTS } from "@/lib/workspace/mock-data";
import type { RuntimeMonitorSummaryView } from "@/lib/integration/contracts";

function mockMonitor(projectId: string, projectName: string): RuntimeMonitorSummaryView {
  return {
    projectId,
    projectName,
    campaignId: null,
    campaignName: null,
    healthStatus: null,
    healthLabel: "Mock demo",
    progressPercent: null,
    nextActionLabel: "Continue Product Alpha investigation",
    nextActionDescription: "Deterministic Product Alpha mock — not campaign runtime.",
    supervisorHealthScore: null,
    findingsCount: null,
    criticalFindingsCount: null,
    topFindings: [],
    metricsSummary: "Mock only",
    safeWarnings: ["Mock Agency Runtime Monitor — not Connected Control Center"],
    controlCenterHref: null,
    unavailableCapabilities: [
      "Campaign Control Center not used in mock mode",
      ...[
        "workforce overlay",
        "current_stage (project-wide)",
        "current_owner_role",
        "project-wide timeline summary",
        "project-level decisions ledger",
      ],
    ],
    specialists: MOCK_AGENCY_SPECIALISTS.map((s) => ({ ...s, origin: "mock" as const })),
    origin: "mock",
    badgeLabel: "Live mock · Product Alpha",
  };
}

async function loadFromControlCenter(
  projectId: string,
  projectName: string,
): Promise<RuntimeMonitorLoadResult> {
  const mode = getIntegrationMode();
  if (!hasApiKey()) {
    return {
      state: "unauthorized",
      mode,
      summary: unavailableRuntimeMonitor(projectId, projectName, "Требуется API key."),
      message: "Требуется авторизация (API key).",
      errorStatus: 401,
    };
  }

  try {
    const summaries = await fetchBusinessCampaignSummaries(projectId);
    if (summaries.length === 0) {
      return {
        state: "unsupported",
        mode,
        summary: unavailableRuntimeMonitor(
          projectId,
          projectName,
          "Нет business campaigns — Control Center недоступен для этого проекта.",
        ),
        message: "Capability not integrated for this project (no campaigns).",
        errorStatus: null,
      };
    }

    const primary = summaries[0]!;
    const center = await fetchBusinessCampaignControlCenter(
      projectId,
      primary.campaign.id,
    );
    const summary = mapControlCenterToRuntimeMonitor(projectId, projectName, center);
    summary.controlCenterHref = `/agents/chat?projectId=${encodeURIComponent(projectId)}&campaignId=${encodeURIComponent(primary.campaign.id)}`;
    return {
      state: "success",
      mode,
      summary,
      message: null,
      errorStatus: null,
    };
  } catch (err) {
    const n = normalizeIntegrationError(err);
    return {
      state: n.loadState === "empty" ? "unsupported" : n.loadState,
      mode,
      summary: unavailableRuntimeMonitor(projectId, projectName, n.message),
      message: n.message,
      errorStatus: n.status,
    };
  }
}

export async function loadRuntimeMonitor(
  projectId: string,
  projectName: string,
): Promise<RuntimeMonitorLoadResult> {
  const mode = getIntegrationMode();

  if (mode === "mock") {
    return {
      state: "success",
      mode,
      summary: mockMonitor(projectId, projectName),
      message: null,
      errorStatus: null,
    };
  }

  if (mode === "backend") {
    return loadFromControlCenter(projectId, projectName);
  }

  // HYBRID
  if (!hasApiKey()) {
    return {
      state: "success",
      mode,
      summary: mockMonitor(projectId, projectName),
      message: "Hybrid: mock monitor (API key отсутствует).",
      errorStatus: null,
    };
  }

  const backend = await loadFromControlCenter(projectId, projectName);
  if (backend.state === "success") {
    return { ...backend, mode };
  }

  // Unsupported (no campaigns): labelled mock section allowed in hybrid
  if (backend.state === "unsupported") {
    const mock = mockMonitor(projectId, projectName);
    mock.badgeLabel = "Hybrid · mock gap (no campaign CC)";
    mock.safeWarnings = [
      ...mock.safeWarnings,
      "Backend project has no campaign Control Center — showing labelled mock.",
    ];
    return {
      state: "success",
      mode,
      summary: mock,
      message: backend.message,
      errorStatus: null,
    };
  }

  // Error/unauthorized: do not invent mock progress
  return { ...backend, mode };
}

export {
  mapControlCenterToRuntimeMonitor,
  unavailableRuntimeMonitor,
  AI591_ABSENT_CAPABILITIES,
} from "@/lib/integration/control-center-adapter";
