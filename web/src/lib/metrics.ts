import type { OperationalMetricsResponse } from "@/lib/api/types/operational-metrics";

export type PublishingMetrics = {
  scheduled_jobs_count?: number;
  failed_jobs_count?: number;
  next_scheduled_publication_at?: string | null;
  jobs_by_status?: Record<string, number>;
};

export function getPublishingMetrics(
  metrics: OperationalMetricsResponse,
): PublishingMetrics {
  return metrics.publishing as PublishingMetrics;
}

export function getCampaignCounts(metrics: OperationalMetricsResponse) {
  return metrics.campaigns;
}
