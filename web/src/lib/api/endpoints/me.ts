import { apiJson } from "@/lib/api/client";
import type { OperationalMetricsResponse } from "@/lib/api/types/operational-metrics";

export function fetchOwnerOperationalMetrics() {
  return apiJson<OperationalMetricsResponse>("/me/operational-metrics");
}
