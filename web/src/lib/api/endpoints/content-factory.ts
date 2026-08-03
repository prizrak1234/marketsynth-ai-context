import { apiJson } from "@/lib/api/client";

export type ContentFactoryBriefPayload = {
  topic: string;
  goal: string;
  audience: string;
  channel: string;
  period?: string;
  frequency?: string;
  format?: string;
  tone_brand_constraints?: string;
  source_materials?: string;
  idempotency_key?: string;
};

export type ContentFactoryProviderReadiness = {
  ready: boolean;
  blocked_reason?: string | null;
  blocked_message_ru?: string | null;
  provider?: string | null;
  model?: string | null;
  estimated_input_tokens_min?: number | null;
  estimated_input_tokens_max?: number | null;
  mock_provider?: boolean;
};

export type ContentFactoryGenerationStage =
  | "preparing_content_plan"
  | "handing_to_copywriter"
  | "forming_materials"
  | "verifying_result"
  | "completed"
  | "blocked"
  | "failed";

export type ContentFactoryGenerationStep = "prepare_plan" | "copywriter" | "finalize" | "all";

export type ContentFactoryGeneratedAssetLineage = {
  content_asset_id: string;
  content_slot: number;
  title: string;
  status: string;
  source_marketing_plan_id: string;
  source_execution_run_id: string;
  source_content_planner_output_id: string;
  source_copywriter_output_id: string;
  llm_provider?: string | null;
  llm_model?: string | null;
};

export type ContentFactoryGenerateMaterialsResponse = {
  stage: ContentFactoryGenerationStage;
  safe_message: string;
  marketing_plan_id?: string | null;
  execution_run_id?: string | null;
  content_planner_output_id?: string | null;
  copywriter_output_id?: string | null;
  content_assets: ContentFactoryGeneratedAssetLineage[];
  blocked_reason?: string | null;
};

function contentFactoryPath(projectId: string, suffix = "") {
  return `/projects/${projectId}/content-factory${suffix}`;
}

export function fetchContentFactoryProviderReadiness(projectId: string) {
  return apiJson<ContentFactoryProviderReadiness>(
    contentFactoryPath(projectId, "/provider-readiness"),
  );
}

export function generateContentFactoryMaterials(
  projectId: string,
  payload: {
    brief: ContentFactoryBriefPayload;
    execution_run_id?: string | null;
    step?: ContentFactoryGenerationStep;
    idempotency_key?: string | null;
  },
) {
  return apiJson<ContentFactoryGenerateMaterialsResponse>(
    contentFactoryPath(projectId, "/generate-materials"),
    {
      method: "POST",
      body: {
        brief: payload.brief,
        execution_run_id: payload.execution_run_id ?? null,
        step: payload.step ?? "all",
        idempotency_key: payload.idempotency_key ?? null,
      },
    },
  );
}

export function fetchContentFactoryGenerationStatus(
  projectId: string,
  executionRunId: string,
) {
  return apiJson<ContentFactoryGenerateMaterialsResponse>(
    contentFactoryPath(projectId, `/generation-runs/${executionRunId}/status`),
  );
}
