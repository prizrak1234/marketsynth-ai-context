"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/providers/toast-provider";
import { createManualContentAssetRevision } from "@/lib/api/endpoints/content-assets";
import { invalidateAfterAssetRevision } from "@/lib/api/invalidate-after-asset-revision";
import { ApiError } from "@/lib/api/errors";
import type { ContentAsset } from "@/lib/api/types/content-assets";

type AssetDraftRevisionEditorProps = {
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

export function AssetDraftRevisionEditor({
  projectId,
  asset,
}: AssetDraftRevisionEditorProps) {
  const [title, setTitle] = useState(asset.title);
  const [body, setBody] = useState(asset.body ?? "");
  const [clientError, setClientError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    setTitle(asset.title);
    setBody(asset.body ?? "");
  }, [asset.id, asset.title, asset.body, asset.current_version_number]);

  const saveMutation = useMutation({
    mutationFn: () =>
      createManualContentAssetRevision(projectId, asset.id, {
        title: title.trim(),
        body,
        metadata_patch: {},
      }),
    onSuccess: (updated) => {
      toast.success(`Revision saved (v${updated.current_version_number})`);
      invalidateAfterAssetRevision(queryClient, projectId, {
        campaignId: asset.campaign_id,
        assetId: asset.id,
      });
      setClientError(null);
    },
    onError: (error) => {
      const message = mutationErrorMessage(error);
      setClientError(message);
      toast.error(`Save revision failed: ${message}`);
    },
  });

  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Edit draft content</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Saving creates a new draft version. Does not approve, schedule, or publish.
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
          saveMutation.mutate();
        }}
      >
        <div className="space-y-1">
          <label htmlFor="asset-draft-title" className="text-sm font-medium">
            Title
          </label>
          <input
            id="asset-draft-title"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-background px-3 text-sm"
            disabled={saveMutation.isPending}
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="asset-draft-body" className="text-sm font-medium">
            Body
          </label>
          <textarea
            id="asset-draft-body"
            rows={12}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm"
            disabled={saveMutation.isPending}
          />
        </div>
        {clientError ? (
          <p className="text-sm text-destructive" role="alert">
            {clientError}
          </p>
        ) : null}
        <div>
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Saving…" : "Create revision"}
          </Button>
        </div>
      </form>
    </section>
  );
}
