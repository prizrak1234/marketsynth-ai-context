import { apiJson, ApiError } from "@/lib/api/client";

import type {
  BusinessIdeaValidationAsyncRunAcceptedResponse,
  BusinessIdeaValidationOutput,
  BusinessIdeaValidationRunResponse,
  BusinessIdeaValidationRunStatus,
  BivRunProgress,
} from "@/lib/api/types/business-idea-validation";

export type BusinessIdeaValidationRunPayload = {
  idempotency_key: string;
  analysis_context_id: string;
  input_snapshot_hash: string;
  research_mode?: "initial" | "rerun" | "refined_rerun";
  parent_run_id?: string;
  rerun_reason?: string;
  changed_fields?: string[];
  idea?: string;
  market?: string;
  location?: string;
  target_audience?: string;
  budget?: string;
  constraints?: string;
};

/** Legacy sync run — backend/tests only; product UI uses POST .../runs (202). */
export async function runBusinessIdeaValidation(
  userRequestId: string,
  payload: BusinessIdeaValidationRunPayload,
): Promise<BusinessIdeaValidationRunResponse> {
  return apiJson<BusinessIdeaValidationRunResponse>(
    `/user-requests/${userRequestId}/business-idea-validation/run`,
    {
      method: "POST",
      body: payload,
    },
  );
}

/** RUNTIME-01B — async research enqueue (202 Accepted). */
export async function startBusinessIdeaValidationRun(
  userRequestId: string,
  payload: BusinessIdeaValidationRunPayload,
): Promise<BusinessIdeaValidationAsyncRunAcceptedResponse> {
  return apiJson<BusinessIdeaValidationAsyncRunAcceptedResponse>(
    `/user-requests/${userRequestId}/business-idea-validation/runs`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function getBusinessIdeaValidationRun(
  userRequestId: string,
  runId: string,
): Promise<BusinessIdeaValidationRunResponse> {
  return apiJson<BusinessIdeaValidationRunResponse>(
    `/user-requests/${userRequestId}/business-idea-validation/runs/${runId}`,
  );
}

export async function getBusinessIdeaValidationRunProgress(
  userRequestId: string,
  runId: string,
): Promise<BivRunProgress> {
  return apiJson<BivRunProgress>(
    `/user-requests/${userRequestId}/business-idea-validation/runs/${runId}/progress`,
  );
}

export async function getBusinessIdeaValidation(
  userRequestId: string,
): Promise<BusinessIdeaValidationRunResponse> {
  return apiJson<BusinessIdeaValidationRunResponse>(
    `/user-requests/${userRequestId}/business-idea-validation`,
  );
}

export async function getBusinessIdeaValidationProgress(
  userRequestId: string,
): Promise<BivRunProgress> {
  return apiJson<BivRunProgress>(
    `/user-requests/${userRequestId}/business-idea-validation/progress`,
  );
}

export async function getBusinessIdeaValidationDiagnostics(
  userRequestId: string,
): Promise<Record<string, unknown>> {
  return apiJson<Record<string, unknown>>(
    `/user-requests/${userRequestId}/business-idea-validation/diagnostics`,
  );
}

export type BusinessIdeaValidationProjectHydration = {
  project_id: string;
  user_request_id: string;
  user_request_text: string;
  run_id: string;
  analysis_context_id?: string | null;
  input_snapshot_hash?: string | null;
  status: BusinessIdeaValidationRunStatus;
  output: BusinessIdeaValidationOutput;
  updated_at: string;
};

export async function getProjectBusinessIdeaValidation(
  projectId: string,
  params?: { analysis_context_id?: string; input_snapshot_hash?: string },
): Promise<BusinessIdeaValidationProjectHydration> {
  const query = new URLSearchParams();
  if (params?.analysis_context_id) {
    query.set("analysis_context_id", params.analysis_context_id);
  }
  if (params?.input_snapshot_hash) {
    query.set("input_snapshot_hash", params.input_snapshot_hash);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiJson<BusinessIdeaValidationProjectHydration>(
    `/projects/${projectId}/business-idea-validation/latest${suffix}`,
  );
}

export type BusinessIdeaValidationProjectLatestRunSummary = {
  project_id: string;
  run_id: string;
  user_request_id: string;
  status: BusinessIdeaValidationRunStatus;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  progress?: BivRunProgress | null;
  result_kind?: string | null;
  research_terminal_state?: string | null;
  safe_error_code?: string | null;
  safe_message?: string | null;
  has_output: boolean;
  retry_allowed: boolean;
  analysis_context_id?: string | null;
  input_snapshot_hash?: string | null;
};

export type ProjectLatestBivRunFetchResult =
  | { kind: "found"; summary: BusinessIdeaValidationProjectLatestRunSummary }
  | { kind: "not_found" }
  | { kind: "auth_error"; status: number }
  | { kind: "server_error"; status: number };

export async function fetchProjectLatestBivRun(
  projectId: string,
): Promise<ProjectLatestBivRunFetchResult> {
  try {
    const summary = await apiJson<BusinessIdeaValidationProjectLatestRunSummary>(
      `/projects/${projectId}/business-idea-validation/latest-run`,
    );
    return { kind: "found", summary };
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 404) {
        return { kind: "not_found" };
      }
      if (err.status === 401 || err.status === 403) {
        return { kind: "auth_error", status: err.status };
      }
      if (err.status >= 500) {
        return { kind: "server_error", status: err.status };
      }
    }
    throw err;
  }
}

export async function getProjectLatestBivRun(
  projectId: string,
): Promise<BusinessIdeaValidationProjectLatestRunSummary | null> {
  const result = await fetchProjectLatestBivRun(projectId);
  if (result.kind === "found") {
    return result.summary;
  }
  return null;
}

export function buildResearchIdempotencyKey(
  analysisContextId: string,
  inputSnapshotHash: string,
): string {
  return `biv-research-${analysisContextId}-${inputSnapshotHash.slice(0, 16)}`;
}

export function buildRerunIdempotencyKey(
  analysisContextId: string,
  inputSnapshotHash: string,
): string {
  const token =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 10)
      : `${Date.now()}`.slice(-10);
  return `biv-rerun-${analysisContextId}-${inputSnapshotHash.slice(0, 12)}-${token}`;
}

export type { BusinessIdeaValidationOutput };
