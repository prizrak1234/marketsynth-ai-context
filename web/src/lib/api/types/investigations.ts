/** Commercial MVP P0.2 — Investigation API types */

export type InvestigationLifecycleStatus =
  | "draft"
  | "ready"
  | "active"
  | "blocked"
  | "under_review"
  | "completed"
  | "cancelled"
  | "superseded";

export type InvestigationReadinessStatus =
  | "not_ready"
  | "conditionally_ready"
  | "ready_for_review";

export type InvestigationStageId =
  | "project_context"
  | "market_research"
  | "competitor_analysis"
  | "audience_analysis"
  | "demand_signals"
  | "economics"
  | "risk_assessment"
  | "evidence_review"
  | "verdict_preparation";

export type InvestigationStageStatus =
  | "not_started"
  | "queued"
  | "in_progress"
  | "blocked"
  | "completed"
  | "needs_review";

export type InvestigationStageStateDto = {
  stage_id: InvestigationStageId;
  status: InvestigationStageStatus;
  blocked_reason?: string | null;
};

export type InvestigationDto = {
  id: string;
  owner_id: string;
  project_id: string;
  project_brief_id: string;
  project_brief_version: number;
  input_fingerprint: string;
  version: number;
  status: InvestigationLifecycleStatus;
  current_stage: InvestigationStageId;
  stages: InvestigationStageStateDto[];
  readiness_status: InvestigationReadinessStatus;
  readiness_reasons: string[];
  started_at: string | null;
  completed_at: string | null;
  blocked_reason: string | null;
  supersedes_investigation_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type InvestigationCreateBody = {
  project_brief_id: string;
  project_brief_version: number;
  input_fingerprint: string;
};

export type InvestigationStageUpdateBody = {
  status: InvestigationStageStatus;
  blocked_reason?: string | null;
};
