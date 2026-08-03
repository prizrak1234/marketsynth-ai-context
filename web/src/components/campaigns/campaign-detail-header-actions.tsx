"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EditCampaignForm } from "@/components/campaigns/edit-campaign-form";
import { CampaignStatusBadge } from "@/components/campaigns/campaign-status-badge";
import { useToast } from "@/components/providers/toast-provider";
import {
  archiveCampaign,
  fetchCampaign,
} from "@/lib/api/endpoints/campaigns";
import { invalidateAfterCampaignChange } from "@/lib/api/invalidate-after-campaign-change";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/layout/page-header";
import { QueryStatus } from "@/components/data/query-status";

type CampaignDetailHeaderActionsProps = {
  projectId: string;
  campaignId: string;
  fallbackTitle: string;
};

function mutationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

export function CampaignDetailHeaderActions({
  projectId,
  campaignId,
  fallbackTitle,
}: CampaignDetailHeaderActionsProps) {
  const [editOpen, setEditOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);

  const queryClient = useQueryClient();
  const toast = useToast();
  const router = useRouter();

  const campaignQuery = useQuery({
    queryKey: queryKeys.campaign(projectId, campaignId),
    queryFn: () => fetchCampaign(projectId, campaignId),
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveCampaign(projectId, campaignId),
    onSuccess: () => {
      toast.success("Campaign archived");
      invalidateAfterCampaignChange(queryClient, projectId, campaignId);
      setArchiveOpen(false);
      router.push("/campaigns");
    },
    onError: (error) => {
      toast.error(`Archive failed: ${mutationErrorMessage(error)}`);
    },
  });

  return (
    <QueryStatus query={campaignQuery}>
      {(campaign) => {
        const isArchived = campaign.status === "archived";
        return (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <PageHeader
                title={campaign.title || fallbackTitle}
                description={
                  <span className="inline-flex items-center gap-2">
                    <span>Campaign {campaignId}</span>
                    <CampaignStatusBadge status={campaign.status} />
                  </span>
                }
              />
              <div className="flex flex-wrap gap-2">
                {!isArchived ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditOpen((open) => !open)}
                    >
                      {editOpen ? "Hide edit" : "Edit campaign"}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setArchiveOpen(true)}
                    >
                      Archive
                    </Button>
                  </>
                ) : null}
              </div>
            </div>

            {editOpen && !isArchived ? (
              <section className="rounded-lg border border-border p-4">
                <h2 className="mb-4 text-sm font-semibold">Edit campaign</h2>
                <EditCampaignForm
                  projectId={projectId}
                  campaign={campaign}
                  onClose={() => setEditOpen(false)}
                />
              </section>
            ) : null}

            <ConfirmDialog
              open={archiveOpen}
              title="Archive campaign?"
              description={`"${campaign.title}" will be archived and cannot be edited.`}
              confirmLabel="Archive"
              destructive
              loading={archiveMutation.isPending}
              onCancel={() => {
                if (!archiveMutation.isPending) {
                  setArchiveOpen(false);
                }
              }}
              onConfirm={() => archiveMutation.mutate()}
            />
          </div>
        );
      }}
    </QueryStatus>
  );
}
