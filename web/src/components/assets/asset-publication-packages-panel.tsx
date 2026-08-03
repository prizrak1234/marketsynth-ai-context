"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  createPublicationPackageFromAsset,
  fetchPublicationPackages,
} from "@/lib/api/endpoints/publication-packages";
import { ApiError } from "@/lib/api/errors";
import { invalidateAfterContentAssetAction } from "@/lib/api/invalidate-after-asset-action";
import type { ContentAsset } from "@/lib/api/types/content-assets";

const CHANNELS = ["telegram", "instagram", "linkedin", "blog"] as const;

type AssetPublicationPackagesPanelProps = {
  projectId: string;
  asset: ContentAsset;
};

export function AssetPublicationPackagesPanel({
  projectId,
  asset,
}: AssetPublicationPackagesPanelProps) {
  const queryClient = useQueryClient();
  const [channel, setChannel] = useState<(typeof CHANNELS)[number]>("telegram");
  const [linkedPackageId, setLinkedPackageId] = useState<string | null>(null);

  const packagesQuery = useQuery({
    queryKey: ["projects", projectId, "publication-packages", asset.id],
    queryFn: () =>
      fetchPublicationPackages(projectId, { content_asset_id: asset.id }),
    enabled: asset.status === "approved",
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createPublicationPackageFromAsset(projectId, asset.id, { channel }),
    onSuccess: (data) => {
      setLinkedPackageId(data.publication_package_id);
      invalidateAfterContentAssetAction(queryClient, projectId, { assetId: asset.id });
      packagesQuery.refetch();
    },
  });

  const err =
    createMutation.error instanceof ApiError ? createMutation.error.message : null;
  const existingChannels = new Set(
    (packagesQuery.data ?? []).map((pkg) => pkg.channel),
  );
  const channelTaken = existingChannels.has(channel);

  return (
    <section className="rounded-lg border border-border p-4" data-testid="legacy-publication-packages">
      <h2 className="text-sm font-semibold">Publication packages (legacy panel)</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Internal asset editor helper. Content Factory recovery uses foundation packages in
        /workspace/recovery-preview/r3 — not this legacy panel.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select
          className="h-8 rounded border border-border bg-background px-2 text-xs"
          value={channel}
          onChange={(e) => setChannel(e.target.value as (typeof CHANNELS)[number])}
        >
          {CHANNELS.map((ch) => (
            <option key={ch} value={ch} disabled={existingChannels.has(ch)}>
              {ch}
              {existingChannels.has(ch) ? " (exists)" : ""}
            </option>
          ))}
        </select>
        <Button
          type="button"
          size="sm"
          disabled={createMutation.isPending || channelTaken}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? "Creating…" : "Create Publication Package"}
        </Button>
      </div>
      {linkedPackageId ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Package created (draft) · {linkedPackageId.slice(0, 8)}…
        </p>
      ) : null}
      {err ? <p className="mt-1 text-xs text-destructive">{err}</p> : null}
      {packagesQuery.data && packagesQuery.data.length > 0 ? (
        <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
          {packagesQuery.data.map((pkg) => (
            <li key={pkg.id}>
              {pkg.channel} · {pkg.status} · {pkg.title}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
