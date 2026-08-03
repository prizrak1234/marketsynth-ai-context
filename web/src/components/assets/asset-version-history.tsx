"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { QueryStatus } from "@/components/data/query-status";
import { fetchContentAssetVersion } from "@/lib/api/endpoints/content-assets";
import { queryKeys } from "@/lib/api/query-keys";
import { formatDateTime } from "@/lib/format";
import type { ContentAssetVersion } from "@/lib/api/types/content-assets";
import { cn } from "@/lib/utils";

type AssetVersionHistoryProps = {
  projectId: string;
  assetId: string;
  versions: ContentAssetVersion[];
  currentVersionNumber: number;
};

export function AssetVersionHistory({
  projectId,
  assetId,
  versions,
  currentVersionNumber,
}: AssetVersionHistoryProps) {
  const [selectedVersion, setSelectedVersion] = useState<number | null>(
    currentVersionNumber,
  );

  const versionQuery = useQuery({
    queryKey: queryKeys.contentAssetVersion(
      projectId,
      assetId,
      selectedVersion ?? 0,
    ),
    queryFn: () =>
      fetchContentAssetVersion(projectId, assetId, selectedVersion!),
    enabled: selectedVersion !== null && selectedVersion > 0,
  });

  return (
    <section className="rounded-lg border border-border p-4">
      <h2 className="text-sm font-semibold">Version history</h2>
      <div className="mt-3 grid gap-4 lg:grid-cols-2">
        <ul className="space-y-1 text-sm">
          {versions.map((version) => {
            const selected = selectedVersion === version.version_number;
            return (
              <li key={version.version_number}>
                <button
                  type="button"
                  onClick={() => setSelectedVersion(version.version_number)}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left transition-colors",
                    selected
                      ? "bg-muted font-medium"
                      : "hover:bg-muted/60",
                  )}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span>
                      v{version.version_number}
                      {version.version_number === currentVersionNumber
                        ? " (current)"
                        : ""}{" "}
                      — {version.title}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {version.created_by_source}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(version.created_at)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="rounded-md border border-border/80 bg-muted/20 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Version preview
          </h3>
          {selectedVersion === null ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Select a version to preview.
            </p>
          ) : (
            <QueryStatus query={versionQuery}>
              {(version) => (
                <div className="mt-2 space-y-2 text-sm">
                  <p className="font-medium">{version.title}</p>
                  {version.body ? (
                    <pre className="max-h-80 overflow-auto rounded-md bg-background/80 p-3 text-xs whitespace-pre-wrap">
                      {version.body}
                    </pre>
                  ) : (
                    <p className="text-muted-foreground">No body content.</p>
                  )}
                </div>
              )}
            </QueryStatus>
          )}
        </div>
      </div>
    </section>
  );
}
