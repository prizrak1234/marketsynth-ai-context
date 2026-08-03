/** CMVP.1 Business Idea Validation DTOs — PRODUCT-01.3B structured evidence. */



export type BusinessIdeaValidationVerdictKind =

  | "proceed"

  | "proceed_with_conditions"

  | "revise"

  | "reject"

  | "insufficient_evidence";



export type BusinessIdeaValidationRunStatus =
  | "pending"
  | "queued"
  | "running"
  | "succeeded"
  | "failed";

export type BivPipelineStage =
  | "normalizing_input"
  | "decomposing_queries"
  | "searching_direct"
  | "searching_indirect"
  | "searching_international"
  | "searching_local"
  | "searching_adjacent"
  | "validating_sources"
  | "extracting_evidence"
  | "synthesizing_findings"
  | "calculating_confidence"
  | "calculating_coverage"
  | "generating_verdict"
  | "building_report"
  | "completed";

export type BivCommercialVerdictKind =
  | "GO"
  | "CONDITIONAL_GO"
  | "PILOT_ONLY"
  | "HOLD"
  | "NO_GO";

export type BivRunProgress = {
  run_id: string;
  state: BusinessIdeaValidationRunStatus;
  current_stage: BivPipelineStage;
  completed_stages: BivPipelineStage[];
  started_at: string;
  updated_at: string;
  progress_percent: number;
  failure?: { error_code: string; safe_message: string } | null;
  correlation_id: string;
};

export type BivEvidenceItem = {
  evidence_id: string;
  source_url: string;
  source_title: string;
  excerpt: string;
  claim_supported: string;
  accepted: boolean;
  rejection_reason?: string | null;
};

export type BivFindingItem = {
  finding_id: string;
  category: string;
  claim: string;
  interpretation: string;
  business_impact: string;
  evidence_ids: string[];
  confidence: number;
};

export type BivCommercialVerdict = {
  kind: BivCommercialVerdictKind;
  rationale: string;
  confirmed_assumptions: string[];
  unconfirmed_assumptions: string[];
  critical_risks: string[];
  go_no_go_conditions: string[];
  confidence: number;
  next_validation_action: string;
};



export type BivResearchTerminalState =

  | "pending"

  | "running"

  | "succeeded_insufficient"

  | "succeeded_complete"

  | "failed";



export type BivEvidenceClassification =

  | "confirmed"

  | "hypothesis"

  | "research_gap"

  | "unsupported_claim";



export type BivStructuredEvidenceType =

  | "source_reference"

  | "observation"

  | "structured_fact"

  | "market_signal"

  | "competitor_signal"

  | "customer_signal"

  | "economic_signal"

  | "risk_signal"

  | "hypothesis"

  | "unsupported_claim"

  | "research_gap";



export type BivSourceQualityTier = "A" | "B" | "C" | "D";



export type BivSourceReference = {

  source_id: string;

  title: string;

  domain?: string | null;

  publisher?: string | null;

  published_at?: string | null;

  retrieved_at?: string | null;

};



export type BusinessIdeaValidationConfidence = {

  total_score: number;

  calculation_version: string;

  factors: Array<{

    name: string;

    score: number;

    weight: number;

    weighted_score: number;

  }>;

  penalties: string[];

};



export type BusinessIdeaValidationSourceSummary = {

  source_id: string;

  url: string;

  title: string;

  publisher?: string | null;

  domain?: string | null;

  retrieved_at: string;

  mcp_server_role: string;

  mcp_tool_name: string;

};



export type BusinessIdeaValidationEvidenceSummary = {

  evidence_id: string;

  source_id: string;

  category: string;

  evidence_type?: BivStructuredEvidenceType;

  classification?: BivEvidenceClassification;

  claim: string;

  observation?: string;

  inference?: string | null;

  supporting_excerpt: string;

  source_reference?: BivSourceReference | null;

  source_url: string;

  source_title: string;

  relevance_score: number;

  reliability_score: number;

  freshness_score: number;

  source_quality_tier?: BivSourceQualityTier;

  contradiction_status: string;

  limitations?: string[];

  sanitized?: boolean;

  is_search_snippet?: boolean;

};



export type BusinessIdeaValidationFinding = {

  category: string;

  title: string;

  statement: string;

  linked_evidence_ids: string[];

  is_hypothesis?: boolean;

};



export type BusinessIdeaValidationRisk = {

  title: string;

  description: string;

  severity: string;

  linked_evidence_ids: string[];

};



export type BusinessIdeaValidationNextStep = {

  id: string;

  label: string;

  action: string;

};



export type BivCoverageAttemptStatus =
  | "not_researched"
  | "not_found"
  | "found_but_irrelevant"
  | "found_but_low_quality"
  | "not_confirmed"
  | "confirmed"
  | "conflicted"
  | "user_hypothesis";

export type BivCategoryCoverageSummary = {
  category: string;
  label: string;
  executed_query?: string | null;
  coverage_status: BivCoverageAttemptStatus;
  customer_status_label: string;
  sources_found: number;
  sources_relevant: number;
  evidence_confirmed: number;
  evidence_hypothesis: number;
  stop_reason?: string | null;
};

export type BivIntakeHypothesis = {
  field: string;
  label: string;
  value: string;
  message: string;
};

export type BivRemediationQuestion = {
  question: string;
  intake_field?: string | null;
  related_categories: string[];
  semantic_group?: string | null;
};

export type BivSemanticGapGroup = {
  group_id: string;
  title: string;
  summary: string;
  related_categories: string[];
  questions: BivRemediationQuestion[];
};

export type BivResearchStopReason = {
  code: string;
  customer_message: string;
};

export type BivPartialResearchReport = {
  established_findings: string[];
  probable_signals: string[];
  user_hypotheses: BivIntakeHypothesis[];
  contradictions: string[];
  interim_conclusion: string;
};

export type BivResearchMode = "initial" | "rerun" | "refined_rerun";

export type BivCustomerSourceCitation = {
  title: string;
  url?: string | null;
  domain?: string | null;
};

export type BivConfirmedFinding = {
  headline: string;
  explanation: string;
  sources: BivCustomerSourceCitation[];
  category?: string;
};

export type BivUnconfirmedTopic = {
  topic: string;
  reason: string;
  methods_used: string[];
  result_summary: string;
  confidence_impact?: string | null;
};

export type BivDimensionConfidenceScore = {
  dimension_id: string;
  label: string;
  score: number;
};

export type BivResearchCoverageScore = {
  dimensions_researched: string[];
  overall_percent: number;
};

export type BivExecutiveSummary = {
  title: string;
  status_line: string;
  confidence_percent: number;
  primary_risk?: string | null;
  primary_advantage?: string | null;
};

export type BivStructuredResearchVerdict = {
  confirmed_summary: string[];
  unconfirmed_summary: string[];
  risks: string[];
  verification_needed: string[];
  recommendation: string;
  confidence_percent: number;
};

export type BivCustomerResearchReport = {
  executive_summary: BivExecutiveSummary;
  confirmed_findings: BivConfirmedFinding[];
  unconfirmed_topics: BivUnconfirmedTopic[];
  dimension_confidence: BivDimensionConfidenceScore[];
  overall_confidence_percent: number;
  coverage: BivResearchCoverageScore;
  clarification_questions: string[];
  structured_verdict: BivStructuredResearchVerdict;
};

export type BivPipelineMetrics = {
  discovery: {
    search_success_count: number;
    search_requests: number;
  };
  fetch: {
    fetch_success_rate: number;
    fetch_success_count: number;
    attempted_eligible_urls: number;
    eligible_urls: number;
    failures_by_outcome: Record<string, number>;
    provider_circuit_state?: Record<string, string>;
  };
};

export type BivPipelineFailure = {
  failure_code: string;
  failure_stage: string;
  retryable: boolean;
  safe_message: string;
};

export type BivInternalResearchDiagnostics = {
  search_queries: Array<{
    category: string;
    query: string;
    rationale: string;
    pipeline_phase?: string;
  }>;
  raw_research_gaps: string[];
  raw_limitations: string[];
  mcp_search_calls: number;
  mcp_fetch_calls: number;
  pipeline_phases_completed: string[];
  research_stop_reason_code?: string | null;
  pipeline_metrics?: BivPipelineMetrics | null;
  pipeline_failure?: BivPipelineFailure | null;
};

export type BivResearchGapPresentation = {
  code: string;
  message_key: string;
  customer_message: string;
  recommended_action?: string | null;
  intake_field?: string | null;
  semantic_group?: string | null;
};

export type BusinessIdeaValidationOutput = {

  investigation_id: string;

  business_verdict_id?: string | null;

  run_id?: string | null;

  owner_id?: string | null;

  project_id?: string | null;

  analysis_context_id?: string | null;

  input_snapshot_hash?: string | null;

  research_terminal_state?: BivResearchTerminalState;

  result_kind?: "complete_research" | "partial_research" | null;

  partial_failure_code?: string | null;

  partial_safe_message?: string | null;

  research_gaps?: string[];

  research_gap_items?: BivResearchGapPresentation[];

  semantic_gap_groups?: BivSemanticGapGroup[];

  remediation_questions?: BivRemediationQuestion[];

  category_coverage?: BivCategoryCoverageSummary[];

  research_stop_reason?: BivResearchStopReason | null;

  partial_report?: BivPartialResearchReport | null;

  research_plan: Array<{ category: string; query: string; rationale: string }>;

  sources: BusinessIdeaValidationSourceSummary[];

  evidence: BusinessIdeaValidationEvidenceSummary[];

  findings: BusinessIdeaValidationFinding[];

  risks: BusinessIdeaValidationRisk[];

  opportunities: Array<{ title: string; description: string; linked_evidence_ids: string[] }>;

  verdict: BusinessIdeaValidationVerdictKind;

  confidence: BusinessIdeaValidationConfidence;

  limitations: string[];

  next_steps: BusinessIdeaValidationNextStep[];

  tool_call_audit_ids: string[];
  customer_report?: BivCustomerResearchReport | null;
  internal_diagnostics?: BivInternalResearchDiagnostics | null;
  evidence_items?: BivEvidenceItem[];
  finding_items?: BivFindingItem[];
  commercial_verdict?: BivCommercialVerdict | null;
  run_progress?: BivRunProgress | null;
};



export type BusinessIdeaValidationAsyncRunAcceptedResponse = {
  run_id: string;
  user_request_id: string;
  project_id: string;
  analysis_context_id: string;
  input_snapshot_hash: string;
  status: BusinessIdeaValidationRunStatus;
  progress?: BivRunProgress | null;
  created_at: string;
  lineage_reused?: boolean;
};

export type BusinessIdeaValidationRunResponse = {

  run_id: string;

  user_request_id: string;

  project_id?: string | null;

  analysis_context_id?: string | null;

  input_snapshot_hash?: string | null;

  status: BusinessIdeaValidationRunStatus;

  output?: BusinessIdeaValidationOutput | null;

  error_code?: string | null;

  safe_message?: string | null;

  lineage_reused?: boolean;

  progress?: BivRunProgress | null;

  research_mode?: "initial" | "rerun" | "refined_rerun" | null;

  parent_run_id?: string | null;

};



export function isResearchTerminal(output: BusinessIdeaValidationOutput | null | undefined): boolean {

  if (!output?.research_terminal_state) return false;

  return (

    output.research_terminal_state === "succeeded_complete" ||

    output.research_terminal_state === "succeeded_insufficient" ||

    output.research_terminal_state === "failed"

  );

}



export function isPartialResearchOutput(

  output: BusinessIdeaValidationOutput | null | undefined,

): boolean {

  return output?.result_kind === "partial_research";

}



export function isPartialResearchRun(

  run: BusinessIdeaValidationRunResponse | null | undefined,

): boolean {

  return run?.status === "failed" && isPartialResearchOutput(run.output ?? null);

}



export function confirmedEvidence(

  evidence: BusinessIdeaValidationEvidenceSummary[],

): BusinessIdeaValidationEvidenceSummary[] {

  return evidence.filter((item) => item.classification === "confirmed" || !item.classification);

}


