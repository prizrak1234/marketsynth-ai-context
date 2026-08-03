"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { createContentAssetRevisionFromApproved } from "@/lib/api/endpoints/content-assets";
import { invalidateAfterAssetRevision } from "@/lib/api/invalidate-after-asset-revision";
import { ApiError } from "@/lib/api/errors";
import type { ContentAsset } from "@/lib/api/types/content-assets";

type AssetApprovedRevisionPanelProps = {
  projectId: string;
  asset: ContentAsset;
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

export function AssetApprovedRevisionPanel({
  projectId,
  asset,
}: AssetApprovedRevisionPanelProps) {
  const router = useRouter();
  const [title, setTitle] = useState(asset.title);
  const [body, setBody] = useState(asset.body ?? "");
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  const createMutation = useMutation({
    mutationFn: () =>
      createContentAssetRevisionFromApproved(projectId, asset.id, {
        title: title.trim() || undefined,
        body: body || undefined,
      }),
    onSuccess: (revision) => {
      toast.success("Draft revision created from approved asset");
      invalidateAfterAssetRevision(queryClient, projectId, {
        campaignId: asset.campaign_id,
        assetId: asset.id,
        additionalAssetIds: [revision.id],
      });
      setClientError(null);
      router.push(`/assets/${revision.id}`);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Create revision failed: ${message}`);
    },
  });

  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Create revision from approved</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Opens a new draft asset. This approved asset is unchanged. No auto-approve or
        publish.
      </p>
      <form
        className="mt-4 grid max-w-2xl gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          setClientError(null);
          if (!title.trim()) {
            setClientError("Title is required");
            return;
          }
          createMutation.mutate();
        }}
      >
        <div className="space-y-1">
          <label htmlFor="asset-rev-title" className="text-sm font-medium">
            Title for new draft
          </label>
          <input
            id="asset-rev-title"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
            disabled={createMutation.isPending}
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="asset-rev-body" className="text-sm font-medium">
            Body for new draft
          </label>
          <textarea
            id="asset-rev-body"
            rows={12}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm"
            disabled={createMutation.isPending}
          />
        </div>
        {clientError ? (
          <p className="text-sm text-destructive" role="alert">
            {clientError}
          </p>
        ) : null}
        <div>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending
              ? "Creating…"
              : "Create revision from approved"}
          </Button>
        </div>
      </form>
    </section>
  );
}
