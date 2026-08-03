/**
 * Product Alpha Phase A3 — Investigation workspace types (frontend-only).
 */

export type InvestigationStatus =
  | "queued"
  | "collecting_context"
  | "researching"
  | "reviewing_evidence"
  | "blocked_by_missing_data"
  | "ready_for_verdict"
  | "completed";

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

export type StageRunState =
  | "not_started"
  | "queued"
  | "in_progress"
  | "blocked"
  | "completed"
  | "needs_review";

export type SourceType =
  | "website"
  | "competitor_website"
  | "market_report"
  | "public_dataset"
  | "analytics_export"
  | "uploaded_document"
  | "interview"
  | "user_statement"
  | "internal_calculation";

export type FreshnessState = "current" | "acceptable" | "outdated" | "unknown";
export type ReliabilityLevel = "high" | "medium" | "low" | "unverified";
export type SourceStatus =
  | "available"
  | "processing"
  | "reviewed"
  | "rejected"
  | "unavailable";

export type EvidenceState =
  | "confirmed"
  | "partial"
  | "conflicting"
  | "missing"
  | "outdated";

export type ConfidenceLevel = "high" | "medium" | "low";

export type InvestigationArea =
  | "market"
  | "competitors"
  | "audience"
  | "demand"
  | "economics"
  | "risks"
  | "product"
  | "geography";

export type FindingType =
  | "fact"
  | "hypothesis"
  | "opportunity"
  | "weakness"
  | "constraint"
  | "anomaly"
  | "contradiction";

export type FindingStatus =
  | "draft"
  | "supported"
  | "disputed"
  | "rejected"
  | "needs_more_data";

export type MissingSeverity = "low" | "medium" | "high" | "critical";

export type MissingDataResolution =
  | "open"
  | "marked_unknown"
  | "assumed"
  | "data_added";

export type RiskStatus = "open" | "mitigating" | "accepted" | "closed";

export type VerdictReadinessStatus =
  | "not_ready"
  | "conditionally_ready"
  | "ready_for_review";

export type InvestigationScenarioId =
  | "conditionally_ready"
  | "not_ready"
  | "ready_for_review"
  | "no_go";

export type InvestigationStage = {
  id: InvestigationStageId;
  label: string;
  order: number;
  state: StageRunState;
  note?: string;
};

export type InvestigationSource = {
  id: string;
  title: string;
  sourceType: SourceType;
  origin: string;
  /** Mock-only marker URL — never implies live browsing */
  mockUrl?: string;
  accessedAtLabel: string;
  freshness: FreshnessState;
  reliability: ReliabilityLevel;
  relevance: ConfidenceLevel;
  status: SourceStatus;
  notes: string;
};

export type EvidenceItem = {
  id: string;
  claim: string;
  state: EvidenceState;
  supportingSourceIds: string[];
  contradictingSourceIds: string[];
  confidence: ConfidenceLevel;
  area: InvestigationArea;
  reviewerNote: string;
  updatedAtLabel: string;
};

export type InvestigationFinding = {
  id: string;
  title: string;
  statement: string;
  type: FindingType;
  relatedEvidenceIds: string[];
  status: FindingStatus;
  businessImpact: string;
  domain: InvestigationArea;
  sourceIds: string[];
};

export type MissingDataItem = {
  id: string;
  missingInformation: string;
  whyItMatters: string;
  severity: MissingSeverity;
  blockedDecision: string;
  recommendedAction: string;
  canContinue: boolean;
  resolution: MissingDataResolution;
  assumptionNote?: string;
};

export type RiskItem = {
  id: string;
  title: string;
  description: string;
  severity: MissingSeverity;
  probability: ConfidenceLevel;
  evidenceIds: string[];
  businessConsequence: string;
  mitigation: string;
  status: RiskStatus;
};

export type OpportunityItem = {
  id: string;
  title: string;
  description: string;
  potentialImpact: string;
  evidenceIds: string[];
  dependency: string;
  confidence: ConfidenceLevel;
  recommendedValidation: string;
};

export type ContradictionItem = {
  id: string;
  statementA: string;
  statementB: string;
  fieldA: string;
  fieldB: string;
  importance: MissingSeverity;
  requiredResolution: string;
  blocksVerdict: boolean;
  resolved: boolean;
};

export type VerdictReadinessResult = {
  status: VerdictReadinessStatus;
  completedAreas: InvestigationArea[];
  blockingGaps: string[];
  unresolvedAssumptions: string[];
  recommendedNextActions: string[];
  /** Explicit: this is NOT GO / NO_GO */
  notABusinessVerdict: true;
};

export type InvestigationSpecialistRow = {
  id: string;
  role: string;
  area: InvestigationArea | "coordination";
  state: "completed" | "running" | "waiting" | "blocked";
  progress: number;
  detail: string;
  artifactCount: number;
  blocker?: string;
  lastActivityLabel: string;
};

export type InvestigationBriefSummary = {
  idea: string;
  product: string;
  geography: string;
  audienceHypotheses: string[];
  budgetState: string;
  keyConstraints: string;
  assumptions: string[];
};

export type InvestigationWorkspace = {
  projectId: string;
  scenarioId: InvestigationScenarioId;
  projectName: string;
  projectStageLabel: string;
  intakeReadinessLabel: string;
  status: InvestigationStatus;
  lastUpdateLabel: string;
  brief: InvestigationBriefSummary;
  stages: InvestigationStage[];
  sources: InvestigationSource[];
  evidence: EvidenceItem[];
  findings: InvestigationFinding[];
  missingData: MissingDataItem[];
  risks: RiskItem[];
  opportunities: OpportunityItem[];
  contradictions: ContradictionItem[];
  specialists: InvestigationSpecialistRow[];
  /** User acknowledged remaining assumptions for conditionally_ready CTA */
  assumptionsAcknowledged: boolean;
  verdictReadiness: VerdictReadinessResult | null;
  updatedAt: string;
};
