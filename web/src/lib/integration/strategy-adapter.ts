/**
 * I5 — Strategy Workspace load (Option B).
 *
 * Strategy SoT = labelled local/mock MarketingStrategy (Product Alpha).
 * MarketingPlan SoT = backend ops execution spine (separate panel).
 * Verdict eligibility (I4) cannot be bypassed by plan presence.
 * Read-only vs MarketingPlan — no dual-write, no campaign/execution side effects.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  fetchLatestBusinessVerdict,
} from "@/lib/api/endpoints/business-verdicts";
import {
  fetchLatestMarketingStrategy,
  fetchMarketingStrategies,
} from "@/lib/api/endpoints/marketing-strategies";
import { fetchMarketingPlans } from "@/lib/api/endpoints/marketing-plans";
import { fetchProject } from "@/lib/api/endpoints/projects";
import type { LoadState } from "@/lib/integration/contracts";
import { mapBackendVerdictToProductAlpha } from "@/lib/integration/business-verdict-api-adapter";
import { mapBackendStrategyToProductAlpha } from "@/lib/integration/marketing-strategy-api-adapter";
import { localStrategyImportPolicy } from "@/lib/integration/marketing-strategy-sync";
import {
  mapMarketingPlanToOpsView,
  selectRelatedMarketingPlans,
  writePolicyI5,
  type MarketingPlanOpsView,
} from "@/lib/integration/marketing-plan-adapter";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  resolveStrategyEligibility,
  type StrategyEligibilityResult,
} from "@/lib/integration/strategy-eligibility";
import {
  invalidEligibilityError,
  normalizeStrategyError,
  semanticConflictPlanIsNotStrategy,
  type StrategyError,
} from "@/lib/integration/strategy-errors";
import {
  backendOpsPlanContextOrigin,
  durableBackendStrategyOrigin,
  localStrategyPreviewOrigin,
  mockStrategyOrigin,
  type StrategyOriginMeta,
} from "@/lib/integration/strategy-origin";
import {
  defaultSectionAuthorities,
  marketingPlanDoesNotEqualStrategy,
  type StrategySectionAuthority,
} from "@/lib/integration/strategy-plan-mapping";
import {
  deterministicLocalPreviewOrigin,
  durableBackendVerdictOrigin,
  mockVerdictOrigin,
} from "@/lib/integration/verdict-origin";
import { getCurrentVerdict } from "@/lib/verdict/storage";
import { prepareVerdictForProject } from "@/lib/verdict/mock-verdicts";
import type { BusinessVerdict } from "@/lib/verdict/types";
import { prepareStrategyForProject } from "@/lib/strategy/mock-strategies";
import {
  listStrategyVersions,
  getCurrentStrategy,
} from "@/lib/strategy/storage";
import type { MarketingStrategy } from "@/lib/strategy/types";

export type StrategyWorkspaceIntegrationView = {
  strategy: MarketingStrategy | null;
  versions: MarketingStrategy[];
  strategyOrigin: StrategyOriginMeta;
  sectionAuthorities: StrategySectionAuthority[];
  relatedPlans: MarketingPlanOpsView[];
  primaryPlan: MarketingPlanOpsView | null;
  planSelectionRule: string;
  planContextOrigin: StrategyOriginMeta | null;
  eligibility: StrategyEligibilityResult;
  semanticNotice: StrategyError | null;
  writePolicy: ReturnType<typeof writePolicyI5>;
  marketingPlanEqualsStrategy: false;
  createsCampaign: false;
  triggersExecution: false;
  autoUploadDisabled: true;
};

export type StrategyLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  view: StrategyWorkspaceIntegrationView | null;
  error: StrategyError | null;
  projectName: string | null;
  legacyPlanOnBlockedVerdict: boolean;
};

function resolveVerdictForMode(
  projectId: string,
  mode: IntegrationMode,
): BusinessVerdict | null {
  if (mode === "backend") {
    return null; // loaded async from backend below
  }
  return getCurrentVerdict(projectId) ?? prepareVerdictForProject(projectId);
}

function originForVerdictMeta(mode: IntegrationMode) {
  if (mode === "mock") return mockVerdictOrigin();
  if (mode === "backend") return durableBackendVerdictOrigin(false);
  return deterministicLocalPreviewOrigin();
}

/**
 * Load Strategy Workspace composition.
 * Does not create MarketingPlan, Campaign, or Execution.
 */
export async function loadStrategyWorkspaceView(
  projectId: string,
): Promise<StrategyLoadResult> {
  const mode = getIntegrationMode();
  const writePolicy = writePolicyI5();

  const verdict = resolveVerdictForMode(projectId, mode);
  const eligibility = resolveStrategyEligibility({
    verdictType: verdict?.type ?? null,
    verdictStatus: verdict?.status ?? null,
    origin: originForVerdictMeta(mode),
  });

  if (mode === "mock") {
    if (!eligibility.allow) {
      return {
        state: "empty",
        mode,
        view: null,
        error: invalidEligibilityError(eligibility.reason),
        projectName: null,
        legacyPlanOnBlockedVerdict: false,
      };
    }
    const strategy = prepareStrategyForProject(projectId);
    return {
      state: "success",
      mode,
      view: {
        strategy,
        versions: listStrategyVersions(projectId),
        strategyOrigin: mockStrategyOrigin(),
        sectionAuthorities: defaultSectionAuthorities("mock"),
        relatedPlans: [],
        primaryPlan: null,
        planSelectionRule: "mock — no MarketingPlan fetch",
        planContextOrigin: null,
        eligibility,
        semanticNotice: null,
        writePolicy,
        marketingPlanEqualsStrategy: false,
        createsCampaign: false,
        triggersExecution: false,
        autoUploadDisabled: true,
      },
      error: null,
      projectName: strategy.projectName,
      legacyPlanOnBlockedVerdict: false,
    };
  }

  if (!canUseBackendApi()) {
    return {
      state: "unauthorized",
      mode,
      view: null,
      error: normalizeStrategyError(new ApiError("unauthorized", 401, null)),
      projectName: null,
      legacyPlanOnBlockedVerdict: false,
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
          : normalizeStrategyError(err),
      projectName: null,
      legacyPlanOnBlockedVerdict: false,
    };
  }

  let relatedPlans: MarketingPlanOpsView[] = [];
  let primaryPlan: MarketingPlanOpsView | null = null;
  let planSelectionRule = "no plans";
  let planFetchError: StrategyError | null = null;

  try {
    const plans = await fetchMarketingPlans(projectId, { limit: 50 });
    const selected = selectRelatedMarketingPlans(plans);
    relatedPlans = selected.related.map(mapMarketingPlanToOpsView);
    primaryPlan = selected.primary ? mapMarketingPlanToOpsView(selected.primary) : null;
    planSelectionRule = selected.rule;
  } catch (err) {
    planFetchError = normalizeStrategyError(err);
  }

  const legacyPlanOnBlockedVerdict = !eligibility.allow && relatedPlans.length > 0;

  // Resolve backend verdict for backend/hybrid eligibility
  let backendVerdict: BusinessVerdict | null = verdict;
  if (mode === "backend" || mode === "hybrid") {
    try {
      const latestV = await fetchLatestBusinessVerdict(projectId);
      backendVerdict = mapBackendVerdictToProductAlpha(
        latestV,
        projectName ?? latestV.project_id,
      );
    } catch {
      /* keep local/null */
    }
  }

  const effectiveEligibility = resolveStrategyEligibility({
    verdictType: backendVerdict?.type ?? verdict?.type ?? null,
    verdictStatus: backendVerdict?.status ?? verdict?.status ?? null,
    origin:
      mode === "backend"
        ? durableBackendVerdictOrigin(backendVerdict?.status === "approved")
        : originForVerdictMeta(mode),
  });

  if (!effectiveEligibility.allow) {
    return {
      state: "empty",
      mode,
      view: {
        strategy: null,
        versions: [],
        strategyOrigin:
          mode === "backend"
            ? durableBackendStrategyOrigin(false)
            : localStrategyPreviewOrigin(),
        sectionAuthorities: defaultSectionAuthorities(mode === "backend" ? "backend" : "hybrid"),
        relatedPlans,
        primaryPlan,
        planSelectionRule,
        planContextOrigin: primaryPlan ? backendOpsPlanContextOrigin() : null,
        eligibility: effectiveEligibility,
        semanticNotice: legacyPlanOnBlockedVerdict
          ? {
              kind: "semantic_conflict",
              message:
                "MarketingPlan существует при blocked Verdict (NO_GO / INSUFFICIENT_DATA / draft). Plan ≠ Strategy eligibility.",
              status: null,
              actionHint: "Показать как legacy ops plan; не открывать Strategy.",
            }
          : invalidEligibilityError(effectiveEligibility.reason),
        writePolicy,
        marketingPlanEqualsStrategy: false,
        createsCampaign: false,
        triggersExecution: false,
        autoUploadDisabled: true,
      },
      error: invalidEligibilityError(effectiveEligibility.reason),
      projectName,
      legacyPlanOnBlockedVerdict: !effectiveEligibility.allow && relatedPlans.length > 0,
    };
  }

  if (mode === "backend") {
    try {
      const list = await fetchMarketingStrategies(projectId);
      if (!list.length) {
        return {
          state: "empty",
          mode,
          view: {
            strategy: null,
            versions: [],
            strategyOrigin: durableBackendStrategyOrigin(false),
            sectionAuthorities: defaultSectionAuthorities("backend"),
            relatedPlans,
            primaryPlan,
            planSelectionRule,
            planContextOrigin: primaryPlan ? backendOpsPlanContextOrigin() : null,
            eligibility: effectiveEligibility,
            semanticNotice: semanticConflictPlanIsNotStrategy(),
            writePolicy,
            marketingPlanEqualsStrategy: false,
            createsCampaign: false,
            triggersExecution: false,
            autoUploadDisabled: true,
          },
          error: null,
          projectName,
          legacyPlanOnBlockedVerdict: false,
        };
      }
      let latest = list[0];
      try {
        latest = await fetchLatestMarketingStrategy(projectId);
      } catch {
        /* use list[0] */
      }
      const mapped = mapBackendStrategyToProductAlpha(
        latest,
        projectName ?? latest.project_id,
      );
      return {
        state: "success",
        mode,
        view: {
          strategy: mapped,
          versions: list.map((s) =>
            mapBackendStrategyToProductAlpha(s, projectName ?? s.project_id),
          ),
          strategyOrigin: durableBackendStrategyOrigin(
            latest.lifecycle_status === "approved",
          ),
          sectionAuthorities: defaultSectionAuthorities("backend"),
          relatedPlans,
          primaryPlan,
          planSelectionRule,
          planContextOrigin: primaryPlan ? backendOpsPlanContextOrigin() : null,
          eligibility: effectiveEligibility,
          semanticNotice: semanticConflictPlanIsNotStrategy(),
          writePolicy,
          marketingPlanEqualsStrategy: false,
          createsCampaign: false,
          triggersExecution: false,
          autoUploadDisabled: true,
        },
        error: planFetchError,
        projectName,
        legacyPlanOnBlockedVerdict: false,
      };
    } catch (err) {
      return {
        state: "error",
        mode,
        view: null,
        error: normalizeStrategyError(err),
        projectName,
        legacyPlanOnBlockedVerdict: false,
      };
    }
  }

  // HYBRID: backend approved Strategy authoritative when present
  try {
    const list = await fetchMarketingStrategies(projectId);
    const approved = list.find((s) => s.lifecycle_status === "approved");
    if (approved) {
      const mapped = mapBackendStrategyToProductAlpha(
        approved,
        projectName ?? approved.project_id,
      );
      return {
        state: "success",
        mode,
        view: {
          strategy: mapped,
          versions: list.map((s) =>
            mapBackendStrategyToProductAlpha(s, projectName ?? s.project_id),
          ),
          strategyOrigin: durableBackendStrategyOrigin(true),
          sectionAuthorities: defaultSectionAuthorities("hybrid"),
          relatedPlans,
          primaryPlan,
          planSelectionRule,
          planContextOrigin: primaryPlan ? backendOpsPlanContextOrigin() : null,
          eligibility: effectiveEligibility,
          semanticNotice: semanticConflictPlanIsNotStrategy(),
          writePolicy,
          marketingPlanEqualsStrategy: false,
          createsCampaign: false,
          triggersExecution: false,
          autoUploadDisabled: true,
        },
        error: planFetchError,
        projectName,
        legacyPlanOnBlockedVerdict: false,
      };
    }
  } catch {
    /* fall through to local */
  }

  // HYBRID: local strategic preview + backend ops plans
  const existing = getCurrentStrategy(projectId);
  let strategy: MarketingStrategy | null = existing;
  try {
    if (!strategy) strategy = prepareStrategyForProject(projectId);
  } catch (e) {
    return {
      state: "empty",
      mode,
      view: null,
      error: invalidEligibilityError(e instanceof Error ? e.message : "Strategy blocked"),
      projectName,
      legacyPlanOnBlockedVerdict: false,
    };
  }

  void marketingPlanDoesNotEqualStrategy();

  return {
    state: "success",
    mode,
    view: {
      strategy: strategy
        ? {
            ...strategy,
            projectName: projectName ?? strategy.projectName,
            localMockLabel:
              "Локальный стратегический preview · MarketingPlan — только ops context",
          }
        : null,
      versions: listStrategyVersions(projectId),
      strategyOrigin: localStrategyPreviewOrigin(),
      sectionAuthorities: defaultSectionAuthorities("hybrid"),
      relatedPlans,
      primaryPlan,
      planSelectionRule,
      planContextOrigin: primaryPlan ? backendOpsPlanContextOrigin() : null,
      eligibility: effectiveEligibility,
      semanticNotice: semanticConflictPlanIsNotStrategy(),
      writePolicy,
      marketingPlanEqualsStrategy: false,
      createsCampaign: false,
      triggersExecution: false,
      autoUploadDisabled: true,
    },
    error: planFetchError,
    projectName,
    legacyPlanOnBlockedVerdict: false,
  };
}

export function localStrategyReconciliationPolicy() {
  const importPolicy = localStrategyImportPolicy();
  return {
    keyPattern: "marketsynth.product_alpha.strategy.v1.{projectId}",
    autoUpload: importPolicy.autoUpload,
    silentOverwrite: false,
    dualWriteToMarketingPlan: false,
    linkFields: [
      "backendMarketingPlanId",
      "backendMarketingPlanVersion",
      "syncState",
      "linkedAt",
      "mappingFingerprint",
      "lastConflict",
      "localStrategyVersion",
    ],
    note: "P0.6 durable MarketingStrategy — local import only via explicit draft conversion.",
  } as const;
}
