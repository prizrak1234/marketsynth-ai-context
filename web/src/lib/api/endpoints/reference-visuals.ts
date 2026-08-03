/** Reference visuals API (H2.6A-R). */

import { apiJson } from "@/lib/api/client";
import { getApiBaseUrl, getApiKey } from "@/lib/api/config";

export type ReferenceSetDto = {
  id: string;
  title: string;
  subject_type: string;
  status: string;
  reference_asset_ids: string[];
  primary_reference_id: string | null;
  consent_confirmed: boolean;
  identity_notes: string | null;
  immutable_traits: string[];
  allowed_variations?: string[];
  forbidden_changes?: string[];
};

export type ReferenceAssetDto = {
  id: string;
  original_filename: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  quality_status: string;
  quality_notes: string | null;
  asset_purpose: string;
  asset_purposes?: string[];
  storage_uri: string | null;
  attach_status?: string | null;
  attach_message?: string | null;
};

export type ReferenceLimitsDto = {
  max_count: number;
  max_bytes_per_file: number;
  max_total_bytes: number;
  min_width: number;
  min_height: number;
  provider_max_images: number;
  accepted_mime: string[];
  identity_promise: string;
  honest_copy_ru: string;
};

export type ReferenceSelectionRoleDto = {
  reference_id: string;
  purpose: string;
  group: string;
  role_label: string;
  is_primary: boolean;
  selected: boolean;
  exclusion_reason: string | null;
};

export type ReferenceSelectionDto = {
  max_provider_references: number;
  selected_reference_ids: string[];
  excluded_reference_ids: string[];
  exclusion_reasons?: Record<string, string>;
  /** @deprecated use exclusion_reasons */
  exclusion_reason?: string | null;
  selection_summary: string;
  identity_selected_ids?: string[];
  appearance_selected_ids?: string[];
  scene_selected_ids?: string[];
  identity_selected_count?: number;
  style_selected_count?: number;
  excluded_count?: number;
  stored_count?: number;
  roles?: ReferenceSelectionRoleDto[];
  transmitted_reference_ids?: string[];
  primary_reference_id?: string | null;
};

const ACCEPT =
  "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp";

export function referenceAcceptAttr(): string {
  return ACCEPT;
}

export async function fetchReferenceLimits(): Promise<ReferenceLimitsDto> {
  return apiJson("/reference-visual-assets/limits");
}

export async function listReferenceSets(limit = 20): Promise<ReferenceSetDto[]> {
  return apiJson(`/reference-sets?limit=${limit}`);
}

export async function getReferenceSet(setId: string): Promise<ReferenceSetDto> {
  return apiJson(`/reference-sets/${setId}`);
}

export async function createReferenceSet(body: {
  title: string;
  subject_type: string;
  consent_confirmed: boolean;
  user_request_id?: string | null;
  immutable_traits?: string[];
  identity_notes?: string | null;
}): Promise<ReferenceSetDto> {
  return apiJson("/reference-sets", { method: "POST", body });
}

export async function patchReferenceSet(
  setId: string,
  body: {
    primary_reference_id?: string | null;
    consent_confirmed?: boolean;
    immutable_traits?: string[];
    allowed_variations?: string[];
    forbidden_changes?: string[];
    identity_notes?: string | null;
    subject_type?: string;
  },
): Promise<ReferenceSetDto> {
  return apiJson(`/reference-sets/${setId}`, { method: "PATCH", body });
}

export async function patchReferenceAsset(
  assetId: string,
  body: {
    asset_purpose?: string;
    asset_purposes?: string[];
  },
): Promise<ReferenceAssetDto> {
  return apiJson(`/reference-visual-assets/${assetId}`, { method: "PATCH", body });
}

export async function listReferenceSetAssets(
  setId: string,
): Promise<ReferenceAssetDto[]> {
  return apiJson(`/reference-sets/${setId}/assets`);
}

export async function fetchReferenceSelection(
  setId: string,
): Promise<ReferenceSelectionDto> {
  return apiJson(`/reference-sets/${setId}/selection`);
}

export async function uploadReferenceAsset(
  setId: string,
  file: File,
  opts: {
    asset_purpose?: string;
    subject_type?: string;
    consent_confirmed?: boolean;
  } = {},
): Promise<ReferenceAssetDto> {
  const form = new FormData();
  form.append("file", file);
  form.append("asset_purpose", opts.asset_purpose || "other");
  form.append("subject_type", opts.subject_type || "mixed");
  form.append("consent_confirmed", opts.consent_confirmed ? "true" : "false");

  const headers = new Headers();
  const apiKey = getApiKey();
  if (apiKey) {
    headers.set("Authorization", `Bearer ${apiKey}`);
  }
  // Do not set Content-Type — browser sets multipart boundary.

  const response = await fetch(
    `${getApiBaseUrl()}/reference-sets/${setId}/assets`,
    {
      method: "POST",
      body: form,
      credentials: "include",
      headers,
      cache: "no-store",
    },
  );
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const body =
      typeof err === "object" && err !== null
        ? (err as {
            error_code?: string;
            safe_message?: string;
            detail?: string | { error_code?: string; safe_message?: string };
          })
        : {};
    const nested =
      typeof body.detail === "object" && body.detail !== null ? body.detail : null;
    const code = String(body.error_code || nested?.error_code || "");
    const safe = String(
      body.safe_message || nested?.safe_message || "",
    ).trim();
    // Prefer human-readable message; never surface raw codes like duplicate_checksum.
    const localized =
      code === "duplicate_checksum"
        ? "Этот файл уже добавлен."
        : code === "reference_binding_failure"
          ? "Не удалось применить референсы. Генерация без них не выполнялась."
          : null;
    const detail =
      safe ||
      localized ||
      (typeof body.detail === "string" ? body.detail : "") ||
      `Upload failed (${response.status})`;
    throw new Error(detail);
  }
  return (await response.json()) as ReferenceAssetDto;
}

export function referenceContentUrl(assetId: string): string {
  return `${getApiBaseUrl()}/reference-visual-assets/${assetId}/content`;
}
