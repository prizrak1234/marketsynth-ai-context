import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";

export function invalidateAfterPublishingChannelChange(
  queryClient: QueryClient,
  projectId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: queryKeys.publishingChannels(projectId),
  });
  void queryClient.invalidateQueries({ queryKey: queryKeys.ownerMetrics });
  void queryClient.invalidateQueries({
    queryKey: queryKeys.projectMetrics(projectId),
  });
}
