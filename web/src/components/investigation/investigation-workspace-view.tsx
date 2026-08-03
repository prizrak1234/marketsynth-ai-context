"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { InvestigationBackendPanel } from "@/components/investigation/investigation-backend-panel";
import { AgencyRuntimeMonitor } from "@/components/workspace/agency-runtime-monitor";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  DEFAULT_EVIDENCE_FILTERS,
  filterEvidence,
  sourceTitleMap,
  type EvidenceFilters,
} from "@/lib/investigation/evidence";
import {
  createInvestigationForProject,
  DEMO_PROJECT_IDS,
  buildScenarioWorkspace,
} from "@/lib/investigation/mock-data";
import { buildPartialIntegrationWorkspace } from "@/lib/investigation/partial-integration-workspace";
import {
  clearInvestigationWorkspace,
  loadInvestigationWorkspace,
  saveInvestigationWorkspace,
} from "@/lib/investigation/storage";
import {
  canPrepareVerdict,
  evaluateVerdictReadiness,
} from "@/lib/investigation/verdict-readiness";
import type {
  InvestigationScenarioId,
  InvestigationSource,
  InvestigationWorkspace,
  MissingDataResolution,
  StageRunState,
} from "@/lib/investigation/types";
import {
  loadInvestigationBackendBundle,
  type InvestigationLoadResult,
} from "@/lib/integration/investigation-adapter";
import {
  createInvestigationFromSubmittedBrief,
  loadInvestigationDomain,
  startInvestigationLifecycle,
  type InvestigationLoadDomainResult,
} from "@/lib/integration/investigation-sync";
import { buildInvestigationSourcesPanel } from "@/lib/integration/investigation-source-adapter";
import {
  loadInvestigationLinkedSources,
  loadProjectSources,
  registerProjectSource,
} from "@/lib/integration/source-sync";
import {
  acceptEvidenceItem,
  createManualEvidence,
  loadInvestigationEvidence,
  submitEvidenceForReview,
  type EvidenceLoadResult,
} from "@/lib/integration/evidence-sync";
import { mapEvidenceSummary } from "@/lib/integration/evidence-summary-adapter";
import { getIntegrationMode } from "@/lib/integration/mode";
import type { EvidenceItem, SourceType } from "@/lib/investigation/types";
import { getMockProject, loadLinkedIntakeDraft, saveMockProject } from "@/lib/project-intake/storage";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import type { AgencySpecialistStatus } from "@/lib/workspace/types";
import type { InvestigationStage } from "@/lib/investigation/types";

type Props = { projectId: string; investigationId?: string | null };

type SourcePanelState = ReturnType<typeof buildInvestigationSourcesPanel> | null;

function stagesFromProjections(
  projections: InvestigationLoadResult["bundle"] extends null
    ? never
    : NonNullable<InvestigationLoadResult["bundle"]>["stageProjections"],
): InvestigationStage[] {
  return projections.map((p) => ({
    id: p.id,
    label: p.label,
    order: p.order,
    state: p.state,
    note: p.note,
  }));
}

const STAGE_STATE_LABEL: Record<StageRunState, string> = {
  not_started: "Not started",
  queued: "Queued",
  in_progress: "In progress",
  blocked: "Blocked",
  completed: "Completed",
  needs_review: "Needs review",
};

export function InvestigationWorkspaceView({ projectId, investigationId }: Props) {
  const router = useRouter();
  const [workspace, setWorkspace] = useState<InvestigationWorkspace | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [filters, setFilters] = useState<EvidenceFilters>(DEFAULT_EVIDENCE_FILTERS);
  const [notice, setNotice] = useState<string | null>(null);
  const [prepareAck, setPrepareAck] = useState(false);
  const [backendProjectLabel, setBackendProjectLabel] = useState<string | null>(null);
  const [linkedIntakeName, setLinkedIntakeName] = useState<string | null>(null);
  const [integrationLoad, setIntegrationLoad] = useState<InvestigationLoadResult | null>(null);
  const [domainLoad, setDomainLoad] = useState<InvestigationLoadDomainResult | null>(null);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [sourcePanel, setSourcePanel] = useState<SourcePanelState>(null);
  const [sourceBusy, setSourceBusy] = useState(false);
  const [sourceForm, setSourceForm] = useState({
    title: "",
    url: "",
    sourceType: "website" as SourceType,
  });
  const [evidenceLoad, setEvidenceLoad] = useState<EvidenceLoadResult | null>(null);
  const [evidenceBusy, setEvidenceBusy] = useState(false);
  const [evidenceForm, setEvidenceForm] = useState({
    claim: "",
    missing: false,
    sourceId: "",
  });
  const integrationMode = getIntegrationMode();

  const refreshSources = useCallback(
    async (localSources: InvestigationSource[], invId?: string | null) => {
      if (integrationMode === "mock") {
        setSourcePanel(
          buildInvestigationSourcesPanel({
            mode: "mock",
            backend: [],
            local: localSources,
          }),
        );
        return;
      }
      let backend = await loadProjectSources(projectId);
      if (invId && backend.ok) {
        const linked = await loadInvestigationLinkedSources(projectId, invId);
        if (linked.ok && linked.sources.length > 0) {
          backend = linked;
        }
      }
      setSourcePanel(
        buildInvestigationSourcesPanel({
          mode: integrationMode,
          backend: backend.ok ? backend.sources : [],
          local: localSources,
        }),
      );
    },
    [integrationMode, projectId],
  );

  const refreshEvidence = useCallback(
    async (invId?: string | null) => {
      const result = await loadInvestigationEvidence(projectId, invId);
      setEvidenceLoad(result);
      return result;
    },
    [projectId],
  );

  useEffect(() => {
    let cancelled = false;
    ensureDemoProjectsSeeded();
    const project = getMockProject(projectId);
    const linked = loadLinkedIntakeDraft(projectId);
    if (linked?.projectBasics.name.trim()) {
      setLinkedIntakeName(linked.projectBasics.name.trim());
    }

    const bootstrapLocal = (nameOverride?: string) => {
      const existing = loadInvestigationWorkspace(projectId);
      let next = existing ?? createInvestigationForProject(projectId, project);
      if (!existing && (nameOverride || linked?.projectBasics.name.trim())) {
        next = {
          ...next,
          projectName: nameOverride || linked!.projectBasics.name.trim(),
        };
      }
      if (!existing) saveInvestigationWorkspace(next);
      return next;
    };

    const applyDomainOverlay = (
      base: InvestigationWorkspace,
      domain: InvestigationLoadDomainResult,
    ): InvestigationWorkspace => {
      if (!domain.ok || !domain.view) return base;
      return {
        ...base,
        status: domain.view.viewStatus,
        stages: domain.view.stages,
        lastUpdateLabel: `Backend Investigation v${domain.view.version} · ${domain.view.status}`,
      };
    };

    if (integrationMode === "mock") {
      const localWs = bootstrapLocal();
      setWorkspace(localWs);
      setIntegrationLoad({
        state: "success",
        mode: "mock",
        bundle: null,
        partialNotice: null,
        error: null,
        allowMockArtifacts: true,
      });
      void loadInvestigationBackendBundle(projectId).then((r) => {
        if (!cancelled) setIntegrationLoad(r);
      });
      void loadInvestigationDomain(projectId, { investigationId }).then((d) => {
        if (!cancelled) setDomainLoad(d);
      });
      void refreshSources(localWs.sources, investigationId);
      void refreshEvidence(investigationId);
      setLoaded(true);
      return () => {
        cancelled = true;
      };
    }

    void Promise.all([
      loadInvestigationBackendBundle(projectId),
      loadInvestigationDomain(projectId, { investigationId }),
    ]).then(([result, domain]) => {
      if (cancelled) return;
      setIntegrationLoad(result);
      setDomainLoad(domain);

      if (result.state === "success" && result.bundle?.project) {
        const name = result.bundle.project.name;
        setBackendProjectLabel(`${name} · backend Project`);

        if (!result.allowMockArtifacts) {
          const stages =
            domain.ok && domain.view
              ? domain.view.stages
              : stagesFromProjections(result.bundle.stageProjections);
          const shell = buildPartialIntegrationWorkspace({
            projectId,
            projectName: name,
            stages,
            intakeReadinessLabel: linked?.readiness?.status ?? "project core only",
          });
          const next = applyDomainOverlay(shell, domain);
          saveInvestigationWorkspace(next);
          setWorkspace(next);
          void refreshSources(
            next.sources,
            domain.ok ? domain.investigation?.id ?? investigationId : investigationId,
          );
          void refreshEvidence(
            domain.ok ? domain.investigation?.id ?? investigationId : investigationId,
          );
          if (domain.ok && domain.view) {
            setNotice(domain.view.notice);
          } else if (domain.ok && !domain.investigation) {
            setNotice(
              "Backend Project загружен. Investigation ещё не создано — используйте «Создать исследование». Page load ничего не создаёт.",
            );
          }
          if (domain.ok && domain.reconciliation.kind.includes("conflict")) {
            setNotice(domain.reconciliation.message);
          }
        } else {
          const local = bootstrapLocal(name);
          const merged: InvestigationWorkspace = applyDomainOverlay(
            {
              ...local,
              projectName: name,
              stages:
                domain.ok && domain.view
                  ? domain.view.stages
                  : result.bundle.stageProjections.length > 0
                    ? stagesFromProjections(result.bundle.stageProjections)
                    : local.stages,
              lastUpdateLabel: "Hybrid · backend lifecycle + local mock artifacts",
            },
            domain,
          );
          saveInvestigationWorkspace(merged);
          setWorkspace(merged);
          void refreshSources(
            merged.sources,
            domain.ok ? domain.investigation?.id ?? investigationId : investigationId,
          );
          void refreshEvidence(
            domain.ok ? domain.investigation?.id ?? investigationId : investigationId,
          );
          setNotice(
            domain.ok && domain.view
              ? `${domain.view.notice} Hybrid: local Source/Evidence = preview.`
              : "Hybrid: local investigation artifacts помечены Product Alpha mock; backend Investigation — в панели P0.2.",
          );
        }
      } else if (result.allowMockArtifacts) {
        const local = bootstrapLocal();
        setWorkspace(local);
        void refreshSources(local.sources, investigationId);
        void refreshEvidence(investigationId);
        if (result.error) {
          setNotice(`${result.error.message} Показан локальный mock (hybrid).`);
        }
      } else {
        setWorkspace(null);
        setSourcePanel(
          buildInvestigationSourcesPanel({
            mode: integrationMode,
            backend: [],
            local: [],
          }),
        );
        setNotice(result.error?.message ?? "Investigation backend недоступен.");
      }
      setLoaded(true);
    });

    return () => {
      cancelled = true;
    };
  }, [projectId, integrationMode, investigationId, refreshSources, refreshEvidence]);

  const onRegisterSource = async () => {
    if (!sourceForm.title.trim()) {
      setNotice("Укажите название источника.");
      return;
    }
    setSourceBusy(true);
    const result = await registerProjectSource(
      projectId,
      {
        source_type: sourceForm.sourceType,
        provenance_type: "user_provided",
        title: sourceForm.title.trim(),
        origin: "manual_registration",
        url: sourceForm.url.trim() || null,
        capabilities: sourceForm.sourceType === "website" ? ["webpage", "text"] : ["text"],
      },
      {
        investigationId:
          domainLoad?.ok && domainLoad.investigation
            ? domainLoad.investigation.id
            : investigationId,
      },
    );
    setSourceBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setNotice(
      "Source зарегистрирован (provenance only). URL не загружался. Evidence не создавалось.",
    );
    setSourceForm({ title: "", url: "", sourceType: "website" });
    await refreshSources(
      workspace?.sources ?? [],
      domainLoad?.ok ? domainLoad.investigation?.id ?? investigationId : investigationId,
    );
  };

  const onCreateInvestigation = async () => {
    setLifecycleBusy(true);
    const result = await createInvestigationFromSubmittedBrief(projectId);
    setLifecycleBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setDomainLoad({
      ok: true,
      mode: result.mode,
      investigation: result.investigation,
      view: result.view,
      reconciliation: {
        kind: "backend_only",
        backendWinsLifecycle: true,
        localArtifactsSeparate: true,
        message: "Investigation создано явно.",
        backendInvestigationId: result.investigation.id,
        backendVersion: result.investigation.version,
        backendStatus: result.investigation.status,
        backendCurrentStage: result.view.currentStage,
        localCurrentStage: null,
      },
      pageLoadSideEffect: false,
      createsAgentRun: false,
      createsLlm: false,
    });
    if (workspace) {
      const next = {
        ...workspace,
        status: result.view.viewStatus,
        stages: result.view.stages,
        lastUpdateLabel: `Backend Investigation v${result.view.version} · ${result.view.status}`,
      };
      saveInvestigationWorkspace(next);
      setWorkspace(next);
    }
    setNotice(
      `Investigation создано (draft). ${result.view.notice} Agent Run / LLM не запускались.`,
    );
    router.replace(
      `/workspace/projects/${projectId}/investigation?investigationId=${result.investigation.id}`,
    );
  };

  const onStartInvestigation = async () => {
    const id = domainLoad?.ok ? domainLoad.investigation?.id : null;
    if (!id) {
      setNotice("Сначала создайте Investigation.");
      return;
    }
    setLifecycleBusy(true);
    const result = await startInvestigationLifecycle(projectId, id);
    setLifecycleBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setDomainLoad({
      ok: true,
      mode: result.mode,
      investigation: result.investigation,
      view: result.view,
      reconciliation: {
        kind: "aligned",
        backendWinsLifecycle: true,
        localArtifactsSeparate: true,
        message: "Lifecycle active.",
        backendInvestigationId: result.investigation.id,
        backendVersion: result.investigation.version,
        backendStatus: result.investigation.status,
        backendCurrentStage: result.view.currentStage,
        localCurrentStage: result.view.currentStage,
      },
      pageLoadSideEffect: false,
      createsAgentRun: false,
      createsLlm: false,
    });
    if (workspace) {
      const next = {
        ...workspace,
        status: result.view.viewStatus,
        stages: result.view.stages,
        lastUpdateLabel: `Backend Investigation v${result.view.version} · ${result.view.status}`,
      };
      saveInvestigationWorkspace(next);
      setWorkspace(next);
    }
    setNotice(
      `Исследование active (lifecycle only). ${result.view.notice}`,
    );
  };

  const persist = useCallback((next: InvestigationWorkspace) => {
    const withReady = {
      ...next,
      verdictReadiness: evaluateVerdictReadiness(next),
      updatedAt: new Date().toISOString(),
    };
    saveInvestigationWorkspace(withReady);
    setWorkspace(withReady);
  }, []);

  const resetScenario = (scenarioId: InvestigationScenarioId) => {
    clearInvestigationWorkspace(projectId);
    const fresh = buildScenarioWorkspace(
      scenarioId,
      projectId,
      workspace?.projectName,
    );
    saveInvestigationWorkspace(fresh);
    setWorkspace(fresh);
    setNotice(`Сценарий сброшен: ${scenarioId}`);
    setPrepareAck(false);
  };

  const resolveMissing = (
    id: string,
    resolution: MissingDataResolution,
    assumptionNote?: string,
  ) => {
    if (!workspace) return;
    persist({
      ...workspace,
      missingData: workspace.missingData.map((m) =>
        m.id === id
          ? {
              ...m,
              resolution,
              assumptionNote:
                resolution === "assumed"
                  ? assumptionNote || m.recommendedAction
                  : m.assumptionNote,
            }
          : m,
      ),
      contradictions:
        resolution === "data_added"
          ? workspace.contradictions.map((c) =>
              c.blocksVerdict ? { ...c, resolved: false } : c,
            )
          : workspace.contradictions,
    });
    setNotice(
      resolution === "assumed"
        ? "Допущение зафиксировано явно."
        : resolution === "marked_unknown"
          ? "Отмечено как неизвестно."
          : "Данные отмечены как добавленные (local mock).",
    );
  };

  const filteredEvidence = useMemo(() => {
    if (!workspace) return [];
    if (integrationMode === "backend" && evidenceLoad?.ok) {
      return filterEvidence(evidenceLoad.views as EvidenceItem[], workspace.sources, filters);
    }
    if (integrationMode === "hybrid" && evidenceLoad?.ok && evidenceLoad.views.length > 0) {
      const backendIds = new Set(evidenceLoad.views.map((e) => e.id));
      const localOnly = workspace.evidence.filter((e) => !backendIds.has(e.id));
      return filterEvidence(
        [...evidenceLoad.views, ...localOnly],
        workspace.sources,
        filters,
      );
    }
    return filterEvidence(workspace.evidence, workspace.sources, filters);
  }, [workspace, filters, integrationMode, evidenceLoad]);

  const resolvedInvestigationId =
    domainLoad?.ok && domainLoad.investigation
      ? domainLoad.investigation.id
      : investigationId;

  const onCreateEvidence = async () => {
    const invId = resolvedInvestigationId;
    if (!invId) {
      setNotice("Сначала создайте Investigation.");
      return;
    }
    if (!evidenceForm.claim.trim()) {
      setNotice("Введите одно атомное утверждение.");
      return;
    }
    setEvidenceBusy(true);
    const result = await createManualEvidence(projectId, invId, {
      claim: evidenceForm.claim.trim(),
      evidence_type: evidenceForm.missing ? "absence_signal" : "observed_fact",
      investigation_area: "evidence_review",
      assessment_state: evidenceForm.missing ? "missing" : "unverified",
      materiality: "medium",
      why_it_matters: evidenceForm.missing ? "Блокирует полноту investigation." : null,
      source_links:
        evidenceForm.missing || !evidenceForm.sourceId
          ? []
          : [
              {
                source_id: evidenceForm.sourceId,
                stance: "supports",
                locator_type: "manual_reference",
              },
            ],
    });
    setEvidenceBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setNotice(
      "Evidence создано (draft). Это не Business Verdict. Agent Run / LLM не вызывались.",
    );
    setEvidenceForm({ claim: "", missing: false, sourceId: "" });
    await refreshEvidence(invId);
  };

  const evidenceLifecycleStatus = (evidenceId: string): string | null => {
    if (!evidenceLoad?.ok) return null;
    return evidenceLoad.evidence.find((e) => e.id === evidenceId)?.lifecycle_status ?? null;
  };

  const onSubmitEvidenceReview = async (evidenceId: string) => {
    const invId = resolvedInvestigationId;
    if (!invId) {
      setNotice("Сначала создайте Investigation.");
      return;
    }
    setEvidenceBusy(true);
    const result = await submitEvidenceForReview(projectId, invId, evidenceId);
    setEvidenceBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setNotice("Evidence отправлено на проверку (under_review).");
    await refreshEvidence(invId);
  };

  const onAcceptEvidence = async (evidenceId: string) => {
    const invId = resolvedInvestigationId;
    if (!invId) {
      setNotice("Сначала создайте Investigation.");
      return;
    }
    setEvidenceBusy(true);
    const result = await acceptEvidenceItem(projectId, invId, evidenceId);
    setEvidenceBusy(false);
    if (!result.ok) {
      setNotice(`${result.error.message} ${result.error.actionHint}`);
      return;
    }
    setNotice("Evidence принято (accepted). Это не Business Verdict.");
    await refreshEvidence(invId);
  };

  if (!loaded) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
      >
        Загрузка investigation workspace…
      </div>
    );
  }

  if (!workspace) {
    return (
      <div
        className="flex min-h-screen flex-col items-center justify-center gap-3 p-6"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      >
        <p>Проект не найден.</p>
        <Link href="/workspace/projects/new" style={{ color: "var(--brand-blue-light)" }}>
          Создать бриф
        </Link>
      </div>
    );
  }

  const readiness = workspace.verdictReadiness ?? evaluateVerdictReadiness(workspace);
  const titles = sourceTitleMap(workspace.sources);
  const canPrepare = canPrepareVerdict(
    readiness,
    workspace.assumptionsAcknowledged || prepareAck,
  );

  const monitorRows: AgencySpecialistStatus[] = workspace.specialists.map((s) => ({
    id: s.id,
    role: s.role,
    state: s.state,
    progress: s.progress,
    detail: [
      s.detail,
      `area: ${s.area}`,
      `artifacts: ${s.artifactCount}`,
      s.blocker ? `blocker: ${s.blocker}` : null,
      s.lastActivityLabel,
    ]
      .filter(Boolean)
      .join(" · "),
  }));

  return (
    <div
      className="flex min-h-screen"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
    >
      <WorkspaceNav />
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header
          className="border-b px-4 py-4 sm:px-6"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "color-mix(in srgb, var(--ms-bg-surface) 92%, transparent)",
          }}
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <p
                className="text-[11px] font-semibold uppercase tracking-[0.22em]"
                style={{ color: "var(--ms-brand-secondary)" }}
              >
                {PRODUCT_BRAND.displayName} · Investigation Workspace
              </p>
              <h1 className="mt-1 text-lg font-semibold sm:text-xl">{workspace.projectName}</h1>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <StatusPill label={`Stage: ${workspace.projectStageLabel}`} />
                <StatusPill label={`Intake: ${workspace.intakeReadinessLabel}`} />
                <StatusPill label={`Investigation: ${workspace.status}`} />
                <StatusPill label={workspace.lastUpdateLabel} muted />
                <StatusPill
                  label={
                    integrationMode === "backend"
                      ? "Artifacts: empty until Evidence domain"
                      : integrationMode === "hybrid"
                        ? "Hybrid · mock artifacts labelled"
                        : "Investigation: local mock · Phase A3"
                  }
                  muted
                />
                {backendProjectLabel ? (
                  <StatusPill label={backendProjectLabel} />
                ) : null}
                {linkedIntakeName ? (
                  <StatusPill label="Локальный intake draft связан" muted />
                ) : null}
              </div>
              <p className="mt-3 max-w-2xl text-xs" style={{ color: "var(--ms-text-muted)" }}>
                I3: Project / Campaign / Supervisor / Skill проекции — где есть factual mapping.
                Sources и Evidence без durable SoT. Opening this page does not start providers or
                LLM research. Business Verdict — I4.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/workspace/projects/new/review"
                className="rounded-md px-3 py-2 text-xs font-medium"
                style={{
                  background: "var(--ms-bg-elevated)",
                  color: "var(--ms-text-secondary)",
                  boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                }}
              >
                Открыть intake review
              </Link>
              <Link
                href="/workspace"
                className="rounded-md px-3 py-2 text-xs font-medium"
                style={{
                  background: "var(--ms-bg-elevated)",
                  color: "var(--ms-text-secondary)",
                  boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                }}
              >
                Workspace
              </Link>
            </div>
          </div>
        </header>

        <InvestigationBackendPanel load={integrationLoad} domain={domainLoad} />

        <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6">
          {integrationMode !== "mock" ? (
            <section
              className="rounded-xl border p-4"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              aria-label="Investigation lifecycle P0.2"
            >
              <h2
                className="text-sm font-semibold"
                style={{ color: "var(--ms-brand-secondary)" }}
              >
                Investigation lifecycle (P0.2)
              </h2>
              <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                Создание и старт только вручную. Page load не создаёт Investigation.
                Автоматический исследовательский контур пока не подключён.
              </p>
              {domainLoad?.ok && domainLoad.investigation ? (
                <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                  Backend · v{domainLoad.investigation.version} ·{" "}
                  {domainLoad.investigation.status} · stage{" "}
                  {domainLoad.investigation.current_stage} · brief v
                  {domainLoad.investigation.project_brief_version}
                </p>
              ) : (
                <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                  Durable Investigation ещё нет (или 404). Source/Evidence — недоступны до
                  P0.3/P0.4.
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={lifecycleBusy || Boolean(domainLoad?.ok && domainLoad.investigation)}
                  onClick={() => void onCreateInvestigation()}
                  className="rounded-md px-3 py-2 text-xs font-medium disabled:opacity-50"
                  style={{
                    background: "var(--ms-brand-primary)",
                    color: "var(--ms-text-primary)",
                  }}
                >
                  Создать исследование
                </button>
                <button
                  type="button"
                  disabled={
                    lifecycleBusy ||
                    !(
                      domainLoad?.ok &&
                      domainLoad.investigation &&
                      (domainLoad.investigation.status === "draft" ||
                        domainLoad.investigation.status === "ready")
                    )
                  }
                  onClick={() => void onStartInvestigation()}
                  className="rounded-md px-3 py-2 text-xs font-medium disabled:opacity-50"
                  style={{
                    background: "var(--ms-bg-elevated)",
                    color: "var(--ms-text-secondary)",
                    boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                  }}
                >
                  Начать исследование
                </button>
              </div>
            </section>
          ) : null}

          {notice ? (
            <p
              role="status"
              className="rounded-md border px-3 py-2 text-xs"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
              }}
            >
              {notice}
            </p>
          ) : null}

          <p
            className="rounded-xl border p-3 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-elevated)",
              color: "var(--ms-text-secondary)",
            }}
          >
            Аналитический evidence workspace. Backend / LLM / web research не подключены.
            Source → Fact → Finding → Risk/Opportunity → Decision candidate.
          </p>

          {/* Scenario switcher */}
          <section
            className="rounded-xl border p-4"
            style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
            aria-label="Mock scenarios"
          >
            <h2 className="text-sm font-semibold" style={{ color: "var(--ms-brand-secondary)" }}>
              SCENARIO (local reset)
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {(
                [
                  ["conditionally_ready", "A · Conditionally ready"],
                  ["not_ready", "B · Not ready"],
                  ["ready_for_review", "C · Ready for review"],
                  ["no_go", "D · NO_GO evidence"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className="rounded-md px-3 py-2 text-xs font-semibold"
                  style={{
                    background:
                      workspace.scenarioId === id
                        ? "var(--ms-brand-primary)"
                        : "var(--ms-bg-elevated)",
                    color: "var(--ms-text-primary)",
                    boxShadow:
                      workspace.scenarioId === id
                        ? undefined
                        : "inset 0 0 0 1px var(--ms-border-default)",
                  }}
                  onClick={() => resetScenario(id)}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-[11px]" style={{ color: "var(--ms-text-muted)" }}>
              Demo IDs: {Object.values(DEMO_PROJECT_IDS).join(" · ")}
            </p>
          </section>

          {/* Summary */}
          <Panel title="Investigation summary">
            <dl className="grid gap-3 sm:grid-cols-2 text-sm">
              <SummaryLine label="Idea" value={workspace.brief.idea} />
              <SummaryLine label="Product" value={workspace.brief.product} />
              <SummaryLine label="Geography" value={workspace.brief.geography} />
              <SummaryLine label="Budget" value={workspace.brief.budgetState} />
              <SummaryLine label="Constraints" value={workspace.brief.keyConstraints} />
              <SummaryLine
                label="Audience hypotheses"
                value={
                  workspace.brief.audienceHypotheses.length
                    ? workspace.brief.audienceHypotheses.join("; ")
                    : "—"
                }
              />
            </dl>
            {workspace.brief.assumptions.length > 0 ? (
              <ul className="mt-3 list-disc pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {workspace.brief.assumptions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            ) : null}
          </Panel>

          {/* Pipeline */}
          <Panel title="Investigation pipeline">
            <ol className="space-y-2">
              {workspace.stages.map((s) => (
                <li
                  key={s.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm"
                  style={{ borderColor: "var(--ms-border-default)" }}
                >
                  <span>
                    <span className="mr-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {s.order}.
                    </span>
                    {s.label}
                  </span>
                  <span className="text-xs font-medium" aria-label={`State: ${STAGE_STATE_LABEL[s.state]}`}>
                    [{STAGE_STATE_LABEL[s.state]}]
                    {s.note ? ` — ${s.note}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          </Panel>

          <AgencyRuntimeMonitor
            specialists={monitorRows}
            projectName={workspace.projectName}
          />

          {/* Sources */}
          <Panel title="Sources">
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              {sourcePanel?.provenanceOnlyNotice ??
                "На этом этапе Marketsynth сохраняет только сведения о происхождении источника. Анализ и доказательства создаются отдельно."}
            </p>
            {integrationMode !== "mock" ? (
              <div
                className="mb-4 rounded-md border p-3"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-elevated)",
                }}
              >
                <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
                  Добавить источник
                </h3>
                <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  Без загрузки URL и без file upload. Reliability по умолчанию — unverified.
                </p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  <input
                    aria-label="Source title"
                    value={sourceForm.title}
                    onChange={(e) =>
                      setSourceForm((f) => ({ ...f, title: e.target.value }))
                    }
                    placeholder="Title"
                    className="rounded-md border px-2 py-1.5 text-xs"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-canvas)",
                      color: "var(--ms-text-primary)",
                    }}
                  />
                  <input
                    aria-label="Source URL"
                    value={sourceForm.url}
                    onChange={(e) => setSourceForm((f) => ({ ...f, url: e.target.value }))}
                    placeholder="URL (optional, not fetched)"
                    className="rounded-md border px-2 py-1.5 text-xs"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-canvas)",
                      color: "var(--ms-text-primary)",
                    }}
                  />
                  <select
                    aria-label="Source type"
                    value={sourceForm.sourceType}
                    onChange={(e) =>
                      setSourceForm((f) => ({
                        ...f,
                        sourceType: e.target.value as SourceType,
                      }))
                    }
                    className="rounded-md border px-2 py-1.5 text-xs"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-canvas)",
                      color: "var(--ms-text-primary)",
                    }}
                  >
                    <option value="website">website</option>
                    <option value="competitor_website">competitor_website</option>
                    <option value="market_report">market_report</option>
                    <option value="uploaded_document">uploaded_document</option>
                    <option value="interview">interview</option>
                    <option value="user_statement">user_statement</option>
                    <option value="analytics_export">analytics_export</option>
                    <option value="internal_calculation">internal_calculation</option>
                  </select>
                </div>
                <button
                  type="button"
                  disabled={sourceBusy}
                  onClick={() => void onRegisterSource()}
                  className="mt-2 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                  style={{
                    background: "var(--ms-brand-primary)",
                    color: "var(--ms-text-primary)",
                  }}
                >
                  Добавить источник
                </button>
              </div>
            ) : null}
            <div className="grid gap-3">
              {(sourcePanel
                ? [...sourcePanel.backendSources, ...sourcePanel.localPreviewSources]
                : workspace.sources
              ).length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                  {integrationMode === "backend"
                    ? "Нет backend Sources. Mock не подставляется."
                    : "Нет Sources."}
                </p>
              ) : (
                (sourcePanel
                  ? [...sourcePanel.backendSources, ...sourcePanel.localPreviewSources]
                  : workspace.sources
                ).map((s) => (
                  <article
                    key={s.id}
                    className="rounded-md border p-3 text-sm"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-elevated)",
                    }}
                  >
                    <h3 className="font-medium">{s.title}</h3>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {s.sourceType} · {s.origin} · freshness: {s.freshness} · reliability:{" "}
                      {s.reliability} · status: {s.status}
                      {"originLabel" in s && s.originLabel
                        ? ` · origin: ${String(s.originLabel)}`
                        : ""}
                    </p>
                    {s.mockUrl ? (
                      <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                        {s.mockUrl}
                      </p>
                    ) : null}
                    <p className="mt-2" style={{ color: "var(--ms-text-secondary)" }}>
                      {s.notes}
                    </p>
                  </article>
                ))
              )}
            </div>
          </Panel>

          {/* Evidence Register */}
          <Panel title="Evidence Register">
            <p className="mb-3 text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Evidence — это проверяемое утверждение, связанное с конкретными источниками. Оно не
              является итоговым вердиктом.
            </p>
            {evidenceLoad?.ok && evidenceLoad.summary ? (
              <p className="mb-3 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                Summary: {mapEvidenceSummary(evidenceLoad.summary).total} · accepted{" "}
                {mapEvidenceSummary(evidenceLoad.summary).acceptedCount} · readiness{" "}
                {mapEvidenceSummary(evidenceLoad.summary).readinessContribution} · not Verdict
              </p>
            ) : null}
            {integrationMode !== "mock" ? (
              <div
                className="mb-4 rounded-md border p-3"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-elevated)",
                }}
              >
                <h3 className="text-xs font-semibold" style={{ color: "var(--ms-text-primary)" }}>
                  Добавить доказательство
                </h3>
                <textarea
                  aria-label="Evidence claim"
                  value={evidenceForm.claim}
                  onChange={(e) =>
                    setEvidenceForm((f) => ({ ...f, claim: e.target.value }))
                  }
                  placeholder="Одно атомное проверяемое утверждение"
                  rows={2}
                  className="mt-2 w-full rounded-md border px-2 py-1.5 text-xs"
                  style={{
                    borderColor: "var(--ms-border-default)",
                    background: "var(--ms-bg-canvas)",
                    color: "var(--ms-text-primary)",
                  }}
                />
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <label className="flex items-center gap-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                    <input
                      type="checkbox"
                      checked={evidenceForm.missing}
                      onChange={(e) =>
                        setEvidenceForm((f) => ({ ...f, missing: e.target.checked }))
                      }
                    />
                    Данных пока нет (missing)
                  </label>
                  {!evidenceForm.missing ? (
                    <select
                      aria-label="Supporting source"
                      value={evidenceForm.sourceId}
                      onChange={(e) =>
                        setEvidenceForm((f) => ({ ...f, sourceId: e.target.value }))
                      }
                      className="rounded-md border px-2 py-1 text-xs"
                      style={{
                        borderColor: "var(--ms-border-default)",
                        background: "var(--ms-bg-canvas)",
                        color: "var(--ms-text-primary)",
                      }}
                    >
                      <option value="">Select Source…</option>
                      {(sourcePanel?.backendSources ?? []).map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.title}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  <button
                    type="button"
                    disabled={evidenceBusy}
                    onClick={() => void onCreateEvidence()}
                    className="rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    style={{
                      background: "var(--ms-brand-primary)",
                      color: "var(--ms-text-primary)",
                    }}
                  >
                    Добавить доказательство
                  </button>
                </div>
              </div>
            ) : null}
            <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Evidence filters">
              <FilterSelect
                label="State"
                value={filters.state}
                onChange={(v) => setFilters((f) => ({ ...f, state: v as EvidenceFilters["state"] }))}
                options={["all", "confirmed", "partial", "conflicting", "missing", "outdated"]}
              />
              <FilterSelect
                label="Area"
                value={filters.area}
                onChange={(v) => setFilters((f) => ({ ...f, area: v as EvidenceFilters["area"] }))}
                options={[
                  "all",
                  "market",
                  "competitors",
                  "audience",
                  "demand",
                  "economics",
                  "risks",
                  "product",
                  "geography",
                ]}
              />
              <FilterSelect
                label="Confidence"
                value={filters.confidence}
                onChange={(v) =>
                  setFilters((f) => ({
                    ...f,
                    confidence: v as EvidenceFilters["confidence"],
                  }))
                }
                options={["all", "high", "medium", "low"]}
              />
              <FilterSelect
                label="Source type"
                value={filters.sourceType}
                onChange={(v) =>
                  setFilters((f) => ({
                    ...f,
                    sourceType: v as EvidenceFilters["sourceType"],
                  }))
                }
                options={[
                  "all",
                  "website",
                  "competitor_website",
                  "market_report",
                  "public_dataset",
                  "analytics_export",
                  "uploaded_document",
                  "interview",
                  "user_statement",
                  "internal_calculation",
                ]}
              />
            </div>
            <div className="space-y-3">
              {filteredEvidence.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                  {integrationMode === "backend"
                    ? "Нет backend Evidence. Mock не подставляется."
                    : "Нет evidence по фильтрам."}
                </p>
              ) : (
                filteredEvidence.map((e) => (
                  <article
                    key={e.id}
                    className="rounded-md border p-3 text-sm"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-elevated)",
                    }}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold uppercase" aria-label={`Evidence state ${e.state}`}>
                        [{e.state}]
                      </span>
                      <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                        {e.area} · confidence: {e.confidence}
                      </span>
                    </div>
                    <p className="mt-2 font-medium">{e.claim}</p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                      Support:{" "}
                      {e.supportingSourceIds.map((id) => titles.get(id) ?? id).join(", ") || "—"}
                      {e.contradictingSourceIds.length
                        ? ` · Conflict: ${e.contradictingSourceIds
                            .map((id) => titles.get(id) ?? id)
                            .join(", ")}`
                        : ""}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {e.reviewerNote} · {e.updatedAtLabel}
                    </p>
                    {integrationMode !== "mock" &&
                    (evidenceLifecycleStatus(e.id) === "draft" ||
                      evidenceLifecycleStatus(e.id) === "under_review") ? (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          data-testid="evidence-submit-review"
                          disabled={evidenceBusy}
                          onClick={() => void onSubmitEvidenceReview(e.id)}
                          className="rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                          style={{
                            background: "var(--ms-bg-elevated)",
                            color: "var(--ms-text-secondary)",
                            boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                          }}
                        >
                          Отправить на проверку
                        </button>
                        <button
                          type="button"
                          data-testid="evidence-accept"
                          disabled={evidenceBusy}
                          onClick={() => void onAcceptEvidence(e.id)}
                          className="rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                          style={{
                            background: "var(--ms-bg-elevated)",
                            color: "var(--ms-text-secondary)",
                            boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                          }}
                        >
                          Принять
                        </button>
                      </div>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </Panel>

          {/* Findings */}
          <Panel title="Findings">
            <div className="grid gap-3 lg:grid-cols-2">
              {workspace.findings.map((f) => {
                const isAssumption = f.type === "hypothesis";
                return (
                  <article
                    key={f.id}
                    className="rounded-md border p-3 text-sm"
                    style={{
                      borderColor: isAssumption
                        ? "color-mix(in srgb, var(--ms-status-warning, var(--brand-blue-light)) 50%, var(--ms-border-default))"
                        : "var(--ms-border-default)",
                      background: "var(--ms-bg-elevated)",
                    }}
                  >
                    <p className="text-xs font-semibold uppercase tracking-wide">
                      {isAssumption ? "HYPOTHESIS" : f.type.toUpperCase()} · {f.status}
                    </p>
                    <h3 className="mt-1 font-medium">{f.title}</h3>
                    <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                      {f.statement}
                    </p>
                    <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Impact: {f.businessImpact} · domain: {f.domain}
                    </p>
                  </article>
                );
              })}
            </div>
          </Panel>

          {/* Missing data */}
          <Panel title="Missing data">
            <div className="space-y-3">
              {workspace.missingData.map((m) => (
                <article
                  key={m.id}
                  className="rounded-md border p-3 text-sm"
                  style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-elevated)" }}
                >
                  <p className="font-medium">
                    [{m.severity}] {m.missingInformation} · {m.resolution}
                  </p>
                  <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                    {m.whyItMatters}
                  </p>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Blocks: {m.blockedDecision} · continue: {m.canContinue ? "yes" : "no"}
                  </p>
                  {m.resolution === "open" ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <ActionBtn onClick={() => resolveMissing(m.id, "data_added")}>
                        Добавить данные
                      </ActionBtn>
                      <ActionBtn onClick={() => resolveMissing(m.id, "marked_unknown")}>
                        Отметить как неизвестно
                      </ActionBtn>
                      <ActionBtn
                        onClick={() =>
                          resolveMissing(
                            m.id,
                            "assumed",
                            `Продолжаем с допущением: ${m.missingInformation}`,
                          )
                        }
                      >
                        Продолжить с допущением
                      </ActionBtn>
                    </div>
                  ) : m.assumptionNote ? (
                    <p className="mt-2 text-xs" style={{ color: "var(--brand-blue-light)" }}>
                      Assumption: {m.assumptionNote}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          </Panel>

          {/* Risks / Opportunities */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Risks">
              {workspace.risks.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                  Нет рисков в сценарии.
                </p>
              ) : (
                workspace.risks.map((r) => (
                  <article key={r.id} className="mb-3 rounded-md border p-3 text-sm" style={{ borderColor: "var(--ms-border-default)" }}>
                    <p className="font-medium">
                      [{r.severity}/{r.probability}] {r.title}
                    </p>
                    <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                      {r.description}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Consequence: {r.businessConsequence}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Mitigation: {r.mitigation} · {r.status}
                    </p>
                  </article>
                ))
              )}
            </Panel>
            <Panel title="Opportunities">
              {workspace.opportunities.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                  Нет opportunities (не гарантированные outcomes).
                </p>
              ) : (
                workspace.opportunities.map((o) => (
                  <article key={o.id} className="mb-3 rounded-md border p-3 text-sm" style={{ borderColor: "var(--ms-border-default)" }}>
                    <p className="font-medium">
                      [{o.confidence}] {o.title}
                    </p>
                    <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
                      {o.description}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Potential (not guaranteed): {o.potentialImpact}
                    </p>
                    <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      Validate: {o.recommendedValidation}
                    </p>
                  </article>
                ))
              )}
            </Panel>
          </div>

          {/* Contradictions */}
          <Panel title="Contradictions">
            {workspace.contradictions.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                Нет неразрешённых противоречий.
              </p>
            ) : (
              workspace.contradictions.map((c) => (
                <article
                  key={c.id}
                  className="mb-3 rounded-md border p-3 text-sm"
                  style={{ borderColor: "var(--ms-border-default)" }}
                >
                  <p className="font-medium">
                    [{c.importance}] {c.resolved ? "resolved" : "open"}
                    {c.blocksVerdict ? " · BLOCKS VERDICT" : ""}
                  </p>
                  <p className="mt-2" style={{ color: "var(--ms-text-secondary)" }}>
                    A ({c.fieldA}): {c.statementA}
                  </p>
                  <p style={{ color: "var(--ms-text-secondary)" }}>
                    B ({c.fieldB}): {c.statementB}
                  </p>
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    Required: {c.requiredResolution}
                  </p>
                </article>
              ))
            )}
          </Panel>

          {/* Verdict readiness */}
          <Panel title="Verdict readiness">
            <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
              Это не business verdict (GO / CONDITIONAL GO / NO GO). Только готовность
              evidence к подготовке вердикта.
            </p>
            <p
              className="mt-3 text-2xl font-semibold"
              style={{
                color:
                  readiness.status === "ready_for_review"
                    ? "var(--ms-status-success)"
                    : readiness.status === "conditionally_ready"
                      ? "var(--brand-blue-light)"
                      : "var(--ms-status-danger)",
              }}
            >
              {readiness.status}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
              <ListBlock title="Completed areas" items={readiness.completedAreas} />
              <ListBlock title="Blocking gaps" items={readiness.blockingGaps} />
              <ListBlock title="Unresolved assumptions" items={readiness.unresolvedAssumptions} />
              <ListBlock title="Next actions" items={readiness.recommendedNextActions} />
            </div>

            {readiness.status === "conditionally_ready" ? (
              <label className="mt-4 flex items-start gap-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                <input
                  type="checkbox"
                  checked={workspace.assumptionsAcknowledged || prepareAck}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setPrepareAck(checked);
                    persist({ ...workspace, assumptionsAcknowledged: checked });
                  }}
                />
                <span>
                  Подтверждаю, что остались явные допущения, и вердикт будет готовиться с
                  warnings.
                </span>
              </label>
            ) : null}

            <div className="mt-4">
              <button
                type="button"
                disabled={!canPrepare}
                className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-40"
                style={{
                  background: "var(--ms-brand-primary)",
                  color: "var(--ms-text-primary)",
                }}
                onClick={() => {
                  if (!canPrepare) return;
                  router.push(`/workspace/projects/${projectId}/verdict`);
                }}
              >
                Подготовить вердикт
              </button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function ensureDemoProjectsSeeded() {
  for (const [scenario, id] of Object.entries(DEMO_PROJECT_IDS) as Array<
    [InvestigationScenarioId, string]
  >) {
    if (getMockProject(id)) continue;
    const ws = buildScenarioWorkspace(scenario, id);
    const draft = createEmptyDraft("review");
    draft.projectBasics.name = ws.projectName;
    draft.projectBasics.ideaDescription = ws.brief.idea;
    draft.projectBasics.geography = ws.brief.geography || "—";
    draft.product.whatIsSold = ws.brief.product;
    draft.assumptions = ws.brief.assumptions;
    saveMockProject({
      id,
      name: ws.projectName,
      status: "investigation_queued",
      statusLabel: `Demo · ${scenario}`,
      createdAt: new Date().toISOString(),
      readiness: {
        status:
          scenario === "not_ready"
            ? "insufficient_data"
            : scenario === "ready_for_review"
              ? "ready"
              : "conditionally_ready",
        completedSections: [],
        missingCritical: [],
        missingOptional: [],
        assumptions: [],
        contradictions: [],
        recommendedAdditions: [],
      },
      draftSnapshot: draft,
    });
  }
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      className="rounded-xl border p-4 sm:p-5"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
    >
      <h2
        className="text-[11px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function StatusPill({ label, muted }: { label: string; muted?: boolean }) {
  return (
    <span
      className="rounded-full px-2.5 py-0.5 font-medium"
      style={{
        background: muted
          ? "var(--ms-bg-elevated)"
          : "color-mix(in srgb, var(--brand-blue) 18%, transparent)",
        color: muted ? "var(--ms-text-muted)" : "var(--brand-blue-light)",
      }}
    >
      {label}
    </span>
  );
}

function SummaryLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </dt>
      <dd className="mt-0.5" style={{ color: "var(--ms-text-secondary)" }}>
        {value || "—"}
      </dd>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  const id = `filter-${label}`;
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
      {label}
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border px-2 py-1.5 text-sm"
        style={{
          background: "var(--ms-bg-elevated)",
          color: "var(--ms-text-primary)",
          borderColor: "var(--ms-border-default)",
        }}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function ActionBtn({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md px-3 py-1.5 text-xs font-semibold"
      style={{
        background: "var(--ms-bg-elevated)",
        color: "var(--ms-text-secondary)",
        boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
      }}
    >
      {children}
    </button>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold" style={{ color: "var(--ms-text-muted)" }}>
        {title}
      </p>
      {items.length === 0 ? (
        <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
          Нет
        </p>
      ) : (
        <ul className="mt-1 list-disc pl-4" style={{ color: "var(--ms-text-secondary)" }}>
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
