"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CreatePlanDraftForm } from "@/components/campaigns/create-plan-draft-form";
import { PlanDraftDetailPanel } from "@/components/campaigns/plan-draft-detail-panel";
import { PlanDraftStatusBadge } from "@/components/campaigns/plan-draft-status-badge";
import { QueryStatus } from "@/components/data/query-status";
import { fetchCampaign } from "@/lib/api/endpoints/campaigns";
import { fetchCampaignPlanDrafts } from "@/lib/api/endpoints/plan-drafts";
import { queryKeys } from "@/lib/api/query-keys";
import { formatDateTime } from "@/lib/format";

type CampaignPlanDraftsSectionProps = {
  projectId: string;
  campaignId: string;
};

export function CampaignPlanDraftsSection({
  projectId,
  campaignId,
}: CampaignPlanDraftsSectionProps) {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);

  const campaignQuery = useQuery({
    queryKey: queryKeys.campaign(projectId, campaignId),
    queryFn: () => fetchCampaign(projectId, campaignId),
  });

  const planDraftsQuery = useQuery({
    queryKey: [
      ...queryKeys.campaignPlanDrafts(projectId, campaignId),
      { includeArchived },
    ],
    queryFn: () =>
      fetchCampaignPlanDrafts(projectId, campaignId, { includeArchived }),
    enabled: campaignQuery.isSuccess,
  });

  const campaignReadOnly = campaignQuery.data?.status === "archived";

  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Plan drafts</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Campaign → plan → draft content assets → review queue. No approve,
        publish, or schedule from here.
      </p>

      <div className="mt-4 space-y-4">
        {campaignReadOnly ? (
          <p className="text-sm text-amber-800 dark:text-amber-200" role="status">
            Archived campaign — read-only. Plan drafts can be viewed only.
          </p>
        ) : (
          <div id="create-plan-draft">
            <CreatePlanDraftForm
              projectId={projectId}
              campaignId={campaignId}
              onCreated={(draftId) => setSelectedDraftId(draftId)}
            />
          </div>
        )}

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => setIncludeArchived(event.target.checked)}
          />
          Include archived plan drafts
        </label>

        <QueryStatus
          query={planDraftsQuery}
          loadingVariant="table"
          loadingLines={3}
          empty={
            planDraftsQuery.isSuccess &&
            (planDraftsQuery.data?.length ?? 0) === 0
          }
          emptyTitle="No plan drafts"
          emptyDescription="Create a plan to generate draft assets for this campaign."
          emptyAction={
            campaignReadOnly ? undefined : (
              <Button
                type="button"
                onClick={() => {
                  document
                    .getElementById("create-plan-draft")
                    ?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                Create plan draft
              </Button>
            )
          }
        >
          {(drafts) => (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-border bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">Title</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Items</th>
                    <th className="px-4 py-3 font-medium">Updated</th>
                    <th className="px-4 py-3 font-medium text-right">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {drafts.map((draft) => {
                    const itemCount =
                      draft.plan_payload?.content_items?.length ?? 0;
                    return (
                      <tr
                        key={draft.id}
                        className={
                          selectedDraftId === draft.id
                            ? "border-b border-border/60 bg-muted/30"
                            : "border-b border-border/60"
                        }
                      >
                        <td className="px-4 py-3 font-medium">{draft.title}</td>
                        <td className="px-4 py-3">
                          <PlanDraftStatusBadge status={draft.status} />
                        </td>
                        <td className="px-4 py-3 tabular-nums">{itemCount}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {formatDateTime(draft.updated_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedDraftId(draft.id)}
                          >
                            Open
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </QueryStatus>

        {selectedDraftId ? (
          <PlanDraftDetailPanel
            projectId={projectId}
            campaignId={campaignId}
            draftId={selectedDraftId}
            campaignReadOnly={campaignReadOnly}
            onClose={() => setSelectedDraftId(null)}
          />
        ) : null}
      </div>
    </section>
  );
}
