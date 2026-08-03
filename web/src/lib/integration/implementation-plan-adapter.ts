/**
 * I6 — Implementation Plan Workspace load (Option B, read-only handoff).
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import { fetchMarketingPlans } from "@/lib/api/endpoints/marketing-plans";
import {
  fetchImplementationPlans,
  fetchLatestImplementationPlan,
} from "@/lib/api/endpoints/implementation-plans";
import { fetchProject } from "@/lib/api/endpoints/projects";
import type { LoadState } from "@/lib/integration/contracts";
import {
  implementationPlanApprovalCreatesMarketingPlanApproval,
  marketingPlanApprovalCreatesExecutionApproval,
} from "@/lib/integration/approval-boundary";
import {
  normalizeHandoffError,
  writeBlockedNoCreateApi,
  type HandoffError,
} from "@/lib/integration/handoff-errors";
import {
  buildMarketingPlanHandoffPreview,
  i6WritePolicy,
  implementationPlanEqualsMarketingPlan,
  type HandoffPreview,
} from "@/lib/integration/implementation-marketing-plan-mapping";
import { mapBackendImplementationPlanToProductAlpha } from "@/lib/integration/implementation-plan-api-adapter";
import { normalizeImplementationPlanError } from "@/lib/integration/implementation-plan-errors";
import { localImplementationPlanImportPolicy } from "@/lib/integration/implementation-plan-sync";
import {
  durableBackendImplementationOrigin,
  localImplementationOrigin,
  mockImplementationOrigin,
  unsupportedImplementationBackendOrigin,
  type ImplementationPlanOriginMeta,
} from "@/lib/integration/implementation-plan-origin";
import {
  mapMarketingPlanToOpsView,
  selectRelatedMarketingPlans,
  type MarketingPlanOpsView,
} from "@/lib/integration/marketing-plan-adapter";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import { preparePlanForProject } from "@/lib/implementation-plan/mock-plans";
import {
  getCurrentPlan,
  listPlanVersions,
} from "@/lib/implementation-plan/storage";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";

export type ImplementationWorkspaceIntegrationView = {
  plan: ImplementationPlan | null;
  versions: ImplementationPlan[];
  origin: ImplementationPlanOriginMeta;
  relatedPlans: MarketingPlanOpsView[];
  primaryPlan: MarketingPlanOpsView | null;
  planSelectionRule: string;
  handoffPreview: HandoffPreview | null;
  writePolicy: ReturnType<typeof i6WritePolicy>;
  writeBlocker: HandoffError;
  equalsMarketingPlan: false;
  createsCampaign: false;
  createsAgentRun: false;
  createsExecutionApproval: false;
  localApprovalCreatesPlanApproval: false;
  planApprovalCreatesExecutionApproval: false;
  conversionStatesNote: string;
};

export type ImplementationLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  view: ImplementationWorkspaceIntegrationView | null;
  error: HandoffError | null;
  projectName: string | null;
};

/**
 * Load Implementation Plan composition. Never converts / executes.
 */
export async function loadImplementationPlanWorkspace(
  projectId: string,
): Promise<ImplementationLoadResult> {
  const mode = getIntegrationMode();
  const writePolicy = i6WritePolicy();
  const writeBlocker = writeBlockedNoCreateApi();
  void implementationPlanEqualsMarketingPlan();
  void implementationPlanApprovalCreatesMarketingPlanApproval();
  void marketingPlanApprovalCreatesExecutionApproval();

  const baseFlags = {
    equalsMarketingPlan: false as const,
    createsCampaign: false as const,
    createsAgentRun: false as const,
    createsExecutionApproval: false as const,
    localApprovalCreatesPlanApproval: false as const,
    planApprovalCreatesExecutionApproval: false as const,
    conversionStatesNote:
      "States not_linked|preview_ready|creating|linked_draft|stale|conflict|failed — FE only; write blocked in I6.",
  };

  if (mode === "mock") {
    const plan = preparePlanForProject(projectId);
    return {
      state: "success",
      mode,
      view: {
        plan,
        versions: listPlanVersions(projectId),
        origin: mockImplementationOrigin(),
        relatedPlans: [],
        primaryPlan: null,
        planSelectionRule: "mock — no MarketingPlan fetch",
        handoffPreview: buildMarketingPlanHandoffPreview(plan),
        writePolicy,
        writeBlocker,
        ...baseFlags,
      },
      error: null,
      projectName: plan.projectName,
    };
  }

  if (!canUseBackendApi()) {
    return {
      state: "unauthorized",
      mode,
      view: null,
      error: normalizeHandoffError(new ApiError("unauthorized", 401, null)),
      projectName: null,
    };
  }

  let projectName: string | null = null;
  try {
    const project = await fetchProject(projectId);
    projectName = project.name;
  } catch (err) {
    return {
      state: err instanceof ApiError && err.status === 404 ? "empty" : "error",
      mode,
      view: null,
      error:
        err instanceof ApiError && err.status === 404
          ? {
              kind: "project_not_found",
              message: "Проект не найден.",
              status: 404,
              actionHint: "Проверьте Workspace.",
            }
          : normalizeHandoffError(err),
      projectName: null,
    };
  }

  let relatedPlans: MarketingPlanOpsView[] = [];
  let primaryPlan: MarketingPlanOpsView | null = null;
  let planSelectionRule = "no plans";
  let planErr: HandoffError | null = null;
  try {
    const plans = await fetchMarketingPlans(projectId, { limit: 50 });
    const sel = selectRelatedMarketingPlans(plans);
    relatedPlans = sel.related.map(mapMarketingPlanToOpsView);
    primaryPlan = sel.primary ? mapMarketingPlanToOpsView(sel.primary) : null;
    planSelectionRule = sel.rule;
  } catch (err) {
    planErr = normalizeHandoffError(err);
  }

  if (mode === "backend") {
    void localImplementationPlanImportPolicy();
    try {
      const latest = await fetchLatestImplementationPlan(projectId);
      const mapped = mapBackendImplementationPlanToProductAlpha(
        latest,
        projectName ?? latest.project_id,
      );
      let versions: ImplementationPlan[] = [mapped];
      try {
        const all = await fetchImplementationPlans(projectId, { limit: 50 });
        versions = all.map((p) =>
          mapBackendImplementationPlanToProductAlpha(p, projectName ?? p.project_id),
        );
      } catch {
        /* keep latest only */
      }
      return {
        state: "success",
        mode,
        view: {
          plan: mapped,
          versions,
          origin: durableBackendImplementationOrigin(true),
          relatedPlans,
          primaryPlan,
          planSelectionRule,
          handoffPreview: buildMarketingPlanHandoffPreview(mapped),
          writePolicy,
          writeBlocker,
          ...baseFlags,
        },
        error: planErr,
        projectName,
      };
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        return {
          state: "empty",
          mode,
          view: {
            plan: null,
            versions: [],
            origin: durableBackendImplementationOrigin(false),
            relatedPlans,
            primaryPlan,
            planSelectionRule,
            handoffPreview: null,
            writePolicy,
            writeBlocker,
            ...baseFlags,
          },
          error: normalizeImplementationPlanError(err) as unknown as HandoffError,
          projectName,
        };
      }
      return {
        state: "error",
        mode,
        view: {
          plan: null,
          versions: [],
          origin: unsupportedImplementationBackendOrigin(),
          relatedPlans,
          primaryPlan,
          planSelectionRule,
          handoffPreview: null,
          writePolicy,
          writeBlocker,
          ...baseFlags,
        },
        error: normalizeImplementationPlanError(err) as unknown as HandoffError,
        projectName,
      };
    }
  }

  // hybrid
  let plan = getCurrentPlan(projectId);
  try {
    if (!plan) plan = preparePlanForProject(projectId);
  } catch (e) {
    return {
      state: "empty",
      mode,
      view: null,
      error: {
        kind: "implementation_plan_not_available",
        message: e instanceof Error ? e.message : "Implementation Plan unavailable",
        status: null,
        actionHint: "Проверьте Strategy / Verdict eligibility.",
      },
      projectName,
    };
  }

  return {
    state: "success",
    mode,
    view: {
      plan: plan
        ? {
            ...plan,
            projectName: projectName ?? plan.projectName,
            localMockLabel:
              "Локальный Implementation Plan · MarketingPlan — ops context only · write blocked",
          }
        : null,
      versions: listPlanVersions(projectId),
      origin: localImplementationOrigin(),
      relatedPlans,
      primaryPlan,
      planSelectionRule,
      handoffPreview: plan ? buildMarketingPlanHandoffPreview(plan) : null,
      writePolicy,
      writeBlocker,
      ...baseFlags,
    },
    error: planErr,
    projectName,
  };
}

export function futureExecutionChainDocumented(): string[] {
  return [
    "Implementation Plan",
    "MarketingPlan draft (future handoff API)",
    "MarketingPlan review/approval",
    "specialist work",
    "execution intent",
    "execution readiness",
    "execution approval",
    "provider execution",
    "verification",
    "evidence",
    "outcome",
  ];
}
