"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQueries, useQuery } from "@tanstack/react-query";
import {
  ApiKeyMissing,
  ProjectIdMissing,
} from "@/components/data/config-missing";
import { EmptyState } from "@/components/data/empty-state";
import { QueryStatus } from "@/components/data/query-status";
import { PageHeader } from "@/components/layout/page-header";
import { CreateCampaignForm } from "@/components/campaigns/create-campaign-form";
import { CampaignStatusBadge } from "@/components/campaigns/campaign-status-badge";
import { WorkflowStateBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import {
  fetchCampaignOverview,
  fetchCampaignWorkflow,
  fetchCampaigns,
} from "@/lib/api";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { formatDateTime } from "@/lib/format";
import type { MarketingCampaign } from "@/lib/api/types/campaigns";

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
] as const;

function CampaignTable({
  projectId,
  campaigns,
}: {
  projectId: string;
  campaigns: MarketingCampaign[];
}) {
  const workflowQueries = useQueries({
    queries: campaigns.map((campaign) => ({
      queryKey: queryKeys.campaignWorkflow(projectId, campaign.id),
      queryFn: () => fetchCampaignWorkflow(projectId, campaign.id),
    })),
  });

  const overviewQueries = useQueries({
    queries: campaigns.map((campaign) => ({
      queryKey: queryKeys.campaignOverview(projectId, campaign.id),
      queryFn: () => fetchCampaignOverview(projectId, campaign.id),
    })),
  });

  const anyChildLoading =
    workflowQueries.some((q) => q.isPending) ||
    overviewQueries.some((q) => q.isPending);

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-border bg-muted/40 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Title</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Workflow</th>
            <th className="px-4 py-3 font-medium">Pending review</th>
            <th className="px-4 py-3 font-medium">Next publication</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((campaign, index) => {
            const workflow = workflowQueries[index];
            const overview = overviewQueries[index];
            const workflowState = workflow.data?.workflow_state ?? "…";
            const pendingReview =
              workflow.data?.counts.pending_review_assets ?? "…";
            const nextPublication = overview.data?.schedule
              .next_scheduled_publication_at
              ? formatDateTime(
                  overview.data.schedule.next_scheduled_publication_at,
                )
              : overview.isPending
                ? "…"
                : "—";

            return (
              <tr key={campaign.id} className="border-b border-border/60">
                <td className="px-4 py-3">
                  <Link
                    href={`/campaigns/${campaign.id}`}
                    className="font-medium text-foreground hover:underline"
                  >
                    {campaign.title}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <CampaignStatusBadge status={campaign.status} />
                </td>
                <td className="px-4 py-3">
                  {workflow.isError ? (
                    <span className="text-xs text-destructive">error</span>
                  ) : workflow.isPending ? (
                    <span className="text-xs text-muted-foreground">…</span>
                  ) : (
                    <WorkflowStateBadge state={String(workflowState)} />
                  )}
                </td>
                <td className="px-4 py-3 tabular-nums">{pendingReview}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {nextPublication}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {anyChildLoading ? (
        <p className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
          Loading workflow and overview per campaign…
        </p>
      ) : null}
    </div>
  );
}

export function CampaignsView() {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =
    useEnvConfig();
  const [includeArchived, setIncludeArchived] = useState(false);
  const [statusFilter, setStatusFilter] =
    useState<(typeof STATUS_FILTER_OPTIONS)[number]["value"]>("all");

  const campaignsQuery = useQuery({
    queryKey: [
      ...queryKeys.campaigns(projectId ?? ""),
      { includeArchived, statusFilter },
    ],
    queryFn: () =>
      fetchCampaigns(projectId!, {
        includeArchived: includeArchived || statusFilter === "archived",
      }),
    enabled: isProjectScopeReady,
  });

  const filteredCampaigns = useMemo(() => {
    const rows = campaignsQuery.data ?? [];
    if (statusFilter === "all") {
      return rows;
    }
    return rows.filter((campaign) => campaign.status === statusFilter);
  }, [campaignsQuery.data, statusFilter]);

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Campaigns" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Campaigns" />
        <ProjectIdMissing />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Campaigns" description={`Project ${projectId}`} />

      <div id="create-campaign">
        <CreateCampaignForm projectId={projectId!} />
      </div>

      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border p-4">
        <div className="space-y-1">
          <label htmlFor="status-filter" className="text-sm font-medium">
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value as (typeof STATUS_FILTER_OPTIONS)[number]["value"],
              )
            }
            className="h-9 min-w-[160px] rounded-lg border border-border bg-background px-3 text-sm"
          >
            {STATUS_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => setIncludeArchived(event.target.checked)}
          />
          Include archived
        </label>
      </div>

      <QueryStatus
        query={campaignsQuery}
        loadingVariant="table"
        loadingLines={4}
      >
        {() => {
          const scrollToCreate = () => {
            document
              .getElementById("create-campaign")
              ?.scrollIntoView({ behavior: "smooth" });
          };

          if ((campaignsQuery.data?.length ?? 0) === 0) {
            return (
              <EmptyState
                title="No campaigns yet"
                description="Create your first campaign to start planning and review."
                action={
                  <Button type="button" onClick={scrollToCreate}>
                    Create campaign
                  </Button>
                }
              />
            );
          }

          if (filteredCampaigns.length === 0) {
            return (
              <EmptyState
                title="No campaigns match filters"
                description="Adjust status or archived filters, or create a new campaign."
                action={
                  <Button type="button" onClick={scrollToCreate}>
                    Create campaign
                  </Button>
                }
              />
            );
          }

          return (
            <CampaignTable
              projectId={projectId!}
              campaigns={filteredCampaigns}
            />
          );
        }}
      </QueryStatus>
    </div>
  );
}
