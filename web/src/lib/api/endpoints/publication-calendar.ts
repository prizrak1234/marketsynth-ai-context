import { apiJson } from "@/lib/api/client";
import type { PublicationCalendarEntry } from "@/lib/api/types/campaigns";

export function fetchPublicationCalendar(
  projectId: string,
  params?: {
    campaignId?: string;
    limit?: number;
  },
) {
  const search = new URLSearchParams();
  if (params?.campaignId) {
    search.set("campaign_id", params.campaignId);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  return apiJson<PublicationCalendarEntry[]>(
    `/projects/${projectId}/publication-calendar${query ? `?${query}` : ""}`,
  );
}
