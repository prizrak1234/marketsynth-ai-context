import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";

export type InvalidateAfterPublicationJobOptions = {
  campaignId?: string | null;
  assetId?: string;
};

function invalidatePublicationReadModels(
  queryClient: QueryClient,
  projectId: string,
  options: InvalidateAfterPublicationJobOptions,
) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.ownerMetrics });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.projectMetrics(projectId),
  });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.campaigns(projectId),
  });

  const assetId = options.assetId;
  if (assetId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.contentAsset(projectId, assetId),
    });
  }

  const campaignId = options.campaignId ?? undefined;
  if (campaignId) {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignWorkflow(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignOverview(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.publicationCalendar(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignPublicationJobs(projectId, campaignId),
    });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.campaignAssets(projectId, campaignId),
    });
  } else {
    void queryClient.invalidateQueries({
      queryKey: ["projects", projectId, "publication-calendar"],
    });
  }
}

/** @deprecated Use invalidateAfterPublicationJobChange */
export function invalidateAfterPublicationSchedule(
  queryClient: QueryClient,
  projectId: string,
  options: InvalidateAfterPublicationJobOptions & { assetId: string },
) {
  invalidatePublicationReadModels(queryClient, projectId, options);
}

export function invalidateAfterPublicationJobChange(
  queryClient: QueryClient,
  projectId: string,
  options: InvalidateAfterPublicationJobOptions,
) {
  invalidatePublicationReadModels(queryClient, projectId, options);
}
