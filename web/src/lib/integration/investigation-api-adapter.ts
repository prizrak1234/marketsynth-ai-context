/**
 * P0.2 — Backend Investigation ↔ Product Alpha Investigation Workspace mapping.
 * Source/Evidence remain unavailable / local-preview only.
 */

import type { InvestigationDto } from "@/lib/api/types/investigations";
import type { DataOrigin } from "@/lib/integration/contracts";
import type {
  InvestigationStage,
  InvestigationStageId,
  InvestigationStatus,
  StageRunState,
} from "@/lib/investigation/types";

const STAGE_LABELS: Record<InvestigationStageId, string> = {
  project_context: "Project Context",
  market_research: "Market Research",
  competitor_analysis: "Competitor Analysis",
  audience_analysis: "Audience Analysis",
  demand_signals: "Demand Signals",
  economics: "Economics",
  risk_assessment: "Risk Assessment",
  evidence_review: "Evidence Review",
  verdict_preparation: "Verdict Preparation",
};

/** Map durable lifecycle status → frozen Product Alpha view status (display only). */
export function mapLifecycleToViewStatus(
  status: InvestigationDto["status"],
): InvestigationStatus {
  switch (status) {
    case "draft":
    case "ready":
      return "queued";
    case "active":
      return "researching";
    case "blocked":
      return "blocked_by_missing_data";
    case "under_review":
      return "reviewing_evidence";
    case "completed":
      return "completed";
    case "cancelled":
    case "superseded":
      return "completed";
    default:
      return "queued";
  }
}

export function mapBackendStagesToView(
  dto: InvestigationDto,
): InvestigationStage[] {
  return dto.stages.map((s, index) => ({
    id: s.stage_id as InvestigationStageId,
    label: STAGE_LABELS[s.stage_id as InvestigationStageId] ?? s.stage_id,
    order: index + 1,
    state: s.status as StageRunState,
    note:
      s.blocked_reason ??
      (s.stage_id === dto.current_stage
        ? `current · lifecycle ${dto.status}`
        : undefined),
  }));
}

export type InvestigationLifecycleView = {
  origin: DataOrigin;
  investigationId: string;
  version: number;
  status: InvestigationDto["status"];
  viewStatus: InvestigationStatus;
  currentStage: InvestigationStageId;
  stages: InvestigationStage[];
  readinessStatus: InvestigationDto["readiness_status"];
  readinessReasons: string[];
  projectBriefId: string;
  projectBriefVersion: number;
  inputFingerprint: string;
  sourceDomain: "unavailable_until_p0_3";
  evidenceDomain: "unavailable_until_p0_4";
  autoResearchConnected: false;
  notice: string;
};

export function mapInvestigationDtoToLifecycleView(
  dto: InvestigationDto,
): InvestigationLifecycleView {
  return {
    origin: "backend",
    investigationId: dto.id,
    version: dto.version,
    status: dto.status,
    viewStatus: mapLifecycleToViewStatus(dto.status),
    currentStage: dto.current_stage as InvestigationStageId,
    stages: mapBackendStagesToView(dto),
    readinessStatus: dto.readiness_status,
    readinessReasons: dto.readiness_reasons,
    projectBriefId: dto.project_brief_id,
    projectBriefVersion: dto.project_brief_version,
    inputFingerprint: dto.input_fingerprint,
    sourceDomain: "unavailable_until_p0_3",
    evidenceDomain: "unavailable_until_p0_4",
    autoResearchConnected: false,
    notice: "Автоматический исследовательский контур пока не подключён.",
  };
}

export function investigationCreateBodyFromBrief(brief: {
  id: string;
  version: number;
  input_fingerprint: string;
}): {
  project_brief_id: string;
  project_brief_version: number;
  input_fingerprint: string;
} {
  return {
    project_brief_id: brief.id,
    project_brief_version: brief.version,
    input_fingerprint: brief.input_fingerprint,
  };
}

export function pageLoadCreatesInvestigation(): false {
  return false;
}

export function createTriggersAgentRun(): false {
  return false;
}

export function createTriggersLlm(): false {
  return false;
}
