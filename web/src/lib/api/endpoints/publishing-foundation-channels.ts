import { apiJson } from "@/lib/api/client";
import type {
  CreatePublishingFoundationChannelPayload,
  PublishingFoundationChannel,
  UpdatePublishingFoundationChannelPayload,
} from "@/lib/api/types/publishing-foundation-channels";

function channelsPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/publishing-foundation/channels${suffix}`;
}

export function fetchPublishingFoundationChannels(
  projectId: string,
  params?: { channel_type?: string; status?: string; include_archived?: boolean },
) {
  const search = new URLSearchParams();
  if (params?.channel_type) search.set("channel_type", params.channel_type);
  if (params?.status) search.set("status", params.status);
  if (params?.include_archived) search.set("include_archived", "true");
  const query = search.toString();
  return apiJson<PublishingFoundationChannel[]>(
    `${channelsPath(projectId)}${query ? `?${query}` : ""}`,
  );
}

export function createPublishingFoundationChannel(
  projectId: string,
  payload: CreatePublishingFoundationChannelPayload,
) {
  return apiJson<PublishingFoundationChannel>(channelsPath(projectId), {
    method: "POST",
    body: payload,
  });
}

export function updatePublishingFoundationChannel(
  projectId: string,
  channelId: string,
  payload: UpdatePublishingFoundationChannelPayload,
) {
  return apiJson<PublishingFoundationChannel>(
    channelsPath(projectId, `/${channelId}`),
    { method: "PATCH", body: payload },
  );
}
