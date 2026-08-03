"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialEmptyState } from "@/components/commercial/commercial-empty-state";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { workspaceProjectLifecycleLabel } from "@/lib/biv/biv-lifecycle-labels";
import { loadWorkspaceProjects } from "@/lib/integration/load-workspace";
import {
  enrichWorkspaceProjectsWithBiv,
  workspaceProjectHref,
} from "@/lib/integration/enrich-workspace-projects-biv";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import { useLocale } from "@/lib/i18n";

function contentDirectorHref(projectId: string) {
  return `/workspace?project=${encodeURIComponent(projectId)}&view=content_director`;
}

/** Project list — primary opens Project Command Center; secondary opens Content Director. */
export default function WorkspaceProjectsPage() {
  const { t } = useLocale();
  const [projects, setProjects] = useState<WorkspaceProjectViewModel[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [hydrationErrors, setHydrationErrors] = useState(0);

  const refresh = useCallback(async () => {
    setLoaded(false);
    const result = await loadWorkspaceProjects();
    const enriched = await enrichWorkspaceProjectsWithBiv(result.projects);
    setProjects(enriched.projects);
    setHydrationErrors(enriched.hydrationErrors);
    setLoaded(true);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div
      className="flex min-h-screen flex-col md:flex-row"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="workspace-projects-list"
    >
      <WorkspaceNav />
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-8 sm:px-8">
        <CommercialPageHeader
          title={t("nav.projects")}
          description={t("home.recentProjects")}
          actions={
            <Link
              href="/workspace"
              className="text-sm underline"
              style={{ color: "var(--ms-text-muted)" }}
              data-testid="projects-back-home"
            >
              {t("videoStudio.backToWorkspace")}
            </Link>
          }
          testId="projects-page-header"
        />

        {hydrationErrors > 0 ? (
          <p
            className="rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              color: "var(--ms-text-secondary)",
            }}
            data-testid="projects-hydration-warning"
          >
            {t("commercial.errors.hydrationUnavailable")}
          </p>
        ) : null}

        {!loaded ? (
          <CommercialLoadingState label={t("common.loading")} testId="projects-loading" />
        ) : projects.length === 0 ? (
          <CommercialEmptyState
            title={t("empty.projectsTitle")}
            body={t("empty.projectsBody")}
            ctaLabel={t("empty.projectsCta")}
            ctaHref="/workspace"
            testId="projects-empty"
          />
        ) : (
          <ul className="space-y-2" data-testid="projects-list">
            {projects.map((p) => (
              <li key={p.id}>
                <CommercialCard
                  padding="sm"
                  testId="projects-list-item"
                  className="transition-opacity hover:opacity-95"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Link
                      href={workspaceProjectHref(p.id)}
                      className="min-w-0 flex-1"
                      data-testid="projects-open-command-center"
                    >
                      <p className="text-sm font-medium">{p.name}</p>
                      <CommercialStatus tone="neutral">
                        {workspaceProjectLifecycleLabel({
                          bivLifecycleLabel: p.bivLifecycleLabel,
                          bivHydrationError: p.bivHydrationError,
                          projectName: p.name,
                          statusLabel: p.statusLabel,
                        })}
                      </CommercialStatus>
                    </Link>
                    <Link
                      href={contentDirectorHref(p.id)}
                      className="text-xs font-medium underline underline-offset-2"
                      style={{ color: "var(--ms-text-muted)" }}
                      data-testid="projects-open-content-director"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {t("contentDirector.entryCta")}
                    </Link>
                  </div>
                </CommercialCard>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
