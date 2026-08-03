import { apiJson } from "@/lib/api/client";
import { normalizeContentAsset, normalizeContentAssetVersion } from "@/lib/api/mappers/content-assets";
import type { ContentAsset, ContentAssetVersion } from "@/lib/api/types/content-assets";

function assetPath(projectId: string, assetId: string, suffix = "") {
  return `/projects/${projectId}/content-assets/${assetId}${suffix}`;
}

function assetsCollectionPath(projectId: string, query = "") {
  return `/projects/${projectId}/content-assets${query}`;
}

export function fetchContentAssets(
  projectId: string,
  params?: { brief_id?: string; include_archived?: boolean },
) {
  const search = new URLSearchParams();
  if (params?.brief_id) search.set("brief_id", params.brief_id);
  if (params?.include_archived) search.set("include_archived", "true");
  const query = search.toString();
  return apiJson<ContentAsset[]>(assetsCollectionPath(projectId, query ? `?${query}` : "")).then(
    (rows) => rows.map((row) => normalizeContentAsset(row)),
  );
}

export type CreateContentAssetPayload = {
  type: string;
  title: string;
  body?: string;
  metadata?: Record<string, unknown>;
  status?: string;
  brief_id?: string;
  campaign_id?: string;
};

export function createContentAsset(projectId: string, payload: CreateContentAssetPayload) {
  return apiJson<ContentAsset>(assetsCollectionPath(projectId), {
    method: "POST",
    body: payload,
  }).then(normalizeContentAsset);
}

export type UpdateContentAssetPayload = {
  title?: string;
  body?: string;
  metadata?: Record<string, unknown>;
  status?: string;
};

export function updateContentAsset(
  projectId: string,
  assetId: string,
  payload: UpdateContentAssetPayload,
) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId), {
    method: "PATCH",
    body: payload,
  }).then(normalizeContentAsset);
}

export function fetchContentAsset(projectId: string, assetId: string) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId)).then(normalizeContentAsset);
}

export function fetchContentAssetVersions(projectId: string, assetId: string) {
  return apiJson<ContentAssetVersion[]>(assetPath(projectId, assetId, "/versions")).then((rows) =>
    rows.map((row) => normalizeContentAssetVersion(row)),
  );
}

export function submitContentAssetForReview(projectId: string, assetId: string) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId, "/submit-review"), {
    method: "POST",
  });
}

export function approveContentAsset(projectId: string, assetId: string) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId, "/approve"), {
    method: "POST",
  });
}

export function archiveContentAsset(projectId: string, assetId: string) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId, "/archive"), {
    method: "POST",
  });
}

export function fetchContentAssetVersion(
  projectId: string,
  assetId: string,
  versionNumber: number,
) {
  return apiJson<ContentAssetVersion>(
    assetPath(projectId, assetId, `/versions/${versionNumber}`),
  );
}

export type ManualRevisionPayload = {
  title: string;
  body: string;
  metadata_patch?: Record<string, unknown>;
};

export function createManualContentAssetRevision(
  projectId: string,
  assetId: string,
  payload: ManualRevisionPayload,
) {
  return apiJson<ContentAsset>(assetPath(projectId, assetId, "/revisions"), {
    method: "POST",
    body: payload,
  });
}

export type CreateRevisionFromApprovedPayload = {
  title?: string;
  body?: string;
  metadata?: Record<string, unknown>;
};

export function createContentAssetRevisionFromApproved(
  projectId: string,
  assetId: string,
  payload: CreateRevisionFromApprovedPayload = {},
) {
  return apiJson<ContentAsset>(
    assetPath(projectId, assetId, "/create-revision"),
    {
      method: "POST",
      body: payload,
    },
  );
}
