"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  approveContentAsset,
  archiveContentAsset,
  submitContentAssetForReview,
} from "@/lib/api/endpoints/content-assets";
import { invalidateAfterContentAssetAction } from "@/lib/api/invalidate-after-asset-action";
import { ApiError } from "@/lib/api/errors";
import { useToast } from "@/components/providers/toast-provider";

type UseContentAssetMutationsOptions = {
  projectId: string;
  assetId: string;
  campaignId?: string | null;
  assetTitle?: string;
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

export function useContentAssetMutations({
  projectId,
  assetId,
  campaignId,
  assetTitle,
}: UseContentAssetMutationsOptions) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const label = assetTitle ? `"${assetTitle}"` : "Asset";

  const onSettled = () => {
    invalidateAfterContentAssetAction(queryClient, projectId, {
      campaignId,
      assetId,
    });
  };

  const submitReviewMutation = useMutation({
    mutationFn: () => submitContentAssetForReview(projectId, assetId),
    onSuccess: () => {
      toast.success(`${label} submitted for review`);
      onSettled();
    },
    onError: (error) => {
      toast.error(`Submit for review failed: ${mutationErrorMessage(error)}`);
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveContentAsset(projectId, assetId),
    onSuccess: () => {
      toast.success(`${label} approved`);
      onSettled();
    },
    onError: (error) => {
      toast.error(`Approve failed: ${mutationErrorMessage(error)}`);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveContentAsset(projectId, assetId),
    onSuccess: () => {
      toast.success(`${label} archived`);
      onSettled();
    },
    onError: (error) => {
      toast.error(`Archive failed: ${mutationErrorMessage(error)}`);
    },
  });

  return {
    submitReviewMutation,
    approveMutation,
    archiveMutation,
    isPending:
      submitReviewMutation.isPending ||
      approveMutation.isPending ||
      archiveMutation.isPending,
  };
}
