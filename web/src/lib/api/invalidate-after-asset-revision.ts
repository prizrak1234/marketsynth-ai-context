import type { QueryClient } from "@tanstack/react-query";
import {
  invalidateAfterContentAssetAction,
  type InvalidateAfterAssetActionOptions,
} from "@/lib/api/invalidate-after-asset-action";
import { queryKeys } from "@/lib/api/query-keys";

export type InvalidateAfterAssetRevisionOptions = InvalidateAfterAssetActionOptions & {
  /** When create-revision spawns a new draft asset. */
  additionalAssetIds?: string[];
};

/** Refresh read models after manual revision or create-revision-from-approved. */
export function invalidateAfterAssetRevision(
  queryClient: QueryClient,
  projectId: string,
  options?: InvalidateAfterAssetRevisionOptions,
) {
  invalidateAfterContentAssetAction(queryClient, projectId, options);

  for (const assetId of options?.additionalAssetIds ?? []) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.contentAsset(projectId, assetId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.contentAssetVersions(projectId, assetId),
    });
  }
}
