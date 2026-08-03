"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AgencyRuntimeMonitor } from "@/components/workspace/agency-runtime-monitor";
import { ActiveProjects } from "@/components/workspace/active-projects";
import { InvestigationPipeline } from "@/components/workspace/investigation-pipeline";
import { RecentVerdicts } from "@/components/workspace/recent-verdicts";
import { WorkspaceEmptyHero } from "@/components/workspace/workspace-empty-hero";
import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { WorkspaceQuickActions } from "@/components/workspace/workspace-quick-actions";
import { useAuth } from "@/lib/auth/auth-context";
import { useLocale } from "@/lib/i18n";
import {
  canShowIntegrationModeSwitcher,
  getIntegrationMode,
  integrationModeLabel,
  setIntegrationMode,
  type IntegrationMode,
} from "@/lib/integration/mode";
import { loadWorkspaceProjects } from "@/lib/integration/load-workspace";
import { loadRuntimeMonitor } from "@/lib/integration/runtime-monitor-adapter";
import type {
  RuntimeMonitorSummaryView,
  WorkspaceProjectViewModel,
} from "@/lib/integration/contracts";
import { getMockWorkspaceSnapshot } from "@/lib/workspace/mock-data";

function toastMock(action: string) {
  console.info(`[Marketsynth Workspace] ${action}`);
}

export function WorkspacePageView() {
  const router = useRouter();
  const { user } = useAuth();
  const { t } = useLocale();
  const showModeSwitch = canShowIntegrationModeSwitcher(user?.role);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setModeState] = useState<IntegrationMode>("mock");
  const [projects, setProjects] = useState<WorkspaceProjectViewModel[]>([]);
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<string>("loading");
  const [monitor, setMonitor] = useState<RuntimeMonitorSummaryView | null>(null);
  const [loaded, setLoaded] = useState(false);

  const snapshot = getMockWorkspaceSnapshot();

  const refresh = useCallback(async () => {
    setLoaded(false);
    // Normal members must not keep sticky Product Alpha mock as "real" data.
    if (!canShowIntegrationModeSwitcher(user?.role) && getIntegrationMode() === "mock") {
      setIntegrationMode("backend");
    }
    const m = getIntegrationMode();
    setModeState(m);
    const result = await loadWorkspaceProjects();
    setProjects(result.projects);
    setLoadState(result.state);
    setLoadMessage(result.message);

    const primary = result.projects[0];
    if (primary) {
      const mon = await loadRuntimeMonitor(primary.id, primary.name);
      setMonitor(mon.summary);
      if (mon.message && result.state === "success") {
        setLoadMessage((prev) => prev ?? mon.message);
      }
    } else {
      setMonitor(null);
    }
    setLoaded(true);
  }, [user?.role]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const notify = (msg: string) => {
    toastMock(msg);
    setNotice(msg);
  };

  const hasProjects = projects.length > 0;
  const headerProject = projects[0]
    ? {
        id: projects[0].id,
        name: projects[0].name,
        status: projects[0].status,
        statusLabel: projects[0].statusLabel,
        stageLabel: projects[0].stageLabel,
        lastAction: projects[0].lastAction,
        updatedAtLabel: projects[0].updatedAtLabel,
        pipelineStage: projects[0].pipelineStage,
      }
    : null;

  const showPipelineVerdicts = mode === "mock" || mode === "hybrid";

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
      data-testid="workspace-operations-dashboard"
    >
      <WorkspaceNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader
          project={headerProject}
          user={snapshot.user}
          onCreateProject={() => router.push("/workspace/projects/new")}
        />

        <div className="mx-auto w-full max-w-7xl flex-1 space-y-6 p-6">
          {showModeSwitch ? (
            <div
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-xs"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-muted)",
              }}
              role="status"
              aria-label={integrationModeLabel(mode)}
              data-testid="projects-integration-mode"
            >
              <span>
                {integrationModeLabel(mode)}
                {loadState !== "success" && loaded ? ` · ${loadState}` : ""}
              </span>
              <label className="flex items-center gap-2">
                <span className="sr-only">Integration mode</span>
                <select
                  className="rounded border px-2 py-1 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                  style={{
                    background: "var(--ms-bg-surface)",
                    borderColor: "var(--ms-border-default)",
                    color: "var(--ms-text-secondary)",
                    outlineColor: "var(--brand-blue-light)",
                  }}
                  value={mode}
                  onChange={(e) => {
                    const next = e.target.value as IntegrationMode;
                    setIntegrationMode(next);
                    setModeState(next);
                    void refresh();
                  }}
                >
                  <option value="mock">mock</option>
                  <option value="hybrid">hybrid</option>
                  <option value="backend">backend</option>
                </select>
              </label>
            </div>
          ) : (
            <p className="sr-only" data-testid="projects-integration-mode-hidden">
              {integrationModeLabel(mode)}
            </p>
          )}

          {notice || loadMessage ? (
            <p
              className="rounded-md border px-3 py-2 text-xs"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
                color: "var(--ms-text-secondary)",
              }}
              role="status"
            >
              {notice ?? loadMessage}
            </p>
          ) : null}

          {!loaded ? (
            <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
              {t("projects.loading")}
            </p>
          ) : null}

          {loaded && loadState === "unauthorized" ? (
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {t("projects.unauthorized")}
            </p>
          ) : null}

          {loaded && loadState === "error" ? (
            <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {t("projects.unavailable")}
            </p>
          ) : null}

          {loaded && !hasProjects && loadState !== "error" && loadState !== "unauthorized" ? (
            <WorkspaceEmptyHero
              onCreateProject={() => router.push("/workspace/projects/new")}
            />
          ) : null}

          {loaded && hasProjects ? <ActiveProjects projects={projects} /> : null}

          {loaded && hasProjects && monitor ? (
            <AgencyRuntimeMonitor
              specialists={monitor.specialists}
              projectName={monitor.campaignName ?? monitor.projectName}
              badgeLabel={monitor.badgeLabel}
              healthLabel={monitor.healthLabel}
              nextActionLabel={monitor.nextActionLabel}
              nextActionDescription={monitor.nextActionDescription}
              unavailableCapabilities={monitor.unavailableCapabilities}
              controlCenterHref={monitor.controlCenterHref}
              findings={monitor.topFindings}
              metricsSummary={monitor.metricsSummary}
              origin={monitor.origin}
            />
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(260px,320px)]">
            <div className="space-y-6">
              {loaded && hasProjects && showPipelineVerdicts ? (
                <InvestigationPipeline
                  stages={snapshot.pipeline}
                  activeStage={snapshot.activePipelineStage}
                />
              ) : null}
              {loaded && hasProjects && mode === "backend" ? (
                <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  {t("projects.pipelineNote")}
                </p>
              ) : null}
              <WorkspaceQuickActions
                onCreateProject={() => router.push("/workspace/projects/new")}
                onImport={() => notify("Импортировать материалы (mock)")}
                onContinue={() => notify("Продолжить исследование (mock)")}
                onKnowledge={() => notify("Открыть Knowledge (mock)")}
              />
            </div>
            {showPipelineVerdicts ? <RecentVerdicts verdicts={snapshot.verdicts} /> : (
              <aside
                className="rounded-xl border p-4 text-xs"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-elevated)",
                  color: "var(--ms-text-muted)",
                }}
              >
                {t("projects.verdictsPlaceholder")}
              </aside>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
