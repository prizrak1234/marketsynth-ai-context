import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";

export type InvalidateAfterAssetActionOptions = {
  campaignId?: string | null;
  assetId?: string;
};

/** Refresh read models affected by approve/archive (human UI only). */
export function invalidateAfterContentAssetAction(
  queryClient: QueryClient,
  projectId: string,
  options?: InvalidateAfterAssetActionOptions,
) {
  void queryClient.invalidateQueries({
    queryKey: queryKeys.reviewQueue(projectId),
  });
  void queryClient.invalidateQueries({ queryKey: queryKeys.ownerMetrics });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.projectMetrics(projectId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaigns(projectId),
  });

  const campaignId = options?.campaignId ?? undefined;
  if (campaignId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignWorkflow(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignOverview(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignAssets(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.publicationCalendar(projectId, campaignId),
    });
  }

  const assetId = options?.assetId;
  if (assetId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.contentAsset(projectId, assetId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.contentAssetVersions(projectId, assetId),
    });
  }
}
