import type {
  AnalysisContextFields,
  AnalysisContextRecord,
} from "@/lib/api/endpoints/analysis-contexts";

const LOCAL_DRAFT_ID = "00000000-0000-0000-0000-000000000001";

/** Optimistic client-side draft shown while backend sync runs or recovers. */
export function buildLocalDraftContext(
  projectId: string,
  fields: AnalysisContextFields,
): AnalysisContextRecord {
  const now = new Date().toISOString();
  return {
    context_id: LOCAL_DRAFT_ID,
    owner_id: LOCAL_DRAFT_ID,
    project_id: projectId,
    state: "draft_entered",
    source_mode: null,
    data_source_label: null,
    idea_description: fields.idea_description ?? "",
    product_or_service: fields.product_or_service ?? null,
    target_customer: fields.target_customer ?? null,
    geography: fields.geography ?? null,
    business_model: fields.business_model ?? null,
    pricing_or_revenue_model: fields.pricing_or_revenue_model ?? null,
    current_stage: fields.current_stage ?? null,
    budget_context: fields.budget_context ?? null,
    known_competitors: fields.known_competitors ?? null,
    analysis_goal: fields.analysis_goal ?? null,
    target_customer_unknown: fields.target_customer_unknown ?? false,
    geography_unknown: fields.geography_unknown ?? false,
    confirmed_by_user: false,
    confirmed_at: null,
    input_snapshot_hash: null,
    source_snapshot_id: null,
    is_active: true,
    missing_fields: [],
    warnings: [],
    created_at: now,
    updated_at: now,
  };
}

export function isLocalDraftContext(context: AnalysisContextRecord | null): boolean {
  return context?.context_id === LOCAL_DRAFT_ID;
}
