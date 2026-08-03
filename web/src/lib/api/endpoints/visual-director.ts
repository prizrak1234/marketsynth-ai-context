import { apiFetch, apiJson } from "@/lib/api/client";

export type VisualDirectorRequest = {
  id: string;
  owner_id: string;
  project_id: string;
  version: number;
  context_source: string;
  title: string;
  objective: string;
  scene_description: string;
  subject: string;
  style: string;
  audience: string;
  mood: string;
  aspect_ratio: string;
  visual_format: string;
  requested_variants: number;
  text_overlay: string;
  must_include: string;
  must_avoid: string;
  related_text_asset_id: string | null;
  reference_asset_ids: string[];
  language: string;
  current_run_id: string | null;
  approved_asset_id: string | null;
  approved_version_number: number | null;
  created_at: string;
  updated_at: string;
};

export type VisualDirectorRun = {
  id: string;
  status: string;
  attempt: number;
  error_code: string | null;
  error_message: string | null;
  provider: string | null;
  model: string | null;
  visual_request_id: string;
  visual_request_version: number;
};

export type VisualDirectorCandidate = {
  asset_id: string;
  visual_run_id: string;
  visual_request_id: string;
  visual_request_version: number;
  candidate_index: number;
  title: string;
  status: string;
  current_version_number: number;
  approved_version_number: number | null;
  rejected: boolean;
  stale: boolean;
  mime_type: string;
  width: number | null;
  height: number | null;
  checksum: string | null;
  content_url: string | null;
  safe_metadata: Record<string, unknown>;
};

export type VisualDirectorWorkspace = {
  request: VisualDirectorRequest | null;
  active_run: VisualDirectorRun | null;
  candidates: VisualDirectorCandidate[];
  approved_asset_id: string | null;
  approved_version_number: number | null;
  next_action: string;
  applied_skill_id?: string | null;
  applied_skill_version?: string | null;
  related_text_preview?: string | null;
};

export type VisualDirectorRequestCreate = {
  title: string;
  objective: string;
  scene_description: string;
  subject: string;
  style?: string;
  audience: string;
  mood?: string;
  aspect_ratio?: string;
  requested_variants?: number;
  text_overlay?: string;
  must_include?: string;
  must_avoid?: string;
  related_text_asset_id?: string | null;
  language?: string;
};

function base(projectId: string) {
  return `/projects/${projectId}/visual-director`;
}

export function fetchVisualDirectorWorkspace(projectId: string, requestId?: string) {
  const q = requestId ? `?request_id=${encodeURIComponent(requestId)}` : "";
  return apiJson<VisualDirectorWorkspace>(`${base(projectId)}/workspace${q}`);
}

export function listVisualDirectorRequests(projectId: string) {
  return apiJson<VisualDirectorRequest[]>(`${base(projectId)}/requests`);
}

export function createVisualDirectorRequest(
  projectId: string,
  payload: VisualDirectorRequestCreate,
) {
  return apiJson<VisualDirectorRequest>(`${base(projectId)}/requests`, {
    method: "POST",
    body: {
      visual_format: "social_post_image",
      context_source: "manual",
      aspect_ratio: "1:1",
      ...payload,
    },
  });
}

export function patchVisualDirectorRequest(
  projectId: string,
  requestId: string,
  payload: Partial<VisualDirectorRequestCreate>,
) {
  return apiJson<VisualDirectorRequest>(`${base(projectId)}/requests/${requestId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function generateVisualDirectorVariants(
  projectId: string,
  requestId: string,
  idempotencyKey?: string,
) {
  return apiJson<VisualDirectorRun>(`${base(projectId)}/requests/${requestId}/generate`, {
    method: "POST",
    body: idempotencyKey ? { idempotency_key: idempotencyKey } : {},
  });
}

export function approveVisualDirectorCandidate(
  projectId: string,
  requestId: string,
  assetId: string,
  confirmTextOverlay = false,
) {
  return apiJson<VisualDirectorCandidate>(
    `${base(projectId)}/requests/${requestId}/candidates/${assetId}/approve`,
    {
      method: "POST",
      body: { confirm_text_overlay: confirmTextOverlay },
    },
  );
}

export function rejectVisualDirectorCandidate(
  projectId: string,
  requestId: string,
  assetId: string,
) {
  return apiJson<VisualDirectorCandidate>(
    `${base(projectId)}/requests/${requestId}/candidates/${assetId}/reject`,
    { method: "POST" },
  );
}

export async function fetchVisualCandidateBlob(
  projectId: string,
  assetId: string,
): Promise<Blob> {
  const response = await apiFetch(
    `${base(projectId)}/candidates/${assetId}/content`,
  );
  if (!response.ok) {
    throw new Error(`image_fetch_failed_${response.status}`);
  }
  return response.blob();
}
