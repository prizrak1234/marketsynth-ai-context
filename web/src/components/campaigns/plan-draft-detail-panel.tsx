"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PlanDraftStatusBadge } from "@/components/campaigns/plan-draft-status-badge";
import { QueryStatus } from "@/components/data/query-status";
import { useToast } from "@/components/providers/toast-provider";
import {
  archiveCampaignPlanDraft,
  fetchCampaignPlanDraft,
  generateAssetsFromPlanDraft,
} from "@/lib/api/endpoints/plan-drafts";
import {
  invalidateAfterPlanDraftChange,
  invalidateAfterPlanDraftGenerate,
} from "@/lib/api/invalidate-after-plan-draft-generate";
import { queryKeys } from "@/lib/api/query-keys";
import { ApiError } from "@/lib/api/errors";
import type { PlanContentItem } from "@/lib/api/types/plan-drafts";
import { formatDateTime } from "@/lib/format";

type PlanDraftDetailPanelProps = {
  projectId: string;
  campaignId: string;
  draftId: string;
  campaignReadOnly: boolean;
  onClose: () => void;
};

function mutationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const message = error.message;
    if (message === "plan_draft_generation_partial_state") {
      return "Partial generation: some draft assets exist but not all planned items. Resolve in API or archive and recreate the plan.";
    }
    return message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

function ContentItemsList({ items }: { items: PlanContentItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No content items.</p>;
  }
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item, index) => (
        <li
          key={`${item.title}-${index}`}
          className="rounded-md border border-border/60 p-2"
        >
          <p className="font-medium">{item.title}</p>
          <p className="text-muted-foreground">
            {item.channel} · {item.format}
            {item.scheduled_at
              ? ` · scheduled ${formatDateTime(item.scheduled_at)}`
              : ""}
          </p>
          {item.notes ? (
            <p className="mt-1 text-xs text-muted-foreground">{item.notes}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function PlanDraftDetailPanel({
  projectId,
  campaignId,
  draftId,
  campaignReadOnly,
  onClose,
}: PlanDraftDetailPanelProps) {
  const [archiveOpen, setArchiveOpen] = useState(false);
  const queryClient = useQueryClient();
  const toast = useToast();

  const draftQuery = useQuery({
    queryKey: queryKeys.campaignPlanDraft(projectId, campaignId, draftId),
    queryFn: () => fetchCampaignPlanDraft(projectId, campaignId, draftId),
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveCampaignPlanDraft(projectId, campaignId, draftId),
    onSuccess: () => {
      toast.success("Plan draft archived");
      invalidateAfterPlanDraftChange(queryClient, projectId, campaignId, draftId);
      setArchiveOpen(false);
      onClose();
    },
    onError: (error) => {
      toast.error(`Archive failed: ${mutationErrorMessage(error)}`);
    },
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      generateAssetsFromPlanDraft(projectId, campaignId, draftId),
    onSuccess: (result) => {
      if (result.already_generated) {
        toast.success(
          `Already generated — ${result.asset_ids.length} draft asset(s) linked`,
        );
      } else {
        toast.success(`Created ${result.created_count} draft asset(s)`);
      }
      invalidateAfterPlanDraftGenerate(queryClient, projectId, campaignId, draftId);
    },
    onError: (error) => {
      toast.error(`Generate failed: ${mutationErrorMessage(error)}`);
    },
  });

  const readOnly = campaignReadOnly;

  return (
    <div className="rounded-lg border border-border bg-muted/10 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold">Plan draft details</p>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      <QueryStatus query={draftQuery}>
        {(draft) => {
          const payload = draft.plan_payload ?? {};
          const items = payload.content_items ?? [];
          const isDraft = draft.status === "draft";

          return (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-medium">{draft.title}</h3>
                <PlanDraftStatusBadge status={draft.status} />
                <span className="text-xs text-muted-foreground">
                  Updated {formatDateTime(draft.updated_at)}
                </span>
              </div>

              <dl className="grid gap-2 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-muted-foreground">goal</dt>
                  <dd>{payload.goal || "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">target_audience</dt>
                  <dd>{payload.target_audience || "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">key_message</dt>
                  <dd>{payload.key_message || "—"}</dd>
                </div>
              </dl>

              <div>
                <p className="mb-2 text-sm font-medium">content_items</p>
                <ContentItemsList items={items} />
              </div>

              {isDraft && items.length > 0 ? (
                <p className="text-sm text-muted-foreground">
                  After generating, approve drafts in the{" "}
                  <Link href="/review" className="font-medium underline">
                    Review Queue
                  </Link>
                  .
                </p>
              ) : null}

              {!readOnly ? (
                <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                  {isDraft ? (
                    <>
                      <Button
                        disabled={
                          generateMutation.isPending || archiveMutation.isPending
                        }
                        onClick={() => generateMutation.mutate()}
                      >
                        {generateMutation.isPending
                          ? "Generating…"
                          : "Generate draft assets"}
                      </Button>
                      <Button
                        variant="destructive"
                        disabled={
                          generateMutation.isPending || archiveMutation.isPending
                        }
                        onClick={() => setArchiveOpen(true)}
                      >
                        Archive plan
                      </Button>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Archived plan drafts cannot generate assets.
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Archived campaign — plan drafts are read-only.
                </p>
              )}

              {generateMutation.isError ? (
                <p className="text-sm text-destructive" role="alert">
                  {mutationErrorMessage(generateMutation.error)}
                </p>
              ) : null}

              {generateMutation.data?.asset_ids.length ? (
                <div className="text-sm">
                  <p className="font-medium">Linked draft assets</p>
                  <ul className="mt-1 list-inside list-disc text-muted-foreground">
                    {generateMutation.data.asset_ids.map((assetId) => (
                      <li key={assetId}>
                        <Link
                          href={`/assets/${assetId}`}
                          className="hover:underline"
                        >
                          {assetId}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        }}
      </QueryStatus>

      <ConfirmDialog
        open={archiveOpen}
        title="Archive plan draft?"
        description="Archived plans cannot generate new assets."
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
}
