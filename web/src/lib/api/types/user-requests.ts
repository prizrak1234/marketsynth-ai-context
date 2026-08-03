/** Backend UserRequest DTOs (Phase H1 + H2.5). */

export type UserRequestStatus =
  | "submitted"
  | "needs_clarification"
  | "routed"
  | "ready_for_draft"
  | "in_progress"
  | "completed"
  | "failed"
  | "cancelled";

export type UserRequestRouteKind =
  | "project_intake"
  | "specialist_task"
  | "clarify"
  | "unsupported";

export type UserRequestExecutionReadiness =
  | "not_applicable"
  | "needs_clarification"
  | "awaiting_knowledge"
  | "ready_for_draft"
  | "blocked";

export type BackendResearchSourceCandidate = {
  id?: string;
  url?: string;
  title?: string;
  publisher?: string;
  published_at?: string;
  authority_level?: string;
  freshness?: string;
};

export type BackendResearchRetrievalReport = {
  candidate_count?: number;
  duplicate_count?: number;
  contradiction_count?: number;
  missing_data_count?: number;
};

export type BackendResearchProviderCoverage = {
  mock_providers?: boolean;
  disclosure_ru?: string;
};

export type BackendResearchContradiction = {
  topic?: string;
  conflicting_statements?: string[];
};

export type BackendResearchCollection = {
  source_candidates?: BackendResearchSourceCandidate[];
  retrieval_report?: BackendResearchRetrievalReport;
  provider_coverage?: BackendResearchProviderCoverage;
  research_summary?: string;
  contradictions?: BackendResearchContradiction[];
  contradiction_note?: string;
  missing_data?: string[];
};

export type BackendUserRequestDto = {
  id: string;
  owner_id: string;
  text: string;
  normalized_text: string;
  selected_scenario: string | null;
  route_category: string;
  route_kind: UserRequestRouteKind;
  route_confidence: number;
  status: UserRequestStatus;
  clarification_question: string | null;
  clarification_answer: string | null;
  project_id: string | null;
  task_id: string | null;
  assigned_specialist: string | null;
  requires_project: boolean;
  avoids_investigation: boolean;
  next_href: string | null;
  next_action_label: string | null;
  assistant_message: string;
  title: string;
  source: string;
  skill_code: string | null;
  skill_version: string | null;
  capability_pack_code: string | null;
  capability_pack_version: string | null;
  knowledge_snapshot_id: string | null;
  knowledge_snapshot_hash: string | null;
  execution_readiness: UserRequestExecutionReadiness;
  missing_inputs: string[];
  quality_profile_code: string | null;
  skill_inputs: Record<string, unknown>;
  approved_knowledge_count: number;
  generated_visual_asset_ids: string[];
  generation_status: string | null;
  generation_warnings: string[];
  content_draft: BackendContentDraft | null;
  content_draft_review_status: ContentDraftReviewStatus | null;
  prompt_package_hash: string | null;
  execution_provider: string | null;
  execution_model: string | null;
  research_run_id?: string | null;
  research_collection?: BackendResearchCollection | null;
  business_idea_validation?: Record<string, unknown> | null;
  client_message_id?: string | null;
  idempotency_key?: string | null;
  conversation_id?: string | null;
  sequence_number?: number | null;
  assistant_run_id?: string | null;
  routing_decision_id?: string | null;
  chat_route?: string | null;
  created_at: string;
  updated_at: string;
};

export type ContentDraftReviewStatus =
  | "pending"
  | "accepted"
  | "revision_requested"
  | "rejected";

export type ContentDraftReviewAction =
  | "accept"
  | "request_revision"
  | "create_variant"
  | "reject";

export type ContentQualityGateDecision = "pass" | "revise" | "block";

export type BackendContentDraftQualityCheck = {
  passed: boolean;
  schema_valid: boolean;
  required_fields_present: boolean;
  locale_ok: boolean;
  no_unsupported_claims: boolean;
  no_secrets: boolean;
  checks: Record<string, boolean>;
  issues: string[];
  score: number;
  dimension_scores?: Record<string, number>;
  critical_failures?: string[];
  gate_decision?: ContentQualityGateDecision;
};

export type BackendContentClaim = {
  statement: string;
  claim_type: string;
  source_refs: string[];
  evidence_state: string;
  confidence: number;
  visible_citation_required: boolean;
  action: string;
};

export type BackendContentTextFoundation = {
  domain_items: string[];
  external_sources: string[];
  user_materials: string[];
  assumptions: string[];
  softened_or_removed_claims: string[];
};

export type BackendContentDomain = {
  primary: string;
  secondary: string[];
  confidence: number;
  labels: string[];
};

export type BackendContentDraft = {
  skill_code: string;
  hook: string;
  body: string;
  cta: string;
  variants: string[];
  assumptions: string[];
  factual_claims: string[];
  warnings: string[];
  knowledge_refs: string[];
  expertise_labels: string[];
  materials_used: string[];
  quality_check: BackendContentDraftQualityCheck;
  generation_mode: string;
  review_status: ContentDraftReviewStatus;
  status: string;
  domain?: BackendContentDomain | null;
  factuality_mode?: string;
  claims?: BackendContentClaim[];
  editorial_notes?: string[];
  text_foundation?: BackendContentTextFoundation | null;
  revision_count?: number;
};
