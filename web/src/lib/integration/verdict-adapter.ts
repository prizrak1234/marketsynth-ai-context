/**
 * I4 — Business Verdict load adapter (Option C).
 *
 * Source of Truth for commercial verdict in I4:
 *   Product Alpha local / deterministic builder (labelled),
 *   until durable Evidence + BusinessVerdict domain are approved.
 *
 * VerdictKind stub exists in contracts — no runtime entity.
 * Never promote Supervisor / CC next_action / readiness → BusinessVerdict.
 * Never auto-upload local verdict to backend.
 * Never convert backend failure → mock success in backend mode.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  fetchBusinessCampaignSummaries,
  fetchBusinessCampaignSupervisorReport,
} from "@/lib/api/endpoints/business-campaigns";
import {
  fetchBusinessVerdicts,
  fetchLatestBusinessVerdict,
} from "@/lib/api/endpoints/business-verdicts";
import { fetchProject } from "@/lib/api/endpoints/projects";
import type { CampaignSupervisorReport } from "@/lib/api/types/business-campaigns";
import type { LoadState } from "@/lib/integration/contracts";
import {
  type DecisionSemanticCategory,
  type VerdictInputSignal,
} from "@/lib/integration/decision-semantics";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  resolveStrategyEligibility,
  type StrategyEligibilityResult,
} from "@/lib/integration/strategy-eligibility";
import { mapBackendVerdictToProductAlpha } from "@/lib/integration/business-verdict-api-adapter";
import { normalizeBusinessVerdictError } from "@/lib/integration/business-verdict-errors";
import { localVerdictImportPolicy } from "@/lib/integration/business-verdict-sync";
import { mapBackendStrategyEligibility } from "@/lib/integration/verdict-strategy-eligibility-adapter";
import {
  normalizeVerdictError,
  unsupportedVerdictCapability,
  type VerdictError,
} from "@/lib/integration/verdict-errors";
import {
  deterministicLocalPreviewOrigin,
  durableBackendVerdictOrigin,
  mockVerdictOrigin,
  unsupportedBackendVerdictOrigin,
  type VerdictOriginMeta,
} from "@/lib/integration/verdict-origin";
import type { BusinessVerdict } from "@/lib/verdict/types";
import { getCurrentVerdict, listVerdictVersions } from "@/lib/verdict/storage";
import { prepareVerdictForProject } from "@/lib/verdict/mock-verdicts";

export type BusinessVerdictViewModel = {
  verdict: BusinessVerdict | null;
  versions: BusinessVerdict[];
  originMeta: VerdictOriginMeta;
  inputSignals: VerdictInputSignal[];
  strategyEligibility: StrategyEligibilityResult;
  /** Explicit: local review status ≠ execution approval */
  verdictReviewIsNotExecutionApproval: true;
  autoUploadDisabled: true;
  noBackendVerdictEntity: boolean;
};

export type VerdictLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  view: BusinessVerdictViewModel | null;
  error: VerdictError | null;
  projectName: string | null;
};

function mapSupervisorToInputSignals(
  report: CampaignSupervisorReport | null,
): VerdictInputSignal[] {
  if (!report) return [];
  const out: VerdictInputSignal[] = [];
  report.findings.forEach((f, i) => {
    out.push({
      id: `sig_finding_${i}`,
      role: "quality_warning",
      title: f.title,
      description: f.description,
      sourceObject: "CampaignSupervisorFinding",
      category: "supervisor_quality_finding",
      origin: "backend",
      disclaimer: "SupervisorFinding → VerdictInputSignal only. Не BusinessVerdict.",
    });
  });
  report.risks.forEach((r, i) => {
    out.push({
      id: `sig_risk_${i}`,
      role: "risk_signal",
      title: "Campaign risk string",
      description: r,
      sourceObject: "CampaignSupervisorReport.risks",
      category: "advisory_recommendation",
      origin: "backend",
      disclaimer: "Advisory risk signal — не verdict type.",
    });
  });
  report.recommended_next_actions.forEach((a, i) => {
    out.push({
      id: `sig_next_${i}`,
      role: "recommended_next_step",
      title: String(a),
      description: "Supervisor recommended_next_action",
      sourceObject: "CampaignSupervisorReport.recommended_next_actions",
      category: "advisory_recommendation" satisfies DecisionSemanticCategory,
      origin: "backend",
      disclaimer: "Operational/advisory — не Control Center ≠ BusinessVerdict, но и не вердикт.",
    });
  });
  return out;
}

function eligibilityFor(
  verdict: BusinessVerdict | null,
  originMeta: VerdictOriginMeta,
): StrategyEligibilityResult {
  return resolveStrategyEligibility({
    verdictType: verdict?.type ?? null,
    verdictStatus: verdict?.status ?? null,
    origin: originMeta,
    readinessStatus: null,
  });
}

/**
 * Load Business Verdict for Product Alpha Workspace.
 * Does not create Strategy, ExecutionApproval, or call providers.
 */
export async function loadBusinessVerdictView(
  projectId: string,
  options?: { ensureLocalPreview?: boolean },
): Promise<VerdictLoadResult> {
  const mode = getIntegrationMode();
  const ensure = options?.ensureLocalPreview ?? true;

  if (mode === "mock") {
    const verdict = ensure
      ? prepareVerdictForProject(projectId)
      : getCurrentVerdict(projectId);
    const originMeta = mockVerdictOrigin();
    return {
      state: verdict ? "success" : "empty",
      mode,
      view: {
        verdict,
        versions: listVerdictVersions(projectId),
        originMeta,
        inputSignals: [],
        strategyEligibility: eligibilityFor(verdict, originMeta),
        verdictReviewIsNotExecutionApproval: true,
        autoUploadDisabled: true,
        noBackendVerdictEntity: true,
      },
      error: null,
      projectName: verdict?.projectName ?? null,
    };
  }

  // backend | hybrid — probe project; no BusinessVerdict API
  if (!canUseBackendApi()) {
    return {
      state: "unauthorized",
      mode,
      view: null,
      error: normalizeVerdictError(new ApiError("unauthorized", 401, null)),
      projectName: null,
    };
  }

  let projectName: string | null = null;
  try {
    const project = await fetchProject(projectId);
    projectName = project.name;
  } catch (err) {
    if (mode === "backend") {
      if (err instanceof ApiError && err.status === 404) {
        return {
          state: "empty",
          mode,
          view: null,
          error: {
            kind: "project_not_found",
            message: "Проект не найден.",
            status: 404,
            actionHint: "Проверьте ID в Workspace.",
          },
          projectName: null,
        };
      }
      return {
        state: "error",
        mode,
        view: null,
        error: normalizeVerdictError(err),
        projectName: null,
      };
    }
    // hybrid: may still show local preview
  }

  let inputSignals: VerdictInputSignal[] = [];
  try {
    const summaries = await fetchBusinessCampaignSummaries(projectId);
    const primary = summaries.find((s) => s.campaign.status === "active") ?? summaries[0];
    if (primary) {
      try {
        const report = await fetchBusinessCampaignSupervisorReport(
          projectId,
          primary.campaign.id,
        );
        inputSignals = mapSupervisorToInputSignals(report);
        // Inject CC next_action as operational recommendation signal
        if (primary.next_action_type && primary.next_action_type !== "none") {
          inputSignals.unshift({
            id: "sig_cc_next",
            role: "operational_recommendation",
            title: `CC next_action: ${primary.next_action_type}`,
            description: "Campaign Control Center operational recommendation",
            sourceObject: "CampaignControlCenter.next_action",
            category: "control_center_next_action",
            origin: "backend",
            disclaimer:
              "ControlCenter.next_action → OperationalRecommendation. Не BusinessVerdict.",
          });
        }
      } catch {
        /* optional */
      }
    }
  } catch {
    /* optional campaigns */
  }

  if (mode === "backend") {
    try {
      const list = await fetchBusinessVerdicts(projectId);
      if (!list.length) {
        return {
          state: "empty",
          mode,
          view: {
            verdict: null,
            versions: [],
            originMeta: durableBackendVerdictOrigin(false),
            inputSignals,
            strategyEligibility: eligibilityFor(null, durableBackendVerdictOrigin(false)),
            verdictReviewIsNotExecutionApproval: true,
            autoUploadDisabled: true,
            noBackendVerdictEntity: false,
          },
          error: null,
          projectName,
        };
      }
      let latestDto = list[0];
      try {
        latestDto = await fetchLatestBusinessVerdict(projectId);
      } catch {
        /* use list[0] */
      }
      const mapped = mapBackendVerdictToProductAlpha(
        latestDto,
        projectName ?? latestDto.project_id,
      );
      const versions = list.map((v) =>
        mapBackendVerdictToProductAlpha(v, projectName ?? v.project_id),
      );
      const originMeta = durableBackendVerdictOrigin(
        latestDto.lifecycle_status === "approved",
      );
      return {
        state: "success",
        mode,
        view: {
          verdict: mapped,
          versions,
          originMeta,
          inputSignals,
          strategyEligibility: mapBackendStrategyEligibility(latestDto),
          verdictReviewIsNotExecutionApproval: true,
          autoUploadDisabled: true,
          noBackendVerdictEntity: false,
        },
        error: null,
        projectName,
      };
    } catch (err) {
      return {
        state: "error",
        mode,
        view: null,
        error: normalizeBusinessVerdictError(err),
        projectName,
      };
    }
  }

  // HYBRID: backend approved authoritative when present; else labelled local preview
  try {
    const list = await fetchBusinessVerdicts(projectId);
    const approved = list.find((v) => v.lifecycle_status === "approved");
    if (approved) {
      const mapped = mapBackendVerdictToProductAlpha(
        approved,
        projectName ?? approved.project_id,
      );
      return {
        state: "success",
        mode,
        view: {
          verdict: mapped,
          versions: list.map((v) =>
            mapBackendVerdictToProductAlpha(v, projectName ?? v.project_id),
          ),
          originMeta: durableBackendVerdictOrigin(true),
          inputSignals,
          strategyEligibility: mapBackendStrategyEligibility(approved),
          verdictReviewIsNotExecutionApproval: true,
          autoUploadDisabled: true,
          noBackendVerdictEntity: false,
        },
        error: null,
        projectName,
      };
    }
  } catch {
    /* fall through to local preview */
  }

  // HYBRID: local deterministic preview labelled; never claim backend persistence
  const existing = getCurrentVerdict(projectId);
  const verdict =
    existing ??
    (ensure ? prepareVerdictForProject(projectId) : null);
  if (verdict && projectName && verdict.projectName !== projectName) {
    // display name overlay only — do not mutate stored verdict silently as backend-approved
  }
  const originMeta = deterministicLocalPreviewOrigin();
  return {
    state: verdict ? "success" : "empty",
    mode,
    view: {
      verdict: verdict
        ? {
            ...verdict,
            projectName: projectName ?? verdict.projectName,
            localMockLabel: "Локальный предварительный вердикт · не persisted / not evidence-verified",
          }
        : null,
      versions: listVerdictVersions(projectId),
      originMeta,
      inputSignals,
      strategyEligibility: eligibilityFor(verdict, originMeta),
      verdictReviewIsNotExecutionApproval: true,
      autoUploadDisabled: true,
      noBackendVerdictEntity: true,
    },
    error: null,
    projectName,
  };
}

/** Explicit user action required later — I4 forbids auto-upload. */
export function canAutoUploadLocalVerdictToBackend(): false {
  return false;
}

export function localVerdictReconciliationPolicy() {
  const importPolicy = localVerdictImportPolicy();
  return {
    keyPattern: "marketsynth.product_alpha.verdict.v1.{projectId}",
    mockMode: "untouched",
    hybridMode: "local_preview_labelled",
    backendMode: "backend_verdicts_only_no_mock_fallback",
    autoUpload: importPolicy.autoUpload,
    silentOverwrite: false,
    deleteLocalInI4: false,
    approvedBackendAuthoritative: importPolicy.backendApprovedAuthoritative,
    note: "P0.5 durable BusinessVerdict — local import only via explicit draft conversion.",
  } as const;
}
