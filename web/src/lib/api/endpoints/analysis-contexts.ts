import { ApiError, apiJson } from "@/lib/api/client";

export type AnalysisContextState =
  | "empty"
  | "draft_entered"
  | "hydrated_unconfirmed"
  | "confirmed"
  | "editing"
  | "analysis_requested"
  | "analyzing"
  | "completed"
  | "blocked";

export type AnalysisContextRecord = {
  context_id: string;
  owner_id: string;
  project_id: string;
  state: AnalysisContextState;
  source_mode: string | null;
  data_source_label: string | null;
  idea_description: string;
  product_or_service: string | null;
  target_customer: string | null;
  geography: string | null;
  business_model: string | null;
  pricing_or_revenue_model: string | null;
  current_stage: string | null;
  budget_context: string | null;
  known_competitors: string | null;
  analysis_goal: string | null;
  target_customer_unknown: boolean;
  geography_unknown: boolean;
  confirmed_by_user: boolean;
  confirmed_at: string | null;
  input_snapshot_hash: string | null;
  source_snapshot_id: string | null;
  is_active: boolean;
  missing_fields: string[];
  warnings: string[];
  created_at: string;
  updated_at: string;
};

export type AnalysisContextFields = {
  idea_description?: string;
  product_or_service?: string | null;
  target_customer?: string | null;
  geography?: string | null;
  business_model?: string | null;
  pricing_or_revenue_model?: string | null;
  current_stage?: string | null;
  budget_context?: string | null;
  known_competitors?: string | null;
  analysis_goal?: string | null;
  target_customer_unknown?: boolean;
  geography_unknown?: boolean;
};

export type AnalysisContextCurrentResponse = {
  project_id: string;
  context: AnalysisContextRecord | null;
  has_completed_analysis: boolean;
  completed_run_id: string | null;
};

export type AnalysisContextStartNewResponse = {
  project_id: string;
  context: AnalysisContextRecord;
};

export async function getCurrentAnalysisContext(projectId: string) {
  return apiJson<AnalysisContextCurrentResponse>(
    `/projects/${projectId}/analysis-contexts/current`,
  );
}

export async function createAnalysisContextDraft(
  projectId: string,
  body: AnalysisContextFields,
) {
  return apiJson<AnalysisContextRecord>(`/projects/${projectId}/analysis-contexts`, {
    method: "POST",
    body,
  });
}

/** Retry once with a fresh project when stored project id is stale or route missing. */
export async function createAnalysisContextDraftResilient(
  projectId: string,
  body: AnalysisContextFields,
  options?: { recreateProject?: () => Promise<string> },
): Promise<{ draft: AnalysisContextRecord; projectId: string }> {
  try {
    const draft = await createAnalysisContextDraft(projectId, body);
    return { draft, projectId };
  } catch (err) {
    if (!(err instanceof ApiError) || !options?.recreateProject) {
      throw err;
    }
    const retriable =
      err.status === 404 ||
      err.errorCode === "project_not_found" ||
      err.errorCode === "not_found" ||
      err.message === "Not Found" ||
      err.message === "not_found";
    if (!retriable) {
      throw err;
    }
    const freshProjectId = await options.recreateProject();
    const draft = await createAnalysisContextDraft(freshProjectId, body);
    return { draft, projectId: freshProjectId };
  }
}

export async function confirmAnalysisContext(
  projectId: string,
  contextId: string,
  inputSnapshotHash?: string,
) {
  return apiJson<AnalysisContextRecord>(
    `/projects/${projectId}/analysis-contexts/${contextId}/confirm`,
    {
      method: "POST",
      body: inputSnapshotHash ? { input_snapshot_hash: inputSnapshotHash } : {},
    },
  );
}

export async function editAnalysisContext(
  projectId: string,
  contextId: string,
  body: AnalysisContextFields,
) {
  return apiJson<AnalysisContextRecord>(
    `/projects/${projectId}/analysis-contexts/${contextId}/edit`,
    {
      method: "POST",
      body,
    },
  );
}

export async function startNewAnalysisContext(projectId: string) {
  return apiJson<AnalysisContextStartNewResponse>(
    `/projects/${projectId}/analysis-contexts/start-new`,
    { method: "POST", body: {} },
  );
}
