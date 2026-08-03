import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";

export function invalidateAfterCampaignChange(
  queryClient: QueryClient,
  projectId: string,
  campaignId?: string,
) {
  void queryClient.invalidateQueries({
    queryKey: ["projects", projectId, "campaigns"],
  });
  void queryClient.invalidateQueries({ queryKey: queryKeys.ownerMetrics });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.projectMetrics(projectId),
  });

  if (campaignId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaign(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignWorkflow(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignOverview(projectId, campaignId),
    });
  }
}
