import { apiJson } from "@/lib/api/client";

export type ContentDirectorRequest = {
  id: string;
  owner_id: string;
  project_id: string;
  version: number;
  context_source: string;
  title: string;
  objective: string;
  channel: string;
  content_type: string;
  audience_description: string;
  key_message: string;
  offer_value_proposition: string;
  tone: string;
  language: string;
  length: string;
  cta: string;
  must_include: string;
  must_avoid: string;
  requested_variants: number;
  current_run_id: string | null;
  approved_asset_id: string | null;
  approved_version_number: number | null;
  created_at: string;
  updated_at: string;
};

export type ContentDirectorRun = {
  id: string;
  status: string;
  attempt: number;
  error_code: string | null;
  error_message: string | null;
  provider: string | null;
  model: string | null;
  content_request_id: string;
  content_request_version: number;
};

export type ContentDirectorCandidate = {
  asset_id: string;
  content_run_id: string;
  content_request_id: string;
  content_request_version: number;
  candidate_index: number;
  title: string;
  body: string;
  status: string;
  current_version_number: number;
  approved_version_number: number | null;
  rejected: boolean;
};

export type ContentDirectorWorkspace = {
  request: ContentDirectorRequest | null;
  active_run: ContentDirectorRun | null;
  candidates: ContentDirectorCandidate[];
  approved_asset_id: string | null;
  approved_version_number: number | null;
  next_action: string;
  applied_skill_id?: string | null;
  applied_skill_version?: string | null;
};

export type ContentDirectorRequestCreate = {
  title: string;
  objective: string;
  audience_description: string;
  key_message: string;
  offer_value_proposition?: string;
  tone?: string;
  language?: string;
  length?: string;
  cta?: string;
  must_include?: string;
  must_avoid?: string;
  requested_variants?: number;
  channel?: string;
  content_type?: string;
  context_source?: string;
};

function base(projectId: string) {
  return `/projects/${projectId}/content-director`;
}

export function fetchContentDirectorWorkspace(projectId: string, requestId?: string) {
  const q = requestId ? `?request_id=${encodeURIComponent(requestId)}` : "";
  return apiJson<ContentDirectorWorkspace>(`${base(projectId)}/workspace${q}`);
}

export function listContentDirectorRequests(projectId: string) {
  return apiJson<ContentDirectorRequest[]>(`${base(projectId)}/requests`);
}

export function createContentDirectorRequest(
  projectId: string,
  payload: ContentDirectorRequestCreate,
) {
  return apiJson<ContentDirectorRequest>(`${base(projectId)}/requests`, {
    method: "POST",
    body: {
      channel: "telegram",
      content_type: "telegram_post",
      context_source: "manual",
      ...payload,
    },
  });
}

export function patchContentDirectorRequest(
  projectId: string,
  requestId: string,
  payload: Partial<ContentDirectorRequestCreate>,
) {
  return apiJson<ContentDirectorRequest>(`${base(projectId)}/requests/${requestId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function generateContentDirectorVariants(
  projectId: string,
  requestId: string,
  idempotencyKey?: string,
) {
  return apiJson<ContentDirectorRun>(`${base(projectId)}/requests/${requestId}/generate`, {
    method: "POST",
    body: idempotencyKey ? { idempotency_key: idempotencyKey } : {},
  });
}

export function editContentDirectorCandidate(
  projectId: string,
  requestId: string,
  assetId: string,
  payload: { title?: string; body: string },
) {
  return apiJson<ContentDirectorCandidate>(
    `${base(projectId)}/requests/${requestId}/candidates/${assetId}`,
    { method: "PATCH", body: payload },
  );
}

export function approveContentDirectorCandidate(
  projectId: string,
  requestId: string,
  assetId: string,
) {
  return apiJson<ContentDirectorCandidate>(
    `${base(projectId)}/requests/${requestId}/candidates/${assetId}/approve`,
    { method: "POST", body: {} },
  );
}

export function rejectContentDirectorCandidate(
  projectId: string,
  requestId: string,
  assetId: string,
) {
  return apiJson<ContentDirectorCandidate>(
    `${base(projectId)}/requests/${requestId}/candidates/${assetId}/reject`,
    { method: "POST" },
  );
}
