/** Backend BusinessVerdict DTOs (Commercial MVP P0.5). */

export type BackendVerdictType =
  | "go"
  | "conditional_go"
  | "no_go"
  | "insufficient_data";

export type BackendVerdictLifecycle =
  | "draft"
  | "under_review"
  | "approved"
  | "rejected"
  | "superseded"
  | "archived";

export type BackendVerdictDto = {
  id: string;
  owner_id: string;
  project_id: string;
  investigation_id: string;
  investigation_version: number;
  project_brief_id: string;
  project_brief_version: number;
  version: number;
  verdict_type: BackendVerdictType;
  lifecycle_status: BackendVerdictLifecycle;
  confidence_level: "high" | "medium" | "low" | "unknown";
  evidence_snapshot_id: string;
  evidence_snapshot_hash: string;
  executive_conclusion: string;
  executive_rationale: string;
  primary_business_implication: string;
  recommended_next_action: string;
  supporting_evidence_summary: string | null;
  counter_evidence_summary: string | null;
  conditions: Array<Record<string, unknown>>;
  critical_risks: Array<Record<string, unknown>>;
  assumptions: Array<Record<string, unknown>>;
  change_triggers: Array<Record<string, unknown>>;
  findings: Array<Record<string, unknown>>;
  readiness_snapshot: string;
  prepared_by_type: string;
  prepared_by_reference: string | null;
  submitted_by: string | null;
  submitted_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  supersedes_verdict_id: string | null;
  strategy_eligibility: {
    strategy_eligible: boolean;
    strategy_blocked_reason: string | null;
    open_conditions_mandatory: boolean;
    pivot_route_allowed: boolean;
    return_to_investigation: boolean;
    creates_strategy: boolean;
    creates_execution_approval: boolean;
    creates_publication_approval: boolean;
    creates_agent_run: boolean;
  };
  evidence_links: Array<{
    id: string;
    evidence_id: string;
    evidence_version: number;
    role: string;
    decision_criterion: string | null;
    materiality_at_snapshot: string;
    assessment_state_at_snapshot: string;
    confidence_at_snapshot: string;
    note: string | null;
  }>;
  evidence_snapshot: BackendEvidenceSnapshotDto | null;
  creates_strategy: boolean;
  creates_execution_approval: boolean;
  creates_publication_approval: boolean;
  creates_agent_run: boolean;
  is_execution_approval: boolean;
  is_readiness: boolean;
  created_at: string;
  updated_at: string;
};

export type BackendEvidenceSnapshotDto = {
  id: string;
  owner_id: string;
  project_id: string;
  investigation_id: string;
  snapshot_hash: string;
  evidence_ids: string[];
  evidence_versions: Record<string, number>;
  accepted_evidence_count: number;
  missing_critical_count: number;
  conflicting_critical_count: number;
  outdated_critical_count: number;
  area_coverage: Record<string, number>;
  readiness_status: string;
  verdict_readiness_contribution: string;
  created_at: string;
};
