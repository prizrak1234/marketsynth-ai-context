"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ApiKeyMissing,
  ProjectIdMissing,
} from "@/components/data/config-missing";
import { QueryStatus } from "@/components/data/query-status";
import { ContentAssetStatusBadge } from "@/components/ui/status-badge";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/page-header";
import { ContentAssetReviewActions } from "@/components/review/content-asset-review-actions";
import { fetchProjectReviewQueue } from "@/lib/api";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { formatDateTime } from "@/lib/format";

export function ReviewQueueView() {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } =
    useEnvConfig();

  const reviewQuery = useQuery({
    queryKey: queryKeys.reviewQueue(projectId ?? ""),
    queryFn: () => fetchProjectReviewQueue(projectId!),
    enabled: isProjectScopeReady,
  });

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Review Queue" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Review Queue" />
        <ProjectIdMissing />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Review Queue"
        description="Human approval — Approve and Archive update asset status only (no auto-publish)."
      />

      <QueryStatus
        query={reviewQuery}
        loadingVariant="table"
        loadingLines={5}
        empty={
          reviewQuery.isSuccess && (reviewQuery.data?.items.length ?? 0) === 0
        }
        emptyTitle="No pending review"
        emptyDescription="Generate draft assets from a campaign plan, then return here to approve."
        emptyAction={
          <Link href="/campaigns" className={cn(buttonVariants({ variant: "default" }))}>
            Open campaigns
          </Link>
        }
      >
        {(data) => (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full min-w-[880px] text-left text-sm">
              <thead className="border-b border-border bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Asset</th>
                  <th className="px-4 py-3 font-medium">Campaign</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium">Updated</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id} className="border-b border-border/60">
                    <td className="px-4 py-3 font-medium">
                      <Link
                        href={`/assets/${item.id}`}
                        className="hover:underline"
                      >
                        {item.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {item.campaign_id && item.campaign_title ? (
                        <Link
                          href={`/campaigns/${item.campaign_id}`}
                          className="hover:underline"
                        >
                          {item.campaign_title}
                        </Link>
                      ) : (
                        (item.campaign_title ?? "—")
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <ContentAssetStatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      v{item.current_version_number}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(item.updated_at)}
                    </td>
                    <td className="px-4 py-3">
                      <ContentAssetReviewActions
                        projectId={projectId!}
                        assetId={item.id}
                        assetTitle={item.title}
                        status={item.status}
                        campaignId={item.campaign_id}
                        layout="inline"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryStatus>
    </div>
  );
}
