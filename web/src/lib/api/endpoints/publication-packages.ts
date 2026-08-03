import { apiJson } from "@/lib/api/client";
import type {
  CreatePublicationPackageFromAssetResponse,
  PublicationPackage,
} from "@/lib/api/types/publication-packages";

function packagesPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/publication-packages${suffix}`;
}

export function fetchPublicationPackages(
  projectId: string,
  params?: { content_asset_id?: string },
) {
  const search = new URLSearchParams();
  if (params?.content_asset_id) {
    search.set("content_asset_id", params.content_asset_id);
  }
  const query = search.toString();
  return apiJson<PublicationPackage[]>(
    `${packagesPath(projectId)}${query ? `?${query}` : ""}`,
  );
}

export type CreatePublicationPackagePayload = {
  channel: string;
  title?: string;
  body?: string;
  cta?: string;
  metadata?: Record<string, unknown>;
};

export function createPublicationPackageFromAsset(
  projectId: string,
  assetId: string,
  payload: CreatePublicationPackagePayload,
) {
  return apiJson<CreatePublicationPackageFromAssetResponse>(
    `/projects/${projectId}/content-assets/${assetId}/create-publication-package`,
    { method: "POST", body: payload },
  );
}

export function fetchPublicationPackage(projectId: string, packageId: string) {
  return apiJson<PublicationPackage>(packagesPath(projectId, `/${packageId}`));
}

export function submitPublicationPackageForReview(projectId: string, packageId: string) {
  return apiJson<PublicationPackage>(
    packagesPath(projectId, `/${packageId}/submit-review`),
    { method: "POST" },
  );
}

export function approvePublicationPackage(projectId: string, packageId: string) {
  return apiJson<PublicationPackage>(packagesPath(projectId, `/${packageId}/approve`), {
    method: "POST",
  });
}

export function archivePublicationPackage(projectId: string, packageId: string) {
  return apiJson<PublicationPackage>(packagesPath(projectId, `/${packageId}/archive`), {
    method: "POST",
  });
}
