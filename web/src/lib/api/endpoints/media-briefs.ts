import { apiJson } from "@/lib/api/client";
import type {
  CreateMediaAssetFromBriefResponse,
  CreateMediaBriefFromAssetResponse,
  MediaBrief,
} from "@/lib/api/types/media-briefs";

function briefsPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/media-briefs${suffix}`;
}

export function fetchMediaBriefs(
  projectId: string,
  params?: { content_asset_id?: string },
) {
  const search = new URLSearchParams();
  if (params?.content_asset_id) {
    search.set("content_asset_id", params.content_asset_id);
  }
  const query = search.toString();
  return apiJson<MediaBrief[]>(`${briefsPath(projectId)}${query ? `?${query}` : ""}`);
}

export function createMediaBriefFromAsset(
  projectId: string,
  assetId: string,
  payload: Record<string, unknown> = {},
) {
  return apiJson<CreateMediaBriefFromAssetResponse>(
    `/projects/${projectId}/content-assets/${assetId}/create-media-brief`,
    { method: "POST", body: payload },
  );
}

export function submitMediaBriefForReview(projectId: string, briefId: string) {
  return apiJson<MediaBrief>(briefsPath(projectId, `/${briefId}/submit-review`), {
    method: "POST",
  });
}

export function approveMediaBrief(projectId: string, briefId: string) {
  return apiJson<MediaBrief>(briefsPath(projectId, `/${briefId}/approve`), {
    method: "POST",
  });
}

export function createMediaAssetFromBrief(
  projectId: string,
  briefId: string,
  mediaType: string,
) {
  return apiJson<CreateMediaAssetFromBriefResponse>(
    briefsPath(projectId, `/${briefId}/create-media-asset`),
    { method: "POST", body: { media_type: mediaType } },
  );
}
