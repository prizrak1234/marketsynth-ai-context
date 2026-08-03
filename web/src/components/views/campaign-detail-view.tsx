"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ApiKeyMissing,
  ProjectIdMissing,
} from "@/components/data/config-missing";
import { QueryStatus } from "@/components/data/query-status";
import { CampaignDetailHeaderActions } from "@/components/campaigns/campaign-detail-header-actions";
import { CampaignPlanDraftsSection } from "@/components/campaigns/campaign-plan-drafts-section";
import { PageHeader } from "@/components/layout/page-header";
import {
  fetchCampaignAssets,
  fetchCampaignOverview,
  fetchCampaignPublicationJobs,
  fetchCampaignWorkflow,
} from "@/lib/api";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { PublicationJobsList } from "@/components/publishing/publication-jobs-list";
import { CampaignStatusBadge } from "@/components/campaigns/campaign-status-badge";
import {
  ContentAssetStatusBadge,
  WorkflowStateBadge,
} from "@/components/ui/status-badge";
import { formatDateTime } from "@/lib/format";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type CampaignDetailViewProps = {
  campaignId: string;
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function CampaignDetailView({ campaignId }: CampaignDetailViewProps) {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =
    useEnvConfig();

  const overviewQuery = useQuery({
    queryKey: queryKeys.campaignOverview(projectId ?? "", campaignId),
    queryFn: () => fetchCampaignOverview(projectId!, campaignId),
    enabled: isProjectScopeReady,
  });

  const workflowQuery = useQuery({
    queryKey: queryKeys.campaignWorkflow(projectId ?? "", campaignId),
    queryFn: () => fetchCampaignWorkflow(projectId!, campaignId),
    enabled: isProjectScopeReady,
  });

  const publicationJobsQuery = useQuery({
    queryKey: queryKeys.campaignPublicationJobs(projectId ?? "", campaignId),
    queryFn: () =>
      fetchCampaignPublicationJobs(projectId!, campaignId, { limit: 100 }),
    enabled: isProjectScopeReady,
  });

  const assetsQuery = useQuery({
    queryKey: queryKeys.campaignAssets(projectId ?? "", campaignId),
    queryFn: () => fetchCampaignAssets(projectId!, campaignId),
    enabled: isProjectScopeReady,
  });

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Campaign" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Campaign" />
        <ProjectIdMissing />
      </div>
    );
  }

  const fallbackTitle =
    typeof overviewQuery.data?.campaign.title === "string"
      ? overviewQuery.data.campaign.title
      : campaignId;

  return (
    <div className="flex flex-col gap-6">
      <CampaignDetailHeaderActions
        projectId={projectId!}
        campaignId={campaignId}
        fallbackTitle={fallbackTitle}
      />

      <div className="grid gap-4">
        <Section title="Overview">
          <QueryStatus query={overviewQuery} loadingVariant="card">
            {(overview) => (
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <CampaignStatusBadge
                      status={String(overview.campaign.status ?? "draft")}
                    />
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Assets</dt>
                  <dd className="font-medium">
                    {overview.counts.assets_total} total ·{" "}
                    {overview.counts.assets_approved} approved ·{" "}
                    {overview.counts.assets_draft} draft
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Jobs</dt>
                  <dd className="font-medium">
                    {overview.counts.jobs_scheduled} scheduled ·{" "}
                    {overview.counts.jobs_failed} failed
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Next publication</dt>
                  <dd className="font-medium">
                    {formatDateTime(overview.schedule.next_scheduled_publication_at)}
                  </dd>
                </div>
              </dl>
            )}
          </QueryStatus>
        </Section>

        <Section title="Workflow">
          <QueryStatus query={workflowQuery} loadingVariant="card">
            {(workflow) => (
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">State</dt>
                  <dd>
                    <WorkflowStateBadge state={workflow.workflow_state} />
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Next action</dt>
                  <dd className="font-mono text-xs">{workflow.next_recommended_action}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Pending review</dt>
                  <dd>{workflow.counts.pending_review_assets}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Assets</dt>
                  <dd>
                    {workflow.counts.assets_total} total ·{" "}
                    {workflow.counts.assets_approved} approved
                  </dd>
                </div>
              </dl>
            )}
          </QueryStatus>
        </Section>

        <CampaignPlanDraftsSection
          projectId={projectId!}
          campaignId={campaignId}
        />

        <Section title="Publication calendar">
          <QueryStatus
            query={publicationJobsQuery}
            loadingVariant="table"
            loadingLines={2}
            empty={
              publicationJobsQuery.isSuccess &&
              (publicationJobsQuery.data?.length ?? 0) === 0
            }
            emptyTitle="No publication jobs"
            emptyDescription="Schedule an approved asset from its asset page."
            emptyAction={
              <Link
                href="#campaign-assets"
                className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
              >
                View campaign assets
              </Link>
            }
          >
            {(jobs) => (
              <PublicationJobsList
                projectId={projectId!}
                campaignId={campaignId}
                jobs={jobs}
              />
            )}
          </QueryStatus>
        </Section>

        <Section title="Campaign assets">
          <div id="campaign-assets">
          <QueryStatus
            query={assetsQuery}
            loadingVariant="text"
            loadingLines={4}
            empty={
              assetsQuery.isSuccess && (assetsQuery.data?.length ?? 0) === 0
            }
            emptyTitle="No assets in this campaign"
            emptyDescription="Generate draft assets from a plan draft above."
            emptyAction={
              <Link
                href="#create-plan-draft"
                className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
              >
                Create plan draft
              </Link>
            }
          >
            {(assets) => (
              <ul className="space-y-2 text-sm">
                {assets.map((asset) => (
                  <li key={asset.id}>
                    <Link
                      href={`/assets/${asset.id}`}
                      className="font-medium hover:underline"
                    >
                      {asset.title}
                    </Link>
                    <span className="ml-2 inline-flex items-center gap-2 text-muted-foreground">
                      <ContentAssetStatusBadge status={asset.status} />
                      <span>v{asset.current_version_number}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </QueryStatus>
          </div>
        </Section>
      </div>
    </div>
  );
}
