"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import { ProjectCapabilityGrid } from "@/components/workspace/project/project-capability-grid";
import { ProjectGeneralChat } from "@/components/workspace/project/project-general-chat";
import {
  fetchProjectCommandCenter,
  type ProjectCommandCenterSummary,
} from "@/lib/api/endpoints/project-command-center";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
  /** Optional client hint before summary loads. */
  projectNameHint?: string | null;
};

/**
 * Canonical Project Command Center for `/workspace?project={id}`.
 * Permanent Marketsynth agency shell — not a single-capability screen.
 */
export function ProjectCommandCenter({ projectId, projectNameHint }: Props) {
  const { t } = useLocale();
  const [summary, setSummary] = useState<ProjectCommandCenterSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectCommandCenter(projectId);
      setSummary(data);
    } catch {
      setError(t("projectCommandCenter.loadError"));
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (loading && !summary) {
    return (
      <CommercialLoadingState
        label={t("common.loading")}
        testId="project-command-center-loading"
      />
    );
  }

  if (error && !summary) {
    return (
      <div data-testid="project-command-center-error" className="space-y-3">
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
        <CommercialButton onClick={() => void reload()} testId="project-command-center-retry">
          {t("projectCommandCenter.retry")}
        </CommercialButton>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-8" data-testid="project-command-center">
      <header
        className="space-y-5 rounded-xl border px-5 py-6 sm:px-8"
        style={{
          borderColor: "var(--ms-border-default)",
          background:
            "radial-gradient(ellipse 90% 80% at 20% 0%, color-mix(in srgb, var(--brand-blue) 22%, transparent), transparent 55%), #0b1220",
          color: "#f5f7fb",
        }}
        data-testid="project-command-center-header"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1 space-y-3" data-testid="pcc-brand-block">
            <Image
              src={PRODUCT_BRAND.assets.master}
              alt={PRODUCT_BRAND.logoDisplayName}
              width={520}
              height={294}
              priority
              className="h-auto w-full max-w-[min(100%,18rem)] object-contain sm:max-w-[22rem]"
              data-testid="pcc-brand-logo"
            />
            <div>
              <p
                className="text-sm font-semibold tracking-[0.12em]"
                data-testid="pcc-brand-name"
              >
                {PRODUCT_BRAND.displayName}
              </p>
              <p className="text-xs" style={{ color: "rgba(245,247,251,0.72)" }}>
                {t("brand.captionRu")}
              </p>
            </div>
          </div>
          <CommercialButton
            href="/workspace/projects"
            variant="secondary"
            testId="project-command-center-back-projects"
          >
            {t("projectCommandCenter.backToProjects")}
          </CommercialButton>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3 border-t pt-4" style={{ borderColor: "rgba(255,255,255,0.12)" }}>
          <div>
            <h1
              className="text-2xl font-semibold"
              data-testid="pcc-project-name"
            >
              {summary.project_name || projectNameHint || t("projectCommandCenter.unnamed")}
            </h1>
            {summary.project_summary ? (
              <p className="mt-1 max-w-2xl text-sm" style={{ color: "rgba(245,247,251,0.78)" }}>
                {summary.project_summary}
              </p>
            ) : (
              <p className="mt-1 text-sm" style={{ color: "rgba(245,247,251,0.78)" }}>
                {t("projectCommandCenter.workingOnProject")}
              </p>
            )}
          </div>
          <CommercialStatus tone="neutral" testId="project-command-center-status">
            {summary.project_status}
          </CommercialStatus>
        </div>
        {summary.last_changed_at ? (
          <p className="text-xs" style={{ color: "rgba(245,247,251,0.55)" }}>
            {t("projectCommandCenter.lastChanged")}:{" "}
            {new Date(summary.last_changed_at).toLocaleString()}
          </p>
        ) : null}
      </header>

      <ProjectGeneralChat projectId={projectId} />

      <ProjectCapabilityGrid cards={summary.capabilities} />

      {summary.skills.length > 0 ? (
        <section className="space-y-2" data-testid="pcc-skills-chips">
          <h2 className="text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            {t("projectCommandCenter.availableSkills")}
          </h2>
          <ul className="flex flex-wrap gap-2">
            {summary.skills.map((s) => (
              <li key={s.skill_id}>
                <CommercialStatus tone="neutral">
                  {s.name}: {s.status_label}
                </CommercialStatus>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="space-y-3" data-testid="pcc-active-work" id="pcc-activity">
        <h2 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("projectCommandCenter.currentActivity")}
        </h2>
        {summary.active_work.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--ms-text-muted)" }} data-testid="pcc-active-empty">
            {t("projectCommandCenter.noActiveWork")}
          </p>
        ) : (
          <ul className="space-y-2">
            {summary.active_work.map((item) => (
              <li key={item.id}>
                <CommercialCard padding="sm" testId="pcc-activity-item">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium">{item.title}</span>
                    <CommercialStatus tone="neutral">{item.status_label}</CommercialStatus>
                  </div>
                  {item.open_href ? (
                    <Link
                      href={item.open_href}
                      className="mt-2 inline-block text-sm underline underline-offset-2"
                    >
                      {t("projectCommandCenter.open")}
                    </Link>
                  ) : null}
                </CommercialCard>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3" data-testid="pcc-recent-results" id="pcc-recent">
        <h2 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("projectCommandCenter.recentResults")}
        </h2>
        {summary.recent_results.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--ms-text-muted)" }} data-testid="pcc-recent-empty">
            {t("projectCommandCenter.noRecentResults")}
          </p>
        ) : (
          <ul className="space-y-2">
            {summary.recent_results.map((item) => (
              <li key={`${item.kind}-${item.id}`}>
                <CommercialCard padding="sm" testId="pcc-recent-item">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium">{item.title}</span>
                    <CommercialStatus tone="neutral">{item.status_label}</CommercialStatus>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {item.kind}
                    {item.version != null ? ` · v${item.version}` : ""}
                    {item.updated_at
                      ? ` · ${new Date(item.updated_at).toLocaleString()}`
                      : ""}
                  </p>
                  {item.open_href ? (
                    <Link
                      href={item.open_href}
                      className="mt-2 inline-block text-sm underline underline-offset-2"
                    >
                      {t("projectCommandCenter.open")}
                    </Link>
                  ) : null}
                </CommercialCard>
              </li>
            ))}
          </ul>
        )}
      </section>

      {summary.attention.length > 0 ? (
        <section className="space-y-3" data-testid="pcc-attention">
          <h2 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
            {t("projectCommandCenter.attention")}
          </h2>
          <ul className="space-y-2">
            {summary.attention.map((item) => (
              <li key={item.id}>
                <CommercialCard padding="sm" testId="pcc-attention-item">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                    {item.message}
                  </p>
                  {item.cta_href && item.cta_label ? (
                    <Link
                      href={item.cta_href}
                      className="mt-2 inline-block text-sm underline underline-offset-2"
                    >
                      {item.cta_label}
                    </Link>
                  ) : null}
                </CommercialCard>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
