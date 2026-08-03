import { apiFetch, apiJson } from "@/lib/api/client";
import type {
  PublicationJob,
  PublicationJobCreateBody,
  PublicationJobRescheduleBody,
  PublishingChannel,
  PublishingChannelCreateBody,
  PublishingChannelUpdateBody,
} from "@/lib/api/types/publishing";

function jobPath(projectId: string, jobId: string, suffix = "") {
  return `/projects/${projectId}/publication-jobs/${jobId}${suffix}`;
}

function channelPath(projectId: string, channelId = "") {
  return `/projects/${projectId}/publishing-channels${channelId ? `/${channelId}` : ""}`;
}

export function fetchPublishingChannels(
  projectId: string,
  params?: { includeArchived?: boolean },
) {
  const search = new URLSearchParams({ limit: "100" });
  if (params?.includeArchived) {
    search.set("include_archived", "true");
  }
  return apiJson<PublishingChannel[]>(
    `${channelPath(projectId)}?${search.toString()}`,
  );
}

export function createPublishingChannel(
  projectId: string,
  body: PublishingChannelCreateBody,
) {
  return apiJson<PublishingChannel>(channelPath(projectId), {
    method: "POST",
    body,
  });
}

export function updatePublishingChannel(
  projectId: string,
  channelId: string,
  body: PublishingChannelUpdateBody,
) {
  return apiJson<PublishingChannel>(channelPath(projectId, channelId), {
    method: "PATCH",
    body,
  });
}

export function archivePublishingChannel(projectId: string, channelId: string) {
  return apiFetch(channelPath(projectId, channelId), { method: "DELETE" });
}

export function createPublicationJob(
  projectId: string,
  body: PublicationJobCreateBody,
) {
  return apiJson<PublicationJob>(`/projects/${projectId}/publication-jobs`, {
    method: "POST",
    body,
  });
}

export function cancelPublicationJob(projectId: string, jobId: string) {
  return apiJson<PublicationJob>(jobPath(projectId, jobId, "/cancel"), {
    method: "POST",
  });
}

export function reschedulePublicationJob(
  projectId: string,
  jobId: string,
  body: PublicationJobRescheduleBody,
) {
  return apiJson<PublicationJob>(jobPath(projectId, jobId, "/reschedule"), {
    method: "POST",
    body,
  });
}
