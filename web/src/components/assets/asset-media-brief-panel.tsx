"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  approveMediaBrief,
  createMediaAssetFromBrief,
  createMediaBriefFromAsset,
  fetchMediaBriefs,
  submitMediaBriefForReview,
} from "@/lib/api/endpoints/media-briefs";
import { ApiError } from "@/lib/api/errors";
import { invalidateAfterContentAssetAction } from "@/lib/api/invalidate-after-asset-action";
import type { ContentAsset } from "@/lib/api/types/content-assets";

type AssetMediaBriefPanelProps = {
  projectId: string;
  asset: ContentAsset;
};

export function AssetMediaBriefPanel({ projectId, asset }: AssetMediaBriefPanelProps) {
  const queryClient = useQueryClient();
  const [linkedBriefId, setLinkedBriefId] = useState<string | null>(null);

  const briefsQuery = useQuery({
    queryKey: ["projects", projectId, "media-briefs", asset.id],
    queryFn: () => fetchMediaBriefs(projectId, { content_asset_id: asset.id }),
    enabled: asset.status === "approved",
  });

  const brief = briefsQuery.data?.[0] ?? null;
  const briefId = brief?.id ?? linkedBriefId;

  const createBriefMutation = useMutation({
    mutationFn: () => createMediaBriefFromAsset(projectId, asset.id, {}),
    onSuccess: (data) => {
      setLinkedBriefId(data.media_brief_id);
      briefsQuery.refetch();
      invalidateAfterContentAssetAction(queryClient, projectId, { assetId: asset.id });
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => submitMediaBriefForReview(projectId, briefId!),
    onSuccess: () => briefsQuery.refetch(),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveMediaBrief(projectId, briefId!),
    onSuccess: () => briefsQuery.refetch(),
  });

  const createAssetMutation = useMutation({
    mutationFn: () => createMediaAssetFromBrief(projectId, briefId!, "image"),
    onSuccess: () => briefsQuery.refetch(),
  });

  const busy =
    createBriefMutation.isPending ||
    submitMutation.isPending ||
    approveMutation.isPending ||
    createAssetMutation.isPending;

  const errMsg =
    (createBriefMutation.error instanceof ApiError && createBriefMutation.error.message) ||
    (submitMutation.error instanceof ApiError && submitMutation.error.message) ||
    (approveMutation.error instanceof ApiError && approveMutation.error.message) ||
    (createAssetMutation.error instanceof ApiError && createAssetMutation.error.message) ||
    null;

  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Media brief</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Translate approved copy into a visual task. No image or video generation in this phase.
      </p>
      {!brief && !linkedBriefId ? (
        <Button
          type="button"
          size="sm"
          className="mt-3"
          disabled={busy}
          onClick={() => createBriefMutation.mutate()}
        >
          Create Media Brief
        </Button>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground">
            Brief · {(brief?.status ?? "draft")} · {(brief?.title ?? asset.title).slice(0, 40)}
          </span>
          {brief?.status === "draft" ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy || !briefId}
              onClick={() => submitMutation.mutate()}
            >
              Submit for Review
            </Button>
          ) : null}
          {brief?.status === "review" ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy || !briefId}
              onClick={() => approveMutation.mutate()}
            >
              Approve Brief
            </Button>
          ) : null}
          {brief?.status === "approved" ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={busy || !briefId}
              onClick={() => createAssetMutation.mutate()}
            >
              Create Media Asset (placeholder)
            </Button>
          ) : null}
        </div>
      )}
      {errMsg ? <p className="mt-1 text-xs text-destructive">{errMsg}</p> : null}
    </section>
  );
}
