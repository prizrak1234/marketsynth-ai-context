/**
 * I3 — Investigation Workspace load adapter (Option B).
 *
 * Reuses Project + Campaign Control Center + Supervisor + related Skill runs.
 * Does NOT create a second Runtime / research engine.
 * Does NOT promote Supervisor/LLM/Skill output to Evidence.
 * Stages are UI projections only — no fake progress %.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  fetchBusinessCampaignControlCenter,
  fetchBusinessCampaignSummaries,
  fetchBusinessCampaignSupervisorReport,
} from "@/lib/api/endpoints/business-campaigns";
import { fetchMarketingSkillRuns } from "@/lib/api/endpoints/marketing-skills";
import { fetchProject, type Project } from "@/lib/api/endpoints/projects";
import type {
  CampaignControlCenter,
  CampaignControlCenterSummary,
  CampaignSupervisorReport,
} from "@/lib/api/types/business-campaigns";
import type { DataOrigin, LoadState } from "@/lib/integration/contracts";
import {
  mapSupervisorReportToQualitySignals,
  qualitySignalsAreNotEvidence,
  type QualitySignalView,
} from "@/lib/integration/evidence-adapter";
import {
  normalizeInvestigationError,
  partialIntegrationNotice,
  type InvestigationError,
} from "@/lib/integration/investigation-errors";
import {
  mapCampaignHealthToViewStatus,
  mockOnlyViewStatus,
  unsupportedLifecycleStatus,
  type InvestigationViewStatusResult,
} from "@/lib/integration/investigation-status-adapter";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  mapSkillRunsToResearchArtifacts,
  mapSkillTypeToStageHint,
  type ResearchArtifactView,
} from "@/lib/integration/source-adapter";
import type {
  InvestigationStage,
  InvestigationStageId,
  StageRunState,
} from "@/lib/investigation/types";

export type InvestigationTimelineEventView = {
  id: string;
  label: string;
  occurredAt: string;
  summary: string | null;
  origin: DataOrigin;
  disclaimer: string;
};

export type InvestigationStageProjection = InvestigationStage & {
  origin: DataOrigin;
  completionRule: string;
};

export type InvestigationBackendBundle = {
  project: Project | null;
  campaignId: string | null;
  campaignName: string | null;
  controlCenter: CampaignControlCenter | null;
  supervisorReport: CampaignSupervisorReport | null;
  qualitySignals: QualitySignalView[];
  researchArtifacts: ResearchArtifactView[];
  stageProjections: InvestigationStageProjection[];
  timelineEvents: InvestigationTimelineEventView[];
  viewStatus: InvestigationViewStatusResult;
  intakeFingerprint: string | null;
  intakeLocalOnly: true;
  evidenceSoT: "absent";
  sourceSoT: "absent";
  qualitySignalsAreNotEvidence: true;
  noBusinessVerdict: true;
  pageLoadTriggersProviders: false;
};

export type InvestigationLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  bundle: InvestigationBackendBundle | null;
  partialNotice: InvestigationError | null;
  error: InvestigationError | null;
  /** When true, UI may keep Product Alpha mock workspace for artifact gaps */
  allowMockArtifacts: boolean;
};

const STAGE_DEFS: Array<{ id: InvestigationStageId; label: string; order: number }> = [
  { id: "project_context", label: "Project Context", order: 1 },
  { id: "market_research", label: "Market Research", order: 2 },
  { id: "competitor_analysis", label: "Competitor Analysis", order: 3 },
  { id: "audience_analysis", label: "Audience Analysis", order: 4 },
  { id: "demand_signals", label: "Demand Signals", order: 5 },
  { id: "economics", label: "Economics", order: 6 },
  { id: "risk_assessment", label: "Risk Assessment", order: 7 },
  { id: "evidence_review", label: "Evidence Review", order: 8 },
  { id: "verdict_preparation", label: "Verdict Preparation", order: 9 },
];

function emptyBundle(partial: Partial<InvestigationBackendBundle>): InvestigationBackendBundle {
  return {
    project: null,
    campaignId: null,
    campaignName: null,
    controlCenter: null,
    supervisorReport: null,
    qualitySignals: [],
    researchArtifacts: [],
    stageProjections: [],
    timelineEvents: [],
    viewStatus: unsupportedLifecycleStatus(),
    intakeFingerprint: null,
    intakeLocalOnly: true,
    evidenceSoT: "absent",
    sourceSoT: "absent",
    qualitySignalsAreNotEvidence: qualitySignalsAreNotEvidence(),
    noBusinessVerdict: true,
    pageLoadTriggersProviders: false,
    ...partial,
  };
}

function buildStageProjections(input: {
  hasProject: boolean;
  hasCampaign: boolean;
  artifactHints: Set<InvestigationStageId>;
  qualitySignalCount: number;
}): InvestigationStageProjection[] {
  return STAGE_DEFS.map((def) => {
    let state: StageRunState = "not_started";
    let note = "Нет backend Investigation stage run.";
    let origin: DataOrigin = "derived";
    let completionRule = "Frontend projection only — no backend stage machine.";

    if (def.id === "project_context" && input.hasProject) {
      state = "completed";
      note = "Project core загружен с backend.";
      origin = "backend";
      completionRule = "Project record exists.";
    } else if (
      (def.id === "market_research" ||
        def.id === "audience_analysis" ||
        def.id === "demand_signals") &&
      input.artifactHints.has(def.id)
    ) {
      state = "needs_review";
      note = "Есть related MarketingSkillRun — кандидат, не завершённый stage.";
      origin = "derived";
      completionRule = "Skill run present ≠ stage completed.";
    } else if (def.id === "risk_assessment" && input.qualitySignalCount > 0) {
      state = "needs_review";
      note = "Supervisor quality signals available — not Risk Assessment completion.";
      origin = "derived";
      completionRule = "Quality signals projected; InvestigationRisk entity absent.";
    } else if (def.id === "evidence_review") {
      state = "blocked";
      note = "InvestigationEvidence SoT отсутствует.";
      origin = "derived";
      completionRule = "Evidence domain absent → blocked projection.";
    } else if (def.id === "verdict_preparation") {
      state = "not_started";
      note = "Business Verdict — I4. Verdict readiness остаётся frontend-only.";
      completionRule = "No verdict generation in I3.";
    } else if (input.hasCampaign && def.id === "project_context") {
      state = "completed";
    }

    return {
      ...def,
      state,
      note,
      origin,
      completionRule,
    };
  });
}

function pickPrimaryCampaign(
  summaries: CampaignControlCenterSummary[],
): CampaignControlCenterSummary | null {
  if (summaries.length === 0) return null;
  const active = summaries.find((s) => s.campaign.status === "active");
  return active ?? summaries[0]!;
}

function mapTimeline(cc: CampaignControlCenter | null): InvestigationTimelineEventView[] {
  if (!cc) return [];
  return cc.timeline.slice(0, 20).map((ev, i) => ({
    id: `cc_tl_${i}_${ev.resource_id}`,
    label: ev.label,
    occurredAt: ev.occurred_at,
    summary: ev.safe_summary ?? null,
    origin: "backend" as const,
    disclaimer: "Campaign Control Center timeline — не Investigation research stage log.",
  }));
}

/**
 * Load Investigation backend projections for a real Project id.
 * Does not start LLM, agents, or providers.
 */
export async function loadInvestigationBackendBundle(
  projectId: string,
): Promise<InvestigationLoadResult> {
  const mode = getIntegrationMode();

  if (mode === "mock") {
    return {
      state: "success",
      mode,
      bundle: emptyBundle({
        viewStatus: mockOnlyViewStatus(),
        stageProjections: buildStageProjections({
          hasProject: false,
          hasCampaign: false,
          artifactHints: new Set(),
          qualitySignalCount: 0,
        }),
      }),
      partialNotice: null,
      error: null,
      allowMockArtifacts: true,
    };
  }

  if (!canUseBackendApi()) {
    return {
      state: "unauthorized",
      mode,
      bundle: null,
      partialNotice: null,
      error: normalizeInvestigationError(new ApiError("API key required", 401, null)),
      allowMockArtifacts: mode === "hybrid",
    };
  }

  try {
    const project = await fetchProject(projectId);
    let summaries: CampaignControlCenterSummary[] = [];
    try {
      summaries = await fetchBusinessCampaignSummaries(projectId);
    } catch {
      summaries = [];
    }

    const primary = pickPrimaryCampaign(summaries);
    let controlCenter: CampaignControlCenter | null = null;
    let supervisorReport: CampaignSupervisorReport | null = null;
    let researchArtifacts: ResearchArtifactView[] = [];

    if (primary) {
      try {
        controlCenter = await fetchBusinessCampaignControlCenter(
          projectId,
          primary.campaign.id,
        );
      } catch {
        controlCenter = null;
      }
      try {
        supervisorReport = await fetchBusinessCampaignSupervisorReport(
          projectId,
          primary.campaign.id,
        );
      } catch {
        supervisorReport = null;
      }
    }

    try {
      const runs = await fetchMarketingSkillRuns(projectId, { limit: 50 });
      researchArtifacts = mapSkillRunsToResearchArtifacts(runs);
    } catch {
      researchArtifacts = [];
    }

    const qualitySignals = mapSupervisorReportToQualitySignals(supervisorReport);
    const artifactHints = new Set<InvestigationStageId>();
    for (const a of researchArtifacts) {
      const hint = mapSkillTypeToStageHint(a.skillType);
      if (hint) artifactHints.add(hint);
    }

    let viewStatus = mapCampaignHealthToViewStatus(controlCenter?.health.status);
    if (researchArtifacts.length > 0) {
      viewStatus = {
        ...viewStatus,
        viewStatus: "research_artifacts_available",
        rationale: `${viewStatus.rationale} Related skill runs present as artifact candidates.`,
      };
    }
    if (qualitySignals.length > 0 && viewStatus.viewStatus !== "blocked") {
      viewStatus = {
        ...viewStatus,
        viewStatus: "quality_signals_available",
        rationale: `${viewStatus.rationale} Supervisor quality signals projected (not evidence).`,
      };
    }

    const bundle = emptyBundle({
      project,
      campaignId: primary?.campaign.id ?? null,
      campaignName: primary?.campaign.name ?? null,
      controlCenter,
      supervisorReport,
      qualitySignals,
      researchArtifacts,
      stageProjections: buildStageProjections({
        hasProject: true,
        hasCampaign: Boolean(primary),
        artifactHints,
        qualitySignalCount: qualitySignals.length,
      }),
      timelineEvents: mapTimeline(controlCenter),
      viewStatus,
      intakeFingerprint: `project:${project.id}:updated:${project.updated_at}`,
    });

    return {
      state: "success",
      mode,
      bundle,
      partialNotice: partialIntegrationNotice(),
      error: null,
      allowMockArtifacts: mode === "hybrid",
    };
  } catch (err) {
    const n = normalizeInvestigationError(err);
    // Fix unauthorized detection for ApiError-shaped
    return {
      state: n.kind === "unauthorized" ? "unauthorized" : n.kind === "project_not_found" ? "empty" : "error",
      mode,
      bundle: null,
      partialNotice: null,
      error: n,
      allowMockArtifacts: mode === "hybrid",
    };
  }
}

/** Agent Run / Task inclusion rules (documented + exported for selfcheck). */
export const AGENT_RUN_INCLUSION_RULES = {
  include: [
    "MarketingSkillRun with skill_type in INVESTIGATION_RELATED_SKILL_TYPES",
    "Campaign-scoped Control Center timeline for primary campaign of project",
    "Campaign Supervisor report for primary campaign",
  ],
  exclude: [
    "Unrelated AgentRun without project investigation metadata",
    "Publishing / media / package execution runs as Investigation evidence",
    "LLMRequest/LLMResponse as Source or Evidence",
    "Generic Task with arbitrary input_payload",
    "Campaign execution readiness / approval readiness as Verdict readiness",
  ],
} as const;
