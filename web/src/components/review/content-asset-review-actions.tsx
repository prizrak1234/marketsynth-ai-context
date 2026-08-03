"use client";

import { useState } from "react";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useContentAssetMutations } from "@/lib/hooks/use-content-asset-mutations";

type ContentAssetReviewActionsProps = {
  projectId: string;
  assetId: string;
  assetTitle: string;
  status: string;
  campaignId?: string | null;
  layout?: "row" | "inline";
};

export function ContentAssetReviewActions({
  projectId,
  assetId,
  assetTitle,
  status,
  campaignId,
  layout = "row",
}: ContentAssetReviewActionsProps) {
  const [archiveOpen, setArchiveOpen] = useState(false);
  const { approveMutation, archiveMutation, isPending } = useContentAssetMutations({
    projectId,
    assetId,
    campaignId,
    assetTitle,
  });

  const isDraft = status === "draft";
  const className =
    layout === "inline"
      ? "flex flex-wrap items-center gap-2"
      : "flex flex-wrap items-center justify-end gap-2";

  return (
    <>
      <div className={className}>
        <Link
          href={`/assets/${assetId}`}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Open
        </Link>
        {isDraft ? (
          <Button
            size="sm"
            disabled={isPending}
            onClick={() => approveMutation.mutate()}
          >
            {approveMutation.isPending ? "Approving…" : "Approve"}
          </Button>
        ) : null}
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => setArchiveOpen(true)}
        >
          Archive
        </Button>
      </div>

      <ConfirmDialog
        open={archiveOpen}
        title="Archive asset?"
        description={`"${assetTitle}" will be archived. This does not publish or schedule anything.`}
        confirmLabel="Archive"
        destructive
        loading={archiveMutation.isPending}
        onCancel={() => {
          if (!archiveMutation.isPending) {
            setArchiveOpen(false);
          }
        }}
        onConfirm={() => {
          archiveMutation.mutate(undefined, {
            onSuccess: () => setArchiveOpen(false),
          });
        }}
      />
    </>
  );
}
