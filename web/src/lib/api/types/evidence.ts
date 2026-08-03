/** Commercial MVP P0.4 — Evidence API types */

export type EvidenceLifecycleStatus =
  | "draft"
  | "under_review"
  | "accepted"
  | "rejected"
  | "superseded"
  | "archived";

export type EvidenceAssessmentState =
  | "confirmed"
  | "partial"
  | "conflicting"
  | "missing"
  | "outdated"
  | "unverified";

export type EvidenceConfidenceLevel = "high" | "medium" | "low" | "unknown";
export type EvidenceMateriality = "critical" | "high" | "medium" | "low";
export type EvidenceSourceStance = "supports" | "contradicts" | "context";

export type EvidenceType =
  | "observed_fact"
  | "metric"
  | "comparison"
  | "user_statement"
  | "customer_statement"
  | "market_signal"
  | "demand_signal"
  | "constraint"
  | "regulatory_fact"
  | "economic_input"
  | "calculation_result"
  | "absence_signal"
  | "historical_fact"
  | "other";

export type EvidenceInvestigationArea =
  | "project_context"
  | "market_research"
  | "competitor_analysis"
  | "audience_analysis"
  | "demand_signals"
  | "economics"
  | "risk_assessment"
  | "evidence_review"
  | "other";

export type EvidenceSourceLinkDto = {
  id: string;
  source_id: string;
  stance: EvidenceSourceStance;
  locator_type: string;
  locator_value: string | null;
  excerpt: string | null;
  note: string | null;
};

export type EvidenceDto = {
  id: string;
  owner_id: string;
  project_id: string;
  investigation_id: string;
  claim: string;
  evidence_type: EvidenceType;
  investigation_area: EvidenceInvestigationArea;
  lifecycle_status: EvidenceLifecycleStatus;
  assessment_state: EvidenceAssessmentState;
  confidence_level: EvidenceConfidenceLevel;
  materiality: EvidenceMateriality;
  review_note: string | null;
  why_it_matters: string | null;
  version: number;
  input_fingerprint: string;
  supersedes_evidence_id: string | null;
  source_links: EvidenceSourceLinkDto[];
  created_at: string;
  updated_at: string;
};

export type EvidenceCreateBody = {
  claim: string;
  evidence_type: EvidenceType;
  investigation_area?: EvidenceInvestigationArea;
  assessment_state?: EvidenceAssessmentState;
  confidence_level?: EvidenceConfidenceLevel;
  materiality?: EvidenceMateriality;
  review_note?: string | null;
  why_it_matters?: string | null;
  recommended_source_type?: string | null;
  source_links: Array<{
    source_id: string;
    stance: EvidenceSourceStance;
    locator_type?: string;
    locator_value?: string | null;
    excerpt?: string | null;
    note?: string | null;
  }>;
};

export type EvidenceSummaryDto = {
  total: number;
  by_assessment_state: Record<string, number>;
  by_area: Record<string, number>;
  by_confidence: Record<string, number>;
  by_materiality: Record<string, number>;
  accepted_count: number;
  unsupported_critical_claims: number;
  conflicting_critical_claims: number;
  outdated_critical_claims: number;
  missing_critical_claims: number;
  verdict_readiness_contribution: string;
  creates_business_verdict: false | boolean;
};
