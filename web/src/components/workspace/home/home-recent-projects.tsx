"use client";

import Link from "next/link";
import type { WorkspaceProjectViewModel } from "@/lib/integration/contracts";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialEmptyState } from "@/components/commercial/commercial-empty-state";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import {
  commercialRecentProjectStatusLabel,
  filterCommercialRecentProjects,
} from "@/lib/home/commercial-recent-projects";
import { workspaceProjectHref } from "@/lib/integration/enrich-workspace-projects-biv";
import { useLocale } from "@/lib/i18n";

type Props = {
  projects: WorkspaceProjectViewModel[];
  mode: string;
  loaded: boolean;
};

export function HomeRecentProjects({ projects, mode, loaded }: Props) {
  const { t } = useLocale();
  const displayProjects = filterCommercialRecentProjects(projects);

  if (!loaded) {
    return (
      <CommercialLoadingState label={t("common.loading")} testId="home-recent-loading" />
    );
  }

  if (displayProjects.length === 0) {
    return (
      <section className="space-y-3" data-testid="home-recent-projects-empty">
        <h2 className="text-base font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("home.recentProjects")}
        </h2>
        <CommercialEmptyState
          title={
            mode === "backend" ? t("home.recentEmptyCommercial") : t("home.recentEmptyMock")
          }
          footer={
            <Link
              href="/workspace/projects"
              className="text-sm font-medium underline underline-offset-2"
              style={{ color: "var(--ms-text-accent, var(--ms-brand-primary))" }}
            >
              {t("home.allProjects")}
            </Link>
          }
          testId="home-recent-empty-card"
        />
      </section>
    );
  }

  return (
    <CommercialCard padding="md" testId="home-recent-projects">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("home.recentProjects")}
        </h2>
        <Link
          href="/workspace/projects"
          className="text-sm font-medium underline underline-offset-2"
          data-testid="home-all-projects-link"
        >
          {t("home.allProjects")}
        </Link>
      </div>
      <ul className="mt-4 space-y-2">
        {displayProjects.slice(0, 5).map((p) => (
          <li key={p.id}>
            <Link href={workspaceProjectHref(p.id)} className="block">
              <CommercialCard
                padding="sm"
                testId="home-recent-project"
                className="transition-opacity hover:opacity-95"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{p.name}</span>
                  <CommercialStatus tone="neutral">
                    {commercialRecentProjectStatusLabel(p)}
                  </CommercialStatus>
                </div>
              </CommercialCard>
            </Link>
          </li>
        ))}
      </ul>
    </CommercialCard>
  );
}
