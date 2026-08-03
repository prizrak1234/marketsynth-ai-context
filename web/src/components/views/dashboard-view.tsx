"use client";

import { useQuery } from "@tanstack/react-query";
import { MarketsynthHomeHero } from "@/components/brand/marketsynth-home-hero";
import { MetricCard } from "@/components/data/metric-card";
import { ApiKeyMissing, ProjectIdMissing } from "@/components/data/config-missing";
import { QueryStatus } from "@/components/data/query-status";
import {
  fetchHealth,
  fetchOwnerOperationalMetrics,
  fetchProjectOperationalMetrics,
} from "@/lib/api";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { formatDateTime, formatNumber } from "@/lib/format";
import {
  getCampaignCounts,
  getPublishingMetrics,
} from "@/lib/metrics";
import { BetaFeedbackForm } from "@/components/beta/beta-feedback-form";
import { BetaGuideCard } from "@/components/beta/beta-guide-card";
import { E2eDemoFlowChecklist } from "@/components/demo/e2e-demo-flow-checklist";
import { FirstRunChecklist } from "@/components/onboarding/first-run-checklist";

export function DashboardView() {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =
    useEnvConfig();

  const healthQuery = useQuery({
    queryKey: queryKeys.health,
    queryFn: fetchHealth,
  });

  const metricsQuery = useQuery({
    queryKey: hasProjectId
      ? queryKeys.projectMetrics(projectId ?? "")
      : queryKeys.ownerMetrics,
    queryFn: () =>
      hasProjectId
        ? fetchProjectOperationalMetrics(projectId!)
        : fetchOwnerOperationalMetrics(),
    enabled: hasApiKey && (!hasProjectId || isProjectScopeReady),
  });

  const publishing =
    metricsQuery.data !== undefined
      ? getPublishingMetrics(metricsQuery.data)
      : undefined;
  const campaigns =
    metricsQuery.data !== undefined
      ? getCampaignCounts(metricsQuery.data)
      : undefined;

  return (
    <div className="flex flex-col gap-8">
      <MarketsynthHomeHero />

      <section className="flex flex-col gap-4">
        <div>
          <h2
            className="text-sm font-semibold uppercase tracking-[0.16em]"
            style={{ color: "var(--ms-brand-secondary)" }}
          >
            Операционный контур
          </h2>
          <p className="mt-1 text-sm" style={{ color: "var(--ms-text-muted)" }}>
            {healthQuery.data
              ? `API ${healthQuery.data.status} · DB ${healthQuery.data.database} · Redis ${healthQuery.data.redis}`
              : "Обзор внутренних метрик и onboarding"}
          </p>
        </div>

        {!hasApiKey ? <ApiKeyMissing /> : null}
        {hasApiKey && !hasProjectId ? <ProjectIdMissing /> : null}

        {hasApiKey && hasProjectId ? (
          <>
            <FirstRunChecklist projectId={projectId!} />
            <BetaGuideCard />
            <E2eDemoFlowChecklist projectId={projectId!} />
            <BetaFeedbackForm projectId={projectId!} />

            <QueryStatus query={metricsQuery} loadingVariant="card">
              {(metrics) => (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <MetricCard
                    label="Campaigns"
                    value={`${formatNumber(campaigns?.total)} total · ${formatNumber(campaigns?.active)} active`}
                    hint={`Window: ${metrics.window}`}
                  />
                  <MetricCard
                    label="Pending review"
                    value={formatNumber(metrics.review_queue.pending_assets)}
                  />
                  <MetricCard
                    label="Scheduled publications"
                    value={formatNumber(publishing?.scheduled_jobs_count)}
                  />
                  <MetricCard
                    label="Failed publications"
                    value={formatNumber(publishing?.failed_jobs_count)}
                  />
                  <MetricCard
                    label="Next publication"
                    value={formatDateTime(publishing?.next_scheduled_publication_at)}
                  />
                  {metrics.project_id ? (
                    <MetricCard
                      label="Scoped project"
                      value={metrics.project_id}
                      hint="From operational metrics response"
                    />
                  ) : null}
                </div>
              )}
            </QueryStatus>
          </>
        ) : null}
      </section>
    </div>
  );
}
