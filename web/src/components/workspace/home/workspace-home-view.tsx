"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import { AgencyAnalysisStages } from "@/components/workspace/home/agency-analysis-stages";
import { ResearchProgressPanel } from "@/components/workspace/home/research-progress-panel";
import { AgencyResultActions } from "@/components/workspace/home/agency-result-actions";
import { AnalysisIntakePanel } from "@/components/workspace/home/analysis-intake-panel";
import { CustomerServiceUnavailable } from "@/components/workspace/home/customer-service-unavailable";
import { HydrationRecoveryCard } from "@/components/workspace/home/hydration-recovery-card";
import { IntentStartPanel } from "@/components/workspace/home/intent-start-panel";
import { CanonicalCommercialEntryPanel } from "@/components/workspace/home/canonical-commercial-entry";
import { isHomeDeveloperMode } from "@/lib/home/developer-mode";
import {
  canonicalIntakeHref,
  toCanonicalPublicNavigationTarget,
} from "@/lib/routes/commercial-surface";
import {
  loadWorkspaceBootDestination,
  workspaceUrlsEquivalent,
  type WorkspaceBootError,
} from "@/lib/workspace/workspace-boot";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CANONICAL_COMMERCIAL_ROUTES } from "@/lib/routes/commercial-routes";
import { HomeRecentProjects } from "@/components/workspace/home/home-recent-projects";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { createUserRequest } from "@/lib/api/endpoints/user-requests";
import {
  confirmAnalysisContext,
  createAnalysisContextDraft,
  createAnalysisContextDraftResilient,
  editAnalysisContext,
  getCurrentAnalysisContext,
  startNewAnalysisContext,
  type AnalysisContextFields,
  type AnalysisContextRecord,
} from "@/lib/api/endpoints/analysis-contexts";
import { createProject, fetchProject, fetchProjects } from "@/lib/api/endpoints/projects";
import { buildLocalDraftContext, isLocalDraftContext } from "@/lib/biv/local-draft-context";
import { workspaceProjectLifecycleLabel } from "@/lib/biv/biv-lifecycle-labels";
import { mergeContextSpecificity } from "@/lib/biv/analysis-context-specificity";
import {
  clearActiveResearchSession,
  loadActiveResearchSession,
  persistActiveResearchSession,
} from "@/lib/biv/active-research-session";
import {
  loadLastCompletedResearch,
  persistLastCompletedResearch,
} from "@/lib/biv/last-completed-research";
import { PartialResearchPanel } from "@/components/workspace/home/partial-research-panel";
import { tryHydrateTerminalPartialRun } from "@/lib/biv/hydrate-terminal-partial-run";
import {
  clearTerminalPartialResearch,
  loadTerminalPartialResearch,
  persistTerminalPartialResearch,
} from "@/lib/biv/terminal-partial-research";
import {
  pickAnalysisProjectSnapshot,
  type ProjectContextSnapshot,
} from "@/lib/biv/pick-analysis-project";
import {
  mapPollingAuthErrorCode,
  resolveContextApplyAction,
  shouldBlockProjectHydrate,
  shouldShowIntakeForm,
} from "@/lib/biv/research-hydration-guard";
import { deriveBivWorkspaceViewModel } from "@/lib/biv/biv-workspace-view-model";
import {
  planRecoveryContinue,
  shouldOpenFormAfterConfirmError,
} from "@/lib/biv/recovery-continue";
import { downloadCustomerReportFile } from "@/lib/biv/customer-report-export";
import type { ResearchUiState } from "@/lib/biv/research-ui-state";
import {
  buildResearchIdempotencyKey,
  buildRerunIdempotencyKey,
  fetchProjectLatestBivRun,
  getBusinessIdeaValidation,
  getBusinessIdeaValidationProgress,
  getBusinessIdeaValidationRun,
  getBusinessIdeaValidationRunProgress,
  getProjectBusinessIdeaValidation,
  startBusinessIdeaValidationRun,
} from "@/lib/api/endpoints/business-idea-validation";
import {
  isPartialResearchOutput,
  isResearchTerminal,
  type BusinessIdeaValidationRunResponse,
} from "@/lib/api/types/business-idea-validation";
import {
  isActiveRunStatus,
  pollResearchRunUntilTerminal,
} from "@/lib/biv/research-run-polling";
import { getLaunchPackJourney, type LaunchPackJourneyHydration } from "@/lib/api/endpoints/launch-pack";
import { ApiError } from "@/lib/api/client";
import type { BackendUserRequestDto } from "@/lib/api/types/user-requests";
import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import { CommercialErrorBoundary } from "@/components/workspace/home/commercial-error-boundary";
import { BusinessValidationResultCard } from "@/components/workspace/home/business-validation-result-card";
import { LaunchPackDecisionPanel } from "@/components/workspace/home/launch-pack-decision-panel";
import { ContentDirectorPanel } from "@/components/content-director/content-director-panel";
import { ProjectCommandCenter } from "@/components/workspace/project/project-command-center";
import { HomeCreativeCapabilityTeaser } from "@/components/workspace/home/home-creative-capability-teaser";
import { ResearchFailurePanel } from "@/components/workspace/home/research-failure-panel";
import {
  mapCommercialError,
  type CommercialErrorView,
} from "@/lib/errors/commercial-error-mapper";
import {
  hasValidVerdictForLaunchPack,
  intakeFieldsFromGaps,
  customerGapItems,
} from "@/lib/biv/research-gap-presentation";
import {
  buildRunningStages,
  buildStagesFromBackendProgress,
  buildStagesFromValidationOutput,
  mapValidationToAgencyVerdict,
  type AgencyStage,
  type AgencyVerdictView,
} from "@/lib/home/agency-analysis-flow";
import {
  navigateToAssistant,
  resolveFreeTextTask,
  resolveIntentSelection,
  saveIntentTask,
} from "@/lib/home/intent-navigation";
import type { UserIntent, UserSubIntent } from "@/lib/home/user-intent-catalog";
import { useLocale } from "@/lib/i18n";
import { useApiAvailability } from "@/lib/hooks/use-api-availability";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  enrichWorkspaceProjectsWithBiv,
} from "@/lib/integration/enrich-workspace-projects-biv";
import { loadWorkspaceProjects } from "@/lib/integration/load-workspace";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";

type AgencyPhase = "intake" | "analyzing" | "verdict";
type IntakeView = "start" | "recovery" | "form" | "confirmed";

function commercialErrorMessage(
  err: unknown,
  t: (key: string) => string,
  context: "research" | "general" = "general",
): string {
  return mapCommercialError(err, t, context).message;
}

type ReportSnapshot = {
  output: BusinessIdeaValidationOutput;
  verdict: AgencyVerdictView;
  stages: AgencyStage[];
};

function isAuthApiError(err: unknown): boolean {
  if (!(err instanceof ApiError) || err.status !== 401) {
    return false;
  }
  return mapPollingAuthErrorCode(err.status, err.errorCode ?? err.message) !== null;
}

type WorkspaceHomeViewProps = {
  initialProjectId?: string | null;
};

/** Canonical Commercial Home — intent-driven entry at /workspace. */
export function WorkspaceHomeView(props: WorkspaceHomeViewProps = {}) {
  const { initialProjectId = null } = props;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryProjectId =
    searchParams.get("project") ?? searchParams.get("projectId") ?? initialProjectId;
  const contentDirectorView = searchParams.get("view") === "content_director";
  /**
   * WORKSPACE-BOOT-RECOVERY-02: bare /workspace boot without hard navigation.
   * When URL already has project → skip boot; render PCC.
   * Single-project: bind inline id + soft router.replace once (no self-redirect loop).
   */
  const needsWorkspaceBoot = !queryProjectId && !contentDirectorView;
  const [bootProjectId, setBootProjectId] = useState<string | null>(null);
  const [bootPhase, setBootPhase] = useState<"idle" | "loading" | "error" | "done">(
    needsWorkspaceBoot ? "loading" : "done",
  );
  const [bootError, setBootError] = useState<WorkspaceBootError | null>(null);
  const [bootRetryKey, setBootRetryKey] = useState(0);
  const bootNavigatedRef = useRef(false);
  const effectiveProjectId = queryProjectId ?? bootProjectId;

  const searchKey = searchParams.toString();
  useEffect(() => {
    if (!needsWorkspaceBoot) {
      setBootPhase("done");
      setBootError(null);
      bootNavigatedRef.current = false;
      return;
    }
    let cancelled = false;
    bootNavigatedRef.current = false;
    setBootPhase("loading");
    setBootError(null);
    setBootProjectId(null);

    const ac = new AbortController();
    void loadWorkspaceBootDestination({ signal: ac.signal }).then((result) => {
      if (cancelled) return;
      if (result.status === "error") {
        setBootError(result);
        setBootPhase("error");
        if (result.kind === "unauthorized") {
          router.replace(
            `${CANONICAL_COMMERCIAL_ROUTES.login}?next=${encodeURIComponent("/workspace")}`,
          );
        }
        return;
      }
      if (result.status === "single_project") {
        setBootProjectId(result.projectId);
        setBootPhase("done");
        const current = `${pathname}${searchKey ? `?${searchKey}` : ""}`;
        if (
          !bootNavigatedRef.current &&
          !workspaceUrlsEquivalent(current, result.href)
        ) {
          bootNavigatedRef.current = true;
          router.replace(result.href);
        }
        return;
      }
      setBootPhase("done");
      const current = `${pathname}${searchKey ? `?${searchKey}` : ""}`;
      if (
        !bootNavigatedRef.current &&
        !workspaceUrlsEquivalent(current, result.href)
      ) {
        bootNavigatedRef.current = true;
        router.replace(result.href);
      }
    });

    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [needsWorkspaceBoot, bootRetryKey, pathname, router, searchKey]);

  useAuth();
  const { t, locale } = useLocale();
  const { status: apiStatus, diagnostics } = useApiAvailability();
  const apiUnavailable = apiStatus === "unavailable";
  const [developerMode, setDeveloperMode] = useState(false);

  useEffect(() => {
    setDeveloperMode(isHomeDeveloperMode());
  }, [pathname]);

  const [draftText, setDraftText] = useState("");
  const [phase, setPhase] = useState<AgencyPhase>("intake");
  const [intakeView, setIntakeView] = useState<IntakeView>("start");
  const [stages, setStages] = useState<AgencyStage[]>([]);
  const [verdict, setVerdict] = useState<AgencyVerdictView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<BusinessIdeaValidationOutput | null>(null);
  const [journey, setJourney] = useState<LaunchPackJourneyHydration | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [analysisContext, setAnalysisContext] = useState<AnalysisContextRecord | null>(null);
  const [confirmedContext, setConfirmedContext] = useState<AnalysisContextRecord | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeUserRequestId, setActiveUserRequestId] = useState<string | null>(null);
  const [highlightIntakeFields, setHighlightIntakeFields] = useState<string[]>([]);
  const [rerunStarting, setRerunStarting] = useState(false);
  const [researchUiState, setResearchUiState] = useState<ResearchUiState>("ready_to_rerun");
  const [intakeMode, setIntakeMode] = useState<"new" | "clarify">("new");
  const [sessionExpiredDuringResearch, setSessionExpiredDuringResearch] = useState(false);
  const [researchFailure, setResearchFailure] = useState<CommercialErrorView | null>(null);
  const runInFlightRef = useRef(false);
  const confirmInFlightRef = useRef(false);
  const phaseRef = useRef<AgencyPhase>("intake");
  const resumeStartedRef = useRef(false);
  const lastReportSnapshotRef = useRef<ReportSnapshot | null>(null);

  const [mode, setMode] = useState<IntegrationMode>("backend");
  const [projects, setProjects] = useState<WorkspaceProjectViewModel[]>([]);
  const [projectsLoaded, setProjectsLoaded] = useState(false);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  const refreshProjects = useCallback(async () => {
    setProjectsLoaded(false);
    setMode(getIntegrationMode());
    const result = await loadWorkspaceProjects();
    const enriched = await enrichWorkspaceProjectsWithBiv(result.projects);
    setProjects(enriched.projects);
    setProjectsLoaded(true);
  }, []);

  const syncProjectContext = useCallback(async (projectId: string) => {
    try {
      const current = await getCurrentAnalysisContext(projectId);
      if (current.context) {
        setAnalysisContext(mergeContextSpecificity(current.context));
        if (current.context.confirmed_by_user) {
          setConfirmedContext(current.context);
        }
      }
    } catch {
      /* context optional during hydration */
    }
  }, []);

  const hydrateFromProject = useCallback(
    async (projectId: string, context?: AnalysisContextRecord | null) => {
      if (
        shouldBlockProjectHydrate({
          runInFlight: runInFlightRef.current,
          currentPhase: phaseRef.current,
        })
      ) {
        return;
      }
      await syncProjectContext(projectId);
      const contextParams =
        context?.context_id && context.input_snapshot_hash
          ? {
              analysis_context_id: context.context_id,
              input_snapshot_hash: context.input_snapshot_hash,
            }
          : undefined;
      try {
        const loaded = await getLaunchPackJourney(projectId);
        setJourney(loaded);
        setActiveProjectId(projectId);
        if (
          contextParams &&
          loaded.validation.output.analysis_context_id &&
          loaded.validation.output.input_snapshot_hash &&
          (loaded.validation.output.analysis_context_id !== contextParams.analysis_context_id ||
            loaded.validation.output.input_snapshot_hash !== contextParams.input_snapshot_hash)
        ) {
          return;
        }
        if (!isResearchTerminal(loaded.validation.output)) {
          return;
        }
        if (isPartialResearchOutput(loaded.validation.output) && context) {
          applyValidationPartial(
            {
              run_id: loaded.validation.run_id,
              user_request_id: loaded.user_request_id,
              project_id: projectId,
              status: "failed",
              output: loaded.validation.output,
              progress: loaded.validation.output.run_progress ?? null,
            },
            context,
            loaded.user_request_id,
            loaded.user_request_text,
          );
          return;
        }
        setActiveRunId(loaded.validation.output.run_id ?? loaded.validation.run_id);
        setActiveUserRequestId(loaded.user_request_id);
        setValidationResult(loaded.validation.output);
        setDraftText(loaded.user_request_text);
        setResearchUiState(
          loaded.validation.output.customer_report ? "completed" : "legacy_report",
        );
        const mapped = mapValidationToAgencyVerdict(
          { id: loaded.user_request_id, text: loaded.user_request_text } as BackendUserRequestDto,
          loaded.validation.output,
        );
        setStages(buildStagesFromValidationOutput(loaded.validation.output));
        setVerdict(mapped);
        setPhase("verdict");
      } catch {
        const fallback = await getProjectBusinessIdeaValidation(projectId, contextParams);
        if (
          contextParams &&
          fallback.analysis_context_id &&
          fallback.input_snapshot_hash &&
          (fallback.analysis_context_id !== contextParams.analysis_context_id ||
            fallback.input_snapshot_hash !== contextParams.input_snapshot_hash)
        ) {
          return;
        }
        if (!isResearchTerminal(fallback.output)) {
          return;
        }
        if (isPartialResearchOutput(fallback.output) && context) {
          applyValidationPartial(
            {
              run_id: fallback.run_id,
              user_request_id: fallback.user_request_id,
              project_id: projectId,
              status: "failed",
              output: fallback.output,
              progress: fallback.output.run_progress ?? null,
            },
            context,
            fallback.user_request_id,
            fallback.user_request_text,
          );
          return;
        }
        setValidationResult(fallback.output);
        setDraftText(fallback.user_request_text);
        setResearchUiState(fallback.output.customer_report ? "completed" : "legacy_report");
        setActiveProjectId(projectId);
        setActiveRunId(fallback.run_id);
        setActiveUserRequestId(fallback.user_request_id);
        const mapped = mapValidationToAgencyVerdict(
          { id: fallback.user_request_id, text: fallback.user_request_text } as BackendUserRequestDto,
          fallback.output,
        );
        setStages(buildStagesFromValidationOutput(fallback.output));
        setVerdict(mapped);
        setPhase("verdict");
      }
    },
    [syncProjectContext],
  );

  async function createFreshProject(): Promise<string> {
    const created = await createProject({ name: "Новый проект" });
    setActiveProjectId(created.id);
    await refreshProjects();
    return created.id;
  }

  async function ensureProjectId(forceNew = false): Promise<string> {
    if (!forceNew && activeProjectId) {
      try {
        await fetchProject(activeProjectId);
        return activeProjectId;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setActiveProjectId(null);
        } else {
          throw err;
        }
      }
    }
    return createFreshProject();
  }

  function openIntakeFormOptimistic(text: string, projectId: string) {
    const fields: AnalysisContextFields = {
      idea_description: text,
      analysis_goal: "Проверить жизнеспособность бизнес-идеи",
    };
    setDraftText(text);
    setAnalysisContext(
      mergeContextSpecificity(buildLocalDraftContext(projectId, fields)),
    );
    setIntakeView("form");
    setPhase("intake");
    setConfirmedContext(null);
    setError(null);
  }

  async function upsertDraftFromText(text: string) {
    let projectId = activeProjectId ?? "00000000-0000-0000-0000-000000000000";
    openIntakeFormOptimistic(text, projectId);

    try {
      projectId = await ensureProjectId();
      openIntakeFormOptimistic(text, projectId);

      const { draft, projectId: resolvedProjectId } = await createAnalysisContextDraftResilient(
        projectId,
        {
          idea_description: text,
          analysis_goal: "Проверить жизнеспособность бизнес-идеи",
        },
        { recreateProject: () => createFreshProject() },
      );
      setActiveProjectId(resolvedProjectId);
      setAnalysisContext(mergeContextSpecificity(draft));
      setError(null);
      return draft;
    } catch (err) {
      setError(commercialErrorMessage(err, t));
      return buildLocalDraftContext(projectId, {
        idea_description: text,
        analysis_goal: "Проверить жизнеспособность бизнес-идеи",
      });
    }
  }

  function resetAgency() {
    setPhase("intake");
    setIntakeView("start");
    setStages([]);
    setVerdict(null);
    setValidationResult(null);
    setJourney(null);
    setAnalysisContext(null);
    setConfirmedContext(null);
    setActiveRunId(null);
    setActiveUserRequestId(null);
    setDraftText("");
    setError(null);
    setResearchFailure(null);
    setSessionExpiredDuringResearch(false);
    clearActiveResearchSession();
  }

  function handleResearchAuthError(err: unknown) {
    if (!isAuthApiError(err)) {
      return false;
    }
    const code =
      err instanceof ApiError ? mapPollingAuthErrorCode(err.status, err.errorCode ?? err.message) : null;
    setSessionExpiredDuringResearch(true);
    setPhase("analyzing");
    setResearchUiState("research_running");
    setResearchFailure(null);
    setError(
      code === "session_expired"
        ? t("auth.session_expired")
        : t("auth.authentication_required"),
    );
    return true;
  }

  function handleResearchFailure(err: unknown, options?: { restoreReport?: boolean }) {
    const failure = mapCommercialError(err, t, "research");
    setResearchFailure(failure);
    setResearchUiState("failed");
    setError(null);
    setSessionExpiredDuringResearch(false);
    setStages([]);

    if (options?.restoreReport && lastReportSnapshotRef.current) {
      const snapshot = lastReportSnapshotRef.current;
      setValidationResult(snapshot.output);
      setVerdict(snapshot.verdict);
      setStages(snapshot.stages);
      phaseRef.current = "verdict";
      setPhase("verdict");
      return;
    }

    phaseRef.current = "analyzing";
    setPhase("analyzing");
  }

  function dismissResearchFailure() {
    setResearchFailure(null);
    if (validationResult?.customer_report) {
      setResearchUiState("completed");
    }
  }

  async function applyValidationSuccess(
    validation: BusinessIdeaValidationRunResponse,
    context: AnalysisContextRecord,
    userRequestId: string,
    userRequestText: string,
  ) {
    const output = validation.output ?? null;
    const projectId = validation.project_id ?? context.project_id;
    setActiveRunId(validation.run_id);
    setValidationResult(output);
    setActiveProjectId(projectId);
    setActiveUserRequestId(userRequestId);
    setConfirmedContext(context);
    setAnalysisContext(mergeContextSpecificity(context));
    setSessionExpiredDuringResearch(false);
    clearActiveResearchSession();
    setResearchFailure(null);

    if (output && isPartialResearchOutput(output)) {
      applyValidationPartial(validation, context, userRequestId, userRequestText);
      return;
    }

    if (output && isResearchTerminal(output)) {
      clearTerminalPartialResearch();
      setResearchUiState(output.customer_report ? "completed" : "legacy_report");
      const mapped = mapValidationToAgencyVerdict(
        { id: userRequestId, text: userRequestText } as BackendUserRequestDto,
        output,
      );
      setStages(buildStagesFromValidationOutput(output));
      setVerdict(mapped);
      phaseRef.current = "verdict";
      setPhase("verdict");
      if (projectId && output.customer_report) {
        persistLastCompletedResearch({
          projectId,
          userRequestId,
          runId: validation.run_id ?? output.run_id ?? null,
          completedAt: Date.now(),
        });
      }
      if (projectId) {
        await hydrateFromProject(projectId, context);
      }
      return;
    }

    setResearchUiState("failed");
    setPhase("analyzing");
    setResearchFailure({
      title: t("commercial.errors.researchFailedTitle"),
      message: t("agency.biv.commercial.researchIncomplete"),
      actionHint: t("commercial.errors.retryHint"),
      internalCode: "research_incomplete",
    });
  }

  function applyValidationPartial(
    validation: BusinessIdeaValidationRunResponse,
    context: AnalysisContextRecord,
    userRequestId: string,
    _userRequestText: string,
  ) {
    const output = validation.output ?? null;
    const projectId = validation.project_id ?? context.project_id;
    setActiveRunId(validation.run_id);
    setValidationResult(output);
    setActiveProjectId(projectId);
    setActiveUserRequestId(userRequestId);
    setConfirmedContext(context);
    setAnalysisContext(mergeContextSpecificity(context));
    setSessionExpiredDuringResearch(false);
    clearActiveResearchSession();
    setResearchFailure(null);
    setResearchUiState("partial_research");
    if (output?.run_progress) {
      setStages(buildStagesFromBackendProgress(output.run_progress));
    } else if (validation.progress) {
      setStages(buildStagesFromBackendProgress(validation.progress));
    }
    phaseRef.current = "analyzing";
    setPhase("analyzing");
    if (projectId && validation.run_id) {
      persistTerminalPartialResearch({
        projectId,
        userRequestId,
        runId: validation.run_id,
        savedAt: Date.now(),
      });
    }
  }

  async function hydrateTerminalPartialRun(
    projectId: string,
    context: AnalysisContextRecord,
    userRequestId: string,
    runId?: string | null,
  ): Promise<boolean> {
    const latest = await tryHydrateTerminalPartialRun({
      projectId,
      userRequestId,
      runId,
      fetchLatest: async (requestId, explicitRunId) =>
        explicitRunId
          ? getBusinessIdeaValidationRun(requestId, explicitRunId)
          : getBusinessIdeaValidation(requestId),
    });
    if (!latest) {
      return false;
    }
    applyValidationPartial(latest, context, userRequestId, context.idea_description);
    return true;
  }

  function applyValidationFailed(run: BusinessIdeaValidationRunResponse) {
    if (isPartialResearchOutput(run.output)) {
      return;
    }
    setActiveRunId(run.run_id);
    setResearchUiState("failed");
    setResearchFailure({
      title: t("commercial.errors.researchFailedTitle"),
      message:
        run.safe_message ??
        (run.error_code === "research_execution_interrupted"
          ? t("commercial.errors.research_execution_interrupted")
          : t("agency.biv.commercial.researchIncomplete")),
      actionHint: t("commercial.errors.retryHint"),
      internalCode: run.error_code ?? "research_failed",
    });
    if (run.progress) {
      setStages(buildStagesFromBackendProgress(run.progress));
    }
    phaseRef.current = "analyzing";
    setPhase("analyzing");
  }

  async function followResearchRunUntilTerminal(
    userRequestId: string,
    runId: string,
    context: AnalysisContextRecord,
    userRequestText: string,
  ) {
    setActiveRunId(runId);
    setActiveUserRequestId(userRequestId);
    setResearchUiState("research_running");
    setPhase("analyzing");
    phaseRef.current = "analyzing";

    const result = await pollResearchRunUntilTerminal({
      userRequestId,
      runId,
      callbacks: {
        onProgress: (progress) => {
          setStages(buildStagesFromBackendProgress(progress));
        },
      },
    });

    switch (result.kind) {
      case "succeeded":
        await applyValidationSuccess(result.run, context, userRequestId, userRequestText);
        return;
      case "partial":
        applyValidationPartial(result.run, context, userRequestId, userRequestText);
        return;
      case "failed":
        applyValidationFailed(result.run);
        return;
      case "not_found":
        handleResearchFailure(
          new ApiError(
            t("commercial.errors.notFoundBody"),
            404,
            {},
            "validation_run_not_found",
          ),
        );
        return;
      case "auth_error":
        handleResearchAuthError(result.error);
        return;
      case "timeout":
        handleResearchFailure(new Error("research_timeout"));
        return;
      case "aborted":
        return;
      default:
        return;
    }
  }

  async function refreshStagesFromBackendProgress(
    userRequestId: string,
    runId?: string | null,
  ) {
    try {
      const progress = runId
        ? await getBusinessIdeaValidationRunProgress(userRequestId, runId)
        : await getBusinessIdeaValidationProgress(userRequestId);
      setStages(buildStagesFromBackendProgress(progress));
      return progress;
    } catch {
      return null;
    }
  }

  async function pollResearchUntilTerminal(
    userRequestId: string,
    runId?: string | null,
  ): Promise<BusinessIdeaValidationRunResponse> {
    if (runId) {
      const result = await pollResearchRunUntilTerminal({
        userRequestId,
        runId,
        callbacks: {
          onProgress: (progress) => {
            setStages(buildStagesFromBackendProgress(progress));
          },
        },
      });
      if (result.kind === "succeeded" || result.kind === "partial") {
        return result.run;
      }
      if (result.kind === "failed") {
        throw new Error(result.run.safe_message ?? result.run.error_code ?? "research_failed");
      }
      if (result.kind === "not_found") {
        throw new ApiError("validation_run_not_found", 404, {}, "validation_run_not_found");
      }
      if (result.kind === "auth_error") {
        throw result.error;
      }
      throw new Error("research_timeout");
    }

    for (let attempt = 0; attempt < 90; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
      await refreshStagesFromBackendProgress(userRequestId);
      let latest: BusinessIdeaValidationRunResponse;
      try {
        latest = await getBusinessIdeaValidation(userRequestId);
      } catch (err) {
        if (handleResearchAuthError(err)) {
          throw err;
        }
        throw err;
      }
      if (latest.progress) {
        setStages(buildStagesFromBackendProgress(latest.progress));
      }
      if (isActiveRunStatus(latest.status)) {
        continue;
      }
      if (latest.status === "failed") {
        if (isPartialResearchOutput(latest.output)) {
          return latest;
        }
        throw new Error(latest.safe_message ?? latest.error_code ?? "research_failed");
      }
      if (latest.status === "succeeded" && latest.output && isResearchTerminal(latest.output)) {
        return latest;
      }
    }
    throw new Error("research_timeout");
  }

  async function resumeActiveResearch(projectId: string, context: AnalysisContextRecord) {
    if (runInFlightRef.current || resumeStartedRef.current) {
      return;
    }
    resumeStartedRef.current = true;
    const saved = loadActiveResearchSession();
    let userRequestId =
      saved?.projectId === projectId ? saved.userRequestId : activeUserRequestId ?? null;
    const runId = saved?.projectId === projectId ? saved.runId ?? null : null;

    if (!userRequestId) {
      const terminalPartial = loadTerminalPartialResearch();
      if (terminalPartial?.projectId === projectId) {
        userRequestId = terminalPartial.userRequestId;
      }
    }

    if (!userRequestId) {
      const lastCompleted = loadLastCompletedResearch();
      if (lastCompleted?.projectId === projectId) {
        userRequestId = lastCompleted.userRequestId;
      }
    }

    if (!userRequestId) {
      try {
        const journey = await getLaunchPackJourney(projectId);
        userRequestId = journey.user_request_id;
      } catch {
        resumeStartedRef.current = false;
        return;
      }
    }

    if (!userRequestId) {
      resumeStartedRef.current = false;
      return;
    }

    runInFlightRef.current = true;
    setLoading(true);
    setPhase("analyzing");
    setResearchUiState("research_running");
    setSessionExpiredDuringResearch(false);
    setError(null);
    setStages(buildRunningStages(0));
    setActiveUserRequestId(userRequestId);

    try {
      const terminalPartial = loadTerminalPartialResearch();
      if (
        terminalPartial?.projectId === projectId &&
        terminalPartial.userRequestId === userRequestId
      ) {
        const hydrated = await hydrateTerminalPartialRun(
          projectId,
          context,
          userRequestId,
          terminalPartial.runId,
        );
        if (hydrated) {
          return;
        }
      }

      if (runId) {
        let latest: BusinessIdeaValidationRunResponse;
        try {
          latest = await getBusinessIdeaValidationRun(userRequestId, runId);
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            handleResearchFailure(err);
            return;
          }
          throw err;
        }
        if (latest.progress) {
          setStages(buildStagesFromBackendProgress(latest.progress));
        }
        if (latest.status === "succeeded") {
          if (latest.output && isResearchTerminal(latest.output)) {
            await applyValidationSuccess(
              latest,
              context,
              userRequestId,
              context.idea_description,
            );
            return;
          }
        }
        if (latest.status === "failed") {
          if (isPartialResearchOutput(latest.output)) {
            applyValidationPartial(
              latest,
              context,
              userRequestId,
              context.idea_description,
            );
            return;
          }
          applyValidationFailed(latest);
          return;
        }
        await followResearchRunUntilTerminal(
          userRequestId,
          runId,
          context,
          context.idea_description,
        );
        return;
      }

      const latest = await getBusinessIdeaValidation(userRequestId);
      if (latest.progress) {
        setStages(buildStagesFromBackendProgress(latest.progress));
      }
      if (latest.status === "succeeded" && latest.output && isResearchTerminal(latest.output)) {
        await applyValidationSuccess(
          latest,
          context,
          userRequestId,
          context.idea_description,
        );
        return;
      }
      if (latest.status === "failed") {
        if (isPartialResearchOutput(latest.output)) {
          applyValidationPartial(
            latest,
            context,
            userRequestId,
            context.idea_description,
          );
          return;
        }
        applyValidationFailed(latest);
        return;
      }
      const validation = await pollResearchUntilTerminal(userRequestId);
      await applyValidationSuccess(
        validation,
        context,
        userRequestId,
        context.idea_description,
      );
    } catch (err) {
      if (!handleResearchAuthError(err)) {
        handleResearchFailure(err);
      }
    } finally {
      setLoading(false);
      runInFlightRef.current = false;
      resumeStartedRef.current = false;
    }
  }

  async function startResearchRun(
    context: AnalysisContextRecord,
    options?: { rerun?: boolean },
  ) {
    if (runInFlightRef.current) {
      return;
    }
    if (!context.confirmed_by_user || !context.input_snapshot_hash) {
      setError(t("biv.errors.analysis_context_required"));
      return;
    }
    if (apiUnavailable) {
      setError(t("intent.apiUnavailableBody"));
      return;
    }

    runInFlightRef.current = true;
    resumeStartedRef.current = true;
    setError(null);
    setResearchFailure(null);
    setSessionExpiredDuringResearch(false);
    setLoading(true);

    const priorReport =
      validationResult?.customer_report && verdict
        ? { output: validationResult, verdict, stages }
        : null;
    if (priorReport) {
      lastReportSnapshotRef.current = priorReport;
    }

    if (options?.rerun) {
      setRerunStarting(true);
      setResearchUiState("rerun_starting");
      clearTerminalPartialResearch();
    } else {
      setResearchUiState("research_running");
    }
    setPhase("analyzing");
    phaseRef.current = "analyzing";
    setJourney(null);
    if (!priorReport) {
      setVerdict(null);
      setValidationResult(null);
    }
    setStages(buildRunningStages(0));

    try {
      let userRequestId = activeUserRequestId;
      let userRequestText = context.idea_description;

      if (!options?.rerun && userRequestId) {
        try {
          const existing = await getBusinessIdeaValidation(userRequestId);
          const matchesConfirmedContext =
            !context.context_id ||
            !context.input_snapshot_hash ||
            (existing.output?.analysis_context_id === context.context_id &&
              existing.output?.input_snapshot_hash === context.input_snapshot_hash);
          if (
            matchesConfirmedContext &&
            existing.status === "succeeded" &&
            existing.output &&
            isResearchTerminal(existing.output)
          ) {
            await applyValidationSuccess(
              existing,
              context,
              userRequestId,
              userRequestText,
            );
            return;
          }
          if (isActiveRunStatus(existing.status)) {
            setResearchUiState("research_running");
            const finished = await pollResearchUntilTerminal(
              userRequestId,
              existing.run_id,
            );
            if (isPartialResearchOutput(finished.output)) {
              applyValidationPartial(finished, context, userRequestId, userRequestText);
              return;
            }
            await applyValidationSuccess(
              finished,
              context,
              userRequestId,
              userRequestText,
            );
            return;
          }
        } catch (err) {
          if (handleResearchAuthError(err)) {
            return;
          }
        }
      }

      if (!userRequestId) {
        const dto = await createUserRequest({
          text: context.idea_description,
          selected_scenario: "idea_validation",
          skill_inputs: {
            home_agency_flow: "v2",
            analysis_intent: "business_viability_research",
            analysis_context_id: context.context_id,
            rerun: options?.rerun ? "true" : "false",
          },
        });
        userRequestId = dto.id;
        userRequestText = dto.text;
        setActiveUserRequestId(userRequestId);
      }

      persistActiveResearchSession({
        projectId: context.project_id,
        userRequestId,
        contextId: context.context_id,
        inputSnapshotHash: context.input_snapshot_hash,
        startedAt: Date.now(),
      });

      const isRerun = Boolean(options?.rerun);
      const idempotencyKey = isRerun
        ? buildRerunIdempotencyKey(context.context_id, context.input_snapshot_hash)
        : buildResearchIdempotencyKey(context.context_id, context.input_snapshot_hash);

      const accepted = await startBusinessIdeaValidationRun(userRequestId, {
        idempotency_key: idempotencyKey,
        research_mode: isRerun
          ? intakeMode === "clarify"
            ? "refined_rerun"
            : "rerun"
          : "initial",
        parent_run_id: isRerun && activeRunId ? activeRunId : undefined,
        changed_fields: isRerun && intakeMode === "clarify" ? highlightIntakeFields : undefined,
        analysis_context_id: context.context_id,
        input_snapshot_hash: context.input_snapshot_hash,
        idea: context.idea_description,
        location: context.geography ?? undefined,
        target_audience: context.target_customer ?? undefined,
        market: context.business_model ?? undefined,
        budget: context.budget_context ?? undefined,
        constraints: context.known_competitors ?? undefined,
      });

      setActiveRunId(accepted.run_id);
      setActiveUserRequestId(accepted.user_request_id);
      persistActiveResearchSession({
        projectId: context.project_id,
        userRequestId: accepted.user_request_id,
        contextId: context.context_id,
        inputSnapshotHash: context.input_snapshot_hash,
        runId: accepted.run_id,
        startedAt: Date.now(),
      });

      await followResearchRunUntilTerminal(
        accepted.user_request_id,
        accepted.run_id,
        context,
        userRequestText,
      );
    } catch (err) {
      if (!handleResearchAuthError(err)) {
        handleResearchFailure(err, { restoreReport: Boolean(priorReport) });
      }
    } finally {
      setLoading(false);
      setRerunStarting(false);
      runInFlightRef.current = false;
      resumeStartedRef.current = false;
    }
  }

  async function resolveContextForRerun(): Promise<AnalysisContextRecord | null> {
    if (confirmedContext?.confirmed_by_user && confirmedContext.input_snapshot_hash) {
      return confirmedContext;
    }
    if (analysisContext?.confirmed_by_user && analysisContext.input_snapshot_hash) {
      return analysisContext;
    }
    if (activeProjectId) {
      const current = await getCurrentAnalysisContext(activeProjectId);
      if (current.context?.confirmed_by_user && current.context.input_snapshot_hash) {
        setAnalysisContext(mergeContextSpecificity(current.context));
        setConfirmedContext(current.context);
        return current.context;
      }
    }
    return null;
  }

  async function handleRetryResearch() {
    const ctx = await resolveContextForRerun();
    if (!ctx) {
      setError(t("agency.biv.commercial.contextMissingForRerun"));
      return;
    }
    await startResearchRun(ctx, { rerun: true });
  }

  const applyContextState = useCallback(
    async (projectId: string, context: AnalysisContextRecord | null, hasCompleted: boolean) => {
      if (context && !runInFlightRef.current) {
        const latestResult = await fetchProjectLatestBivRun(projectId);
        if (latestResult.kind === "server_error") {
          setResearchFailure({
            title: t("commercial.errors.researchFailedTitle"),
            message: t("commercial.errors.hydrationUnavailable"),
            actionHint: t("commercial.errors.retryHint"),
            internalCode: "project_hydration_unavailable",
          });
          setActiveProjectId(projectId);
          setAnalysisContext(mergeContextSpecificity(context));
          setDraftText(context.idea_description);
          if (context.confirmed_by_user) {
            setConfirmedContext(mergeContextSpecificity(context));
          }
          phaseRef.current = "analyzing";
          setPhase("analyzing");
          setResearchUiState("failed");
          return;
        }
        const latestSummary =
          latestResult.kind === "found" ? latestResult.summary : null;
        if (latestSummary) {
          setActiveProjectId(projectId);
          setAnalysisContext(mergeContextSpecificity(context));
          setDraftText(context.idea_description);
          if (context.confirmed_by_user) {
            setConfirmedContext(mergeContextSpecificity(context));
          }
          setActiveUserRequestId(latestSummary.user_request_id);
          setActiveRunId(latestSummary.run_id);

          if (
            latestSummary.status === "queued" ||
            latestSummary.status === "running"
          ) {
            phaseRef.current = "analyzing";
            setPhase("analyzing");
            setResearchUiState("research_running");
            setLoading(true);
            if (latestSummary.progress) {
              setStages(buildStagesFromBackendProgress(latestSummary.progress));
            } else {
              setStages(buildRunningStages(0));
            }
            persistActiveResearchSession({
              projectId,
              userRequestId: latestSummary.user_request_id,
              contextId: context.context_id,
              inputSnapshotHash: context.input_snapshot_hash ?? "",
              runId: latestSummary.run_id,
              startedAt: Date.now(),
            });
            try {
              await followResearchRunUntilTerminal(
                latestSummary.user_request_id,
                latestSummary.run_id,
                context,
                context.idea_description,
              );
            } finally {
              setLoading(false);
            }
            return;
          }

          if (latestSummary.status === "failed" && !latestSummary.has_output) {
            applyValidationFailed({
              run_id: latestSummary.run_id,
              user_request_id: latestSummary.user_request_id,
              project_id: projectId,
              status: "failed",
              output: null,
              error_code: latestSummary.safe_error_code,
              safe_message: latestSummary.safe_message,
              progress: latestSummary.progress ?? null,
            });
            return;
          }

          if (
            latestSummary.status === "failed" &&
            latestSummary.result_kind === "partial_research"
          ) {
            try {
              const run = await getBusinessIdeaValidationRun(
                latestSummary.user_request_id,
                latestSummary.run_id,
              );
              if (isPartialResearchOutput(run.output)) {
                applyValidationPartial(
                  run,
                  context,
                  latestSummary.user_request_id,
                  context.idea_description,
                );
                return;
              }
            } catch {
              /* fall through to journey hydration */
            }
          }

          if (latestSummary.status === "succeeded" && latestSummary.has_output) {
            await hydrateFromProject(projectId, context);
            return;
          }
        }
      }

      const activeSession = loadActiveResearchSession();
      if (
        context &&
        activeSession?.projectId === projectId &&
        activeSession.runId &&
        activeSession.userRequestId &&
        !runInFlightRef.current
      ) {
        setAnalysisContext(mergeContextSpecificity(context));
        setActiveProjectId(projectId);
        setDraftText(context.idea_description);
        if (context.confirmed_by_user) {
          setConfirmedContext(mergeContextSpecificity(context));
        }
        phaseRef.current = "analyzing";
        setPhase("analyzing");
        setResearchUiState("research_running");
        setStages(buildRunningStages(0));
        setLoading(true);
        if (!resumeStartedRef.current && !runInFlightRef.current) {
          void resumeActiveResearch(projectId, context);
        }
        return;
      }

      const action = resolveContextApplyAction({
        contextState: context?.state ?? null,
        hasCompleted,
        confirmedByUser: Boolean(context?.confirmed_by_user),
        runInFlight: runInFlightRef.current,
        currentPhase: phaseRef.current,
      });

      if (action.kind === "noop_active_research") {
        if (context) {
          setAnalysisContext(mergeContextSpecificity(context));
          if (context.confirmed_by_user) {
            setConfirmedContext(mergeContextSpecificity(context));
          }
        }
        return;
      }

      setAnalysisContext(context ? mergeContextSpecificity(context) : null);
      setActiveProjectId(projectId);

      if (action.kind === "start_empty") {
        setIntakeView("start");
        return;
      }

      if (!context) {
        return;
      }

      setDraftText(context.idea_description);

      if (action.kind === "recovery") {
        setIntakeView("recovery");
        setPhase("intake");
        setConfirmedContext(null);
        return;
      }

      if (action.kind === "completed_hydrate") {
        if (context.confirmed_by_user) {
          setConfirmedContext(mergeContextSpecificity(context));
        }
        await hydrateFromProject(projectId, context);
        return;
      }

      if (action.kind === "confirmed_ready") {
        if (context) {
          const terminalPartial = loadTerminalPartialResearch();
          if (terminalPartial?.projectId === projectId) {
            try {
              const hydrated = await hydrateTerminalPartialRun(
                projectId,
                context,
                terminalPartial.userRequestId,
                terminalPartial.runId ?? null,
              );
              if (hydrated) {
                return;
              }
            } catch {
              /* fall through to project latest hydration */
            }
          }
          const contextParams =
            context.context_id && context.input_snapshot_hash
              ? {
                  analysis_context_id: context.context_id,
                  input_snapshot_hash: context.input_snapshot_hash,
                }
              : undefined;
          try {
            const latest = await getProjectBusinessIdeaValidation(projectId, contextParams);
            if (
              isPartialResearchOutput(latest.output) &&
              isResearchTerminal(latest.output)
            ) {
              applyValidationPartial(
                {
                  run_id: latest.run_id,
                  user_request_id: latest.user_request_id,
                  project_id: projectId,
                  status: "failed",
                  output: latest.output,
                  progress: latest.output.run_progress ?? null,
                },
                context,
                latest.user_request_id,
                latest.user_request_text,
              );
              return;
            }
          } catch {
            /* fall through to confirmed intake */
          }
        }
        setConfirmedContext(context);
        setIntakeView("confirmed");
        setPhase("intake");
        return;
      }

      if (action.kind === "analyzing_resume") {
        if (context.confirmed_by_user) {
          setConfirmedContext(mergeContextSpecificity(context));
        }
        const terminalPartial = loadTerminalPartialResearch();
        const partialUserRequestId =
          terminalPartial?.projectId === projectId ? terminalPartial.userRequestId : null;
        if (partialUserRequestId) {
          try {
            const hydrated = await hydrateTerminalPartialRun(
              projectId,
              context,
              partialUserRequestId,
              terminalPartial?.runId ?? null,
            );
            if (hydrated) {
              return;
            }
          } catch {
            /* fall through to active run resume */
          }
        }
        setPhase("analyzing");
        setResearchUiState("research_running");
        setStages(buildRunningStages(1));
        if (!resumeStartedRef.current && !runInFlightRef.current) {
          resumeStartedRef.current = true;
          void resumeActiveResearch(projectId, context).finally(() => {
            resumeStartedRef.current = false;
          });
        }
        return;
      }

      setIntakeView("form");
      setPhase("intake");
    },
    [hydrateFromProject],
  );

  const loadAnalysisContext = useCallback(async () => {
    if (apiUnavailable) return;
    if (runInFlightRef.current || phaseRef.current === "analyzing") {
      return;
    }
    try {
      const backendProjects = await fetchProjects();
      if (backendProjects.length === 0) {
        setIntakeView("start");
        setActiveProjectId(null);
        return;
      }

      const activeSession = loadActiveResearchSession();
      const lastCompleted = loadLastCompletedResearch();
      const preferredProjectIds = [
        effectiveProjectId,
        activeSession?.projectId ?? null,
        lastCompleted?.projectId ?? null,
      ].filter((value): value is string => Boolean(value));

      const snapshots: ProjectContextSnapshot[] = [];
      for (const project of backendProjects) {
        try {
          const current = await getCurrentAnalysisContext(project.id);
          snapshots.push({
            projectId: project.id,
            projectUpdatedAt: project.updated_at,
            context: current.context,
            hasCompletedAnalysis: current.has_completed_analysis,
            completedRunId: current.completed_run_id,
          });
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            continue;
          }
          if (handleResearchAuthError(err)) {
            return;
          }
          throw err;
        }
      }

      if (snapshots.length === 0) {
        setIntakeView("start");
        setActiveProjectId(null);
        return;
      }

      const picked = pickAnalysisProjectSnapshot({
        snapshots,
        preferredProjectIds,
      });
      if (!picked) {
        setIntakeView("start");
        setActiveProjectId(null);
        return;
      }

      await applyContextState(
        picked.projectId,
        picked.context,
        picked.hasCompletedAnalysis,
      );
    } catch (err) {
      if (handleResearchAuthError(err)) {
        return;
      }
      setIntakeView("start");
      setActiveProjectId(null);
    }
  }, [apiUnavailable, applyContextState, effectiveProjectId]);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    void loadAnalysisContext();
  }, [loadAnalysisContext]);

  async function handleRefineInputs() {
    if (!activeProjectId) {
      setError(t("agency.biv.commercial.contextMissingForRerun"));
      return;
    }
    setError(null);
    setIntakeMode("clarify");
    try {
      const current = await getCurrentAnalysisContext(activeProjectId);
      if (current.context) {
        const merged = mergeContextSpecificity(current.context);
        setAnalysisContext(merged);
        setDraftText(merged.idea_description);
        if (merged.confirmed_by_user) {
          setConfirmedContext(merged);
        }
      }
      setHighlightIntakeFields(
        validationResult
          ? intakeFieldsFromGaps(customerGapItems(validationResult))
          : [],
      );
      setPhase("intake");
      setIntakeView("form");
    } catch (err) {
      setError(commercialErrorMessage(err, t));
    }
  }

  async function handleConfirmIntake(fields: AnalysisContextFields) {
    if (!analysisContext || loading || runInFlightRef.current || confirmInFlightRef.current) {
      return;
    }
    confirmInFlightRef.current = true;
    setLoading(true);
    setError(null);
    try {
      let projectId = activeProjectId;
      if (!projectId || isLocalDraftContext(analysisContext)) {
        projectId = await ensureProjectId();
      }
      let contextId = analysisContext.context_id;
      let workingContext = analysisContext;

      if (
        intakeMode === "clarify" &&
        !isLocalDraftContext(analysisContext) &&
        analysisContext.context_id
      ) {
        const edited = await editAnalysisContext(projectId, analysisContext.context_id, fields);
        contextId = edited.context_id;
        workingContext = mergeContextSpecificity(edited);
        setAnalysisContext(workingContext);
      } else if (isLocalDraftContext(analysisContext)) {
        const { draft, projectId: resolvedProjectId } = await createAnalysisContextDraftResilient(
          projectId,
          fields,
          { recreateProject: () => createFreshProject() },
        );
        projectId = resolvedProjectId;
        contextId = draft.context_id;
        workingContext = draft;
        setActiveProjectId(projectId);
        setAnalysisContext(mergeContextSpecificity(draft));
      } else {
        const draft = await createAnalysisContextDraft(projectId, fields);
        contextId = draft.context_id;
        workingContext = draft;
        setAnalysisContext(mergeContextSpecificity(draft));
      }

      const confirmed = await confirmAnalysisContext(
        projectId,
        contextId,
        workingContext.input_snapshot_hash ?? undefined,
      );
      setConfirmedContext(confirmed);
      setAnalysisContext(mergeContextSpecificity(confirmed));

      if (intakeMode === "clarify") {
        setIntakeMode("new");
        await startResearchRun(confirmed, { rerun: true });
        return;
      }

      const current = await getCurrentAnalysisContext(projectId);
      const followUpOnCompletedProject = current.has_completed_analysis;
      if (followUpOnCompletedProject) {
        setActiveUserRequestId(null);
      }
      await startResearchRun(
        confirmed,
        followUpOnCompletedProject ? { rerun: true } : undefined,
      );
    } catch (err) {
      setError(commercialErrorMessage(err, t));
    } finally {
      confirmInFlightRef.current = false;
      setLoading(false);
    }
  }

  function openIncompleteRecoveryIntakeForm(context: AnalysisContextRecord) {
    setConfirmedContext(null);
    setHighlightIntakeFields(context.missing_fields ?? []);
    setAnalysisContext(mergeContextSpecificity(context));
    setIntakeView("form");
    setPhase("intake");
    setError(null);
  }

  async function handleRecoveryContinue() {
    if (!activeProjectId || !analysisContext) return;
    setLoading(true);
    setError(null);
    try {
      const current = await getCurrentAnalysisContext(activeProjectId);
      const context = mergeContextSpecificity(current.context ?? analysisContext);
      setAnalysisContext(context);

      const plan = planRecoveryContinue(context);
      if (plan.action === "open_incomplete_form") {
        openIncompleteRecoveryIntakeForm({
          ...context,
          missing_fields: plan.missingFields,
        });
        return;
      }

      const confirmed = await confirmAnalysisContext(
        activeProjectId,
        context.context_id,
        context.input_snapshot_hash ?? undefined,
      );
      setConfirmedContext(confirmed);
      setAnalysisContext(confirmed);
      const afterConfirm = await getCurrentAnalysisContext(activeProjectId);
      if (afterConfirm.has_completed_analysis) {
        await hydrateFromProject(activeProjectId, confirmed);
        return;
      }
      setIntakeView("form");
    } catch (err) {
      if (shouldOpenFormAfterConfirmError(err) && activeProjectId) {
        try {
          const current = await getCurrentAnalysisContext(activeProjectId);
          if (current.context) {
            openIncompleteRecoveryIntakeForm(mergeContextSpecificity(current.context));
            return;
          }
        } catch {
          /* fall through to generic error */
        }
      }
      setError(commercialErrorMessage(err, t));
    } finally {
      setLoading(false);
    }
  }

  async function handleRecoveryEdit() {
    if (!activeProjectId || !analysisContext) return;
    setIntakeView("form");
    setConfirmedContext(null);
  }

  async function handleStartNewProject() {
    if (!activeProjectId) {
      const projectId = await ensureProjectId();
      const started = await startNewAnalysisContext(projectId);
      setActiveProjectId(started.project_id);
      setAnalysisContext(started.context);
      setDraftText("");
      setIntakeView("start");
      setConfirmedContext(null);
      setPhase("intake");
      setValidationResult(null);
      setVerdict(null);
      setJourney(null);
      setStages([]);
      await refreshProjects();
      return;
    }
    setLoading(true);
    try {
      const started = await startNewAnalysisContext(activeProjectId);
      setActiveProjectId(started.project_id);
      setAnalysisContext(started.context);
      setDraftText("");
      setIntakeView("start");
      setConfirmedContext(null);
      setPhase("intake");
      setValidationResult(null);
      setVerdict(null);
      setJourney(null);
      setStages([]);
      await refreshProjects();
    } finally {
      setLoading(false);
    }
  }

  async function handleFreeTextStart() {
    const text = draftText.trim();
    if (!text) {
      setError(t("home.needTask"));
      return;
    }
    if (isHomeDeveloperMode()) {
      saveIntentTask(text, null);
      const target = resolveFreeTextTask(text, locale);
      if (target.kind === "biv") {
        setDraftText(target.task);
        void upsertDraftFromText(target.task);
        return;
      }
      navigateToAssistant(router, target.task, target.scenario);
      return;
    }
    const target = toCanonicalPublicNavigationTarget(resolveFreeTextTask(text, locale));
    if (target.kind === "canonical_intake") {
      router.push(canonicalIntakeHref());
      return;
    }
    router.push(canonicalIntakeHref());
  }

  async function handleIntentSelect(intent: UserIntent, subIntent?: UserSubIntent) {
    if (isHomeDeveloperMode()) {
      const target = resolveIntentSelection(intent, locale, subIntent);
      if (target.kind === "biv") {
        setDraftText(target.task);
        void upsertDraftFromText(target.task);
        return;
      }
      saveIntentTask(target.task, target.scenario);
      navigateToAssistant(router, target.task, target.scenario);
      return;
    }
    router.push(canonicalIntakeHref());
  }

  function downloadReport() {
    if (!validationResult?.customer_report) {
      return;
    }
    try {
      downloadCustomerReportFile({
        report: validationResult.customer_report,
        output: validationResult,
        projectName: analysisContext?.idea_description?.slice(0, 80) ?? "Marketsynth",
      });
    } catch {
      setResearchFailure({
        title: t("commercial.errors.genericFailedTitle"),
        message: t("commercial.errors.genericFailedBody"),
        actionHint: t("commercial.errors.retryHint"),
        internalCode: "export_validation_failed",
      });
    }
  }

  const bivVm = deriveBivWorkspaceViewModel({
    phase,
    intakeView,
    loading,
    rerunStarting,
    sessionExpiredDuringResearch,
    validationResult,
    activeRunId,
    researchFailure,
    runInFlight: runInFlightRef.current,
    confirmedContextConfirmed: Boolean(confirmedContext?.confirmed_by_user),
  });

  /** Bare BIV home only after boot finished and no project bound (should be rare). */
  const allowBareBivHome =
    !contentDirectorView &&
    !effectiveProjectId &&
    bootPhase === "done" &&
    !bootError;

  const showIntakeStart =
    allowBareBivHome &&
    phase === "intake" &&
    intakeView === "start";
  const showRecovery =
    allowBareBivHome &&
    phase === "intake" &&
    intakeView === "recovery" &&
    analysisContext;
  const showIntakeForm =
    allowBareBivHome &&
    shouldShowIntakeForm({
      phase,
      intakeView,
      sessionExpiredDuringResearch,
    }) &&
    analysisContext;

  const showConfirmedReady =
    allowBareBivHome &&
    phase === "intake" &&
    intakeView === "confirmed" &&
    confirmedContext &&
    !loading;

  const projectRow =
    effectiveProjectId ? projects.find((p) => p.id === effectiveProjectId) : undefined;
  const projectDisplayName =
    projectRow?.name ||
    analysisContext?.idea_description?.slice(0, 80) ||
    confirmedContext?.idea_description?.slice(0, 80) ||
    null;
  const projectDisplayStatus = projectRow
    ? workspaceProjectLifecycleLabel({
        bivLifecycleLabel: projectRow.bivLifecycleLabel,
        bivHydrationError: projectRow.bivHydrationError,
        projectName: projectRow.name,
        statusLabel: projectRow.statusLabel,
      })
    : null;

  return (
    <CommercialErrorBoundary
      fallbackTitle={t("commercial.errors.boundaryTitle")}
      fallbackMessage={t("commercial.errors.boundaryBody")}
      retryLabel={t("commercial.errors.boundaryRetry")}
      homeLabel={t("commercial.errors.boundaryHome")}
      homeHref="/workspace/projects"
    >
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
      data-testid="workspace-home"
      data-home-mode="intent-entry"
      data-locale={locale}
    >
      <WorkspaceNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-8 sm:px-10 sm:py-10">
          {apiUnavailable ? (
            <CustomerServiceUnavailable
              showDevDiagnostics={developerMode}
              diagnostics={diagnostics}
            />
          ) : null}

          {contentDirectorView && effectiveProjectId ? (
            <div className="space-y-4">
              <ContentDirectorPanel
                projectId={effectiveProjectId}
                projectName={projectDisplayName}
                projectStatus={projectDisplayStatus}
              />
            </div>
          ) : null}

          {!contentDirectorView && effectiveProjectId ? (
            <ProjectCommandCenter
              projectId={effectiveProjectId}
              projectNameHint={projectDisplayName}
            />
          ) : null}

          {needsWorkspaceBoot && bootPhase === "loading" ? (
            <CommercialLoadingState
              label={t("projectCommandCenter.openingProject")}
              testId="workspace-boot-loading"
            />
          ) : null}

          {needsWorkspaceBoot && bootPhase === "error" && bootError ? (
            <div
              className="space-y-3 rounded-xl border p-4"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="workspace-boot-error"
              data-boot-error-kind={bootError.kind}
            >
              <p className="text-sm font-semibold" style={{ color: "var(--ms-danger, #b42318)" }}>
                {bootError.kind === "timeout"
                  ? t("commercial.errors.genericFailedTitle")
                  : bootError.kind === "unauthorized"
                    ? t("auth.session_expired")
                    : t("commercial.errors.genericFailedTitle")}
              </p>
              <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {bootError.kind === "timeout"
                  ? t("commercial.errors.retryHint")
                  : t("commercial.errors.genericFailedBody")}
              </p>
              {bootError.retryable ? (
                <CommercialButton
                  type="button"
                  onClick={() => setBootRetryKey((k) => k + 1)}
                  testId="workspace-boot-retry"
                >
                  {t("commercial.errors.boundaryRetry")}
                </CommercialButton>
              ) : (
                <Link
                  href={`${CANONICAL_COMMERCIAL_ROUTES.login}?next=${encodeURIComponent("/workspace")}`}
                  className="inline-block rounded-md px-4 py-2 text-sm font-semibold"
                  style={{
                    background: "var(--ms-brand-primary)",
                    color: "var(--ms-text-on-brand, #fff)",
                  }}
                  data-testid="workspace-boot-login"
                >
                  Войти
                </Link>
              )}
            </div>
          ) : null}

          {showRecovery ? (
            <HydrationRecoveryCard
              context={analysisContext}
              busy={loading}
              onContinue={() => void handleRecoveryContinue()}
              onEdit={() => void handleRecoveryEdit()}
              onStartNew={() => void handleStartNewProject()}
            />
          ) : null}

          {showIntakeForm ? (
            <AnalysisIntakePanel
              context={analysisContext}
              busy={loading}
              error={error}
              focusFieldsOnMount={highlightIntakeFields}
              onChange={(fields) => {
                setAnalysisContext((prev) =>
                  prev
                    ? mergeContextSpecificity({
                        ...prev,
                        ...fields,
                        idea_description: fields.idea_description ?? prev.idea_description,
                      })
                    : prev,
                );
              }}
              onConfirm={() =>
                void handleConfirmIntake({
                  idea_description: analysisContext.idea_description,
                  product_or_service: analysisContext.product_or_service,
                  target_customer: analysisContext.target_customer,
                  geography: analysisContext.geography,
                  business_model: analysisContext.business_model,
                  pricing_or_revenue_model: analysisContext.pricing_or_revenue_model,
                  current_stage: analysisContext.current_stage,
                  budget_context: analysisContext.budget_context,
                  known_competitors: analysisContext.known_competitors,
                  analysis_goal: analysisContext.analysis_goal,
                  target_customer_unknown: analysisContext.target_customer_unknown,
                  geography_unknown: analysisContext.geography_unknown,
                })
              }
            />
          ) : null}

          {showIntakeStart ? (
            isHomeDeveloperMode() ? (
              <IntentStartPanel
                draftText={draftText}
                onDraftChange={(value) => {
                  setError(null);
                  setDraftText(value);
                }}
                onSubmitFreeText={() => void handleFreeTextStart()}
                onSelectIntent={(intent, sub) => void handleIntentSelect(intent, sub)}
                loading={loading}
                error={error}
                apiUnavailable={apiUnavailable}
              />
            ) : (
              <CanonicalCommercialEntryPanel />
            )
          ) : null}

          {showConfirmedReady ? (
            <div
              className="space-y-3 rounded-xl border p-4"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              data-testid="analysis-confirmed-ready"
            >
              <p className="text-sm font-semibold">{t("agency.biv.intakeConfirmed")}</p>
              <AgencyResultActions
                showContinue={false}
                showStartResearch
                busy={loading}
                onStartResearch={() => {
                  if (
                    confirmedContext &&
                    !runInFlightRef.current &&
                    !loading
                  ) {
                    void startResearchRun(confirmedContext);
                  }
                }}
                onContinueWork={() => undefined}
                onDownloadReport={() => undefined}
                onNewProject={() => void handleStartNewProject()}
              />
            </div>
          ) : null}

          {allowBareBivHome &&
          bivVm.showPartialResearchPanel &&
          validationResult ? (
            <PartialResearchPanel
              output={validationResult}
              busy={loading || rerunStarting}
              canRerun={bivVm.canRerun}
              onRerun={() => void handleRetryResearch()}
              onBackToIdea={() => {
                setPhase("intake");
                setIntakeView("confirmed");
              }}
            />
          ) : null}

          {allowBareBivHome && bivVm.showResearchProgress ? (
            <div className="space-y-3" data-testid="biv-research-progress">
              {bivVm.showFailurePanel && researchFailure ? (
                <ResearchFailurePanel
                  failure={researchFailure}
                  busy={loading}
                  showBackToReport={Boolean(lastReportSnapshotRef.current?.output.customer_report)}
                  onRetry={() => {
                    const ctx = confirmedContext ?? analysisContext;
                    if (ctx?.confirmed_by_user) {
                      void startResearchRun(ctx, { rerun: true });
                    } else {
                      void handleRetryResearch();
                    }
                  }}
                  onBackToReport={() => {
                    if (lastReportSnapshotRef.current) {
                      const snapshot = lastReportSnapshotRef.current;
                      setValidationResult(snapshot.output);
                      setVerdict(snapshot.verdict);
                      setStages(snapshot.stages);
                      setResearchFailure(null);
                      setResearchUiState("completed");
                      phaseRef.current = "verdict";
                      setPhase("verdict");
                    }
                  }}
                  labels={{
                    reasonLabel: t("agency.biv.commercial.reason"),
                    retry: t("agency.action.retryResearch"),
                    backToReport: t("commercial.errors.backToReport"),
                    reportIssue: t("commercial.errors.reportIssue"),
                  }}
                />
              ) : (
                <ResearchProgressPanel
                  title={
                    rerunStarting
                      ? t("agency.biv.commercial.rerunStarting")
                      : t("agency.biv.commercial.researchRunning")
                  }
                  stages={stages}
                  working
                />
              )}
              {sessionExpiredDuringResearch ? (
                <div
                  className="space-y-2 rounded-lg border p-4"
                  style={{ borderColor: "var(--ms-border-default)" }}
                  data-testid="biv-session-expired"
                >
                  <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
                    {error ?? t("auth.session_expired")}
                  </p>
                  <Link
                    href="/login?next=/workspace"
                    className="inline-block rounded-md px-4 py-2 text-sm font-semibold"
                    style={{
                      background: "var(--ms-brand-primary)",
                      color: "var(--ms-text-on-brand, #fff)",
                    }}
                  >
                    Войти
                  </Link>
                </div>
              ) : null}
            </div>
          ) : null}

          {allowBareBivHome && bivVm.showControlledRecovery ? (
            <ResearchFailurePanel
              failure={
                researchFailure ?? {
                  title: t("commercial.errors.researchFailedTitle"),
                  message: t("agency.biv.commercial.researchIncomplete"),
                  actionHint: t("commercial.errors.retryHint"),
                  internalCode: "biv_unknown_state",
                }
              }
              busy={loading}
              onRetry={() => void handleRetryResearch()}
              labels={{
                reasonLabel: t("agency.biv.commercial.reason"),
                retry: t("agency.action.retryResearch"),
                backToReport: t("commercial.errors.backToReport"),
                reportIssue: t("commercial.errors.reportIssue"),
              }}
            />
          ) : null}

          {allowBareBivHome &&
          phase === "verdict" &&
          verdict &&
          validationResult &&
          isResearchTerminal(validationResult) ? (
            <div className="space-y-5">
              {researchFailure ? (
                <ResearchFailurePanel
                  failure={researchFailure}
                  busy={loading}
                  showBackToReport={bivVm.showCompletedReport}
                  onRetry={() => void handleRetryResearch()}
                  onBackToReport={dismissResearchFailure}
                  labels={{
                    reasonLabel: t("agency.biv.commercial.reason"),
                    retry: t("agency.action.retryResearch"),
                    backToReport: t("commercial.errors.backToReport"),
                    reportIssue: t("commercial.errors.reportIssue"),
                  }}
                />
              ) : null}
              {!bivVm.showLegacyMigrationOnly && bivVm.showCompletedReport ? (
                <AgencyAnalysisStages stages={stages} working={false} />
              ) : null}
              <BusinessValidationResultCard
                result={validationResult}
                busy={loading}
                migrationOnly={bivVm.showLegacyMigrationOnly}
                onCreateNewReport={() => void handleRetryResearch()}
                onRefineData={() => void handleRefineInputs()}
              />
              {journey &&
              activeProjectId &&
              hasValidVerdictForLaunchPack(validationResult) &&
              bivVm.showCompletedReport ? (
                <LaunchPackDecisionPanel
                  journey={journey}
                  busy={loading}
                  onBusyChange={setLoading}
                  onJourneyUpdate={setJourney}
                  onReviseIdea={() => {
                    setPhase("intake");
                    setIntakeView("form");
                    setJourney(null);
                  }}
                  onRefineInputs={() => void handleRefineInputs()}
                  onStopProject={resetAgency}
                />
              ) : null}
              {!bivVm.duplicateActionsBlocked ? (
              <AgencyResultActions
                showContinue={false}
                showStartResearch={false}
                showRefineInputs={bivVm.canRefine}
                showRetryResearch={bivVm.canRerun}
                showDownloadReport={bivVm.canDownload}
                busy={loading}
                onRefineInputs={() => void handleRefineInputs()}
                onRetryResearch={() => void handleRetryResearch()}
                onStartResearch={() => {
                  const ctx = confirmedContext ?? analysisContext;
                  if (ctx?.confirmed_by_user) void startResearchRun(ctx, { rerun: true });
                }}
                onContinueWork={() => undefined}
                onDownloadReport={downloadReport}
                onNewProject={() => void handleStartNewProject()}
              />
              ) : null}
              {error && !researchFailure ? (
                <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
                  {error}
                </p>
              ) : null}
            </div>
          ) : null}

          {allowBareBivHome && phase === "intake" ? (
            <>
              <HomeCreativeCapabilityTeaser openHref="/workspace/projects" />
              <HomeRecentProjects
                projects={projects}
                mode={mode}
                loaded={projectsLoaded}
              />
            </>
          ) : null}

          {developerMode && allowBareBivHome && phase === "intake" ? (
            <p className="text-center text-xs" style={{ color: "var(--ms-text-muted)" }}>
              <Link
                href="/workspace/developer"
                className="underline"
                data-testid="home-open-developer-workspace"
              >
                {t("agency.openDeveloperWorkspace")}
              </Link>
            </p>
          ) : null}
        </div>
      </div>
    </div>
    </CommercialErrorBoundary>
  );
}
