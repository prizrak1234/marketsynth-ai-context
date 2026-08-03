import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";

export function invalidateAfterPlanDraftGenerate(
  queryClient: QueryClient,
  projectId: string,
  campaignId: string,
  draftId?: string,
) {
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignAssets(projectId, campaignId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignOverview(projectId, campaignId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignWorkflow(projectId, campaignId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.reviewQueue(projectId),
  });
  void queryClient.invalidateQueries({ queryKey: queryKeys.ownerMetrics });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.projectMetrics(projectId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignPlanDrafts(projectId, campaignId),
  });

  if (draftId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignPlanDraft(projectId, campaignId, draftId),
    });
  }
}

export function invalidateAfterPlanDraftChange(
  queryClient: QueryClient,
  projectId: string,
  campaignId: string,
  draftId?: string,
) {
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignPlanDrafts(projectId, campaignId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaignWorkflow(projectId, campaignId),
  });
  if (draftId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignPlanDraft(projectId, campaignId, draftId),
    });
  }
}
