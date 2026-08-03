/**
 * Product Alpha Phase A4 — Business Verdict types (frontend-only).
 */

import type {
  ConfidenceLevel,
  EvidenceState,
  MissingSeverity,
} from "@/lib/investigation/types";

export type BusinessVerdictType =
  | "GO"
  | "CONDITIONAL_GO"
  | "NO_GO"
  | "INSUFFICIENT_DATA";

export type VerdictStatus =
  | "draft"
  | "under_review"
  | "approved"
  | "superseded";

export type ScorecardRating =
  | "strong"
  | "acceptable"
  | "weak"
  | "critical"
  | "insufficient_data";

export type ScorecardDimensionId =
  | "market_attractiveness"
  | "demand_evidence"
  | "competitive_position"
  | "audience_clarity"
  | "economic_viability"
  | "execution_feasibility"
  | "risk_exposure"
  | "evidence_quality";

export type VerdictSensitivity =
  | "low"
  | "medium"
  | "high"
  | "verdict_changing";

export type AssumptionState =
  | "accepted_for_now"
  | "requires_validation"
  | "invalidated"
  | "confirmed";

export type ScorecardDimension = {
  id: ScorecardDimensionId;
  label: string;
  rating: ScorecardRating;
  explanation: string;
  evidenceIds: string[];
  criticalGap?: string;
};

export type VerdictEvidenceLink = {
  evidenceId: string;
  claim: string;
  state: EvidenceState;
  sourceTitles: string[];
  confidence: ConfidenceLevel;
  criterion: ScorecardDimensionId;
  whyItMatters: string;
};

export type CounterEvidenceItem = {
  id: string;
  conflictingClaim: string;
  sourceTitle: string;
  impact: string;
  resolutionStatus: "open" | "mitigated" | "accepted";
  couldChangeVerdict: boolean;
};

export type VerdictRiskItem = {
  id: string;
  title: string;
  severity: MissingSeverity;
  probability: ConfidenceLevel;
  businessConsequence: string;
  evidenceIds: string[];
  mitigation: string;
  sensitivity: VerdictSensitivity;
};

export type VerdictAssumption = {
  id: string;
  statement: string;
  reasonRequired: string;
  supportingEvidenceIds: string[];
  confidence: ConfidenceLevel;
  validationMethod: string;
  validationStage: string;
  effectIfFalse: string;
  state: AssumptionState;
};

export type VerdictCondition = {
  id: string;
  requiredAction: string;
  owner: string;
  successCriterion: string;
  evidenceRequired: string;
  deadlineOrMilestone: string;
  consequenceIfNotMet: string;
};

export type VerdictChangeTrigger = {
  id: string;
  description: string;
  currentState: string;
  threshold: string;
  possibleTransition: string;
};

export type VerdictNextStep = {
  primaryAction: string;
  handoffLabel: string;
  handoffHref: string;
  supportingActions: string[];
  note: string;
};

export type BusinessVerdict = {
  id: string;
  projectId: string;
  projectName: string;
  version: number;
  type: BusinessVerdictType;
  status: VerdictStatus;
  confidence: ConfidenceLevel;
  evidenceCoverageLabel: string;
  preparedAt: string;
  preparedAtLabel: string;
  supersedesVerdictId: string | null;
  evidenceSnapshotId: string;
  oneSentenceConclusion: string;
  executiveRationale: string;
  primaryBusinessImplication: string;
  recommendedImmediateAction: string;
  scorecard: ScorecardDimension[];
  supportingEvidence: VerdictEvidenceLink[];
  counterEvidence: CounterEvidenceItem[];
  risks: VerdictRiskItem[];
  assumptions: VerdictAssumption[];
  conditions: VerdictCondition[];
  changeTriggers: VerdictChangeTrigger[];
  nextStep: VerdictNextStep;
  /** Explicit separation from investigation readiness */
  basedOnReadinessStatus: string;
  localMockLabel: string;
};

export type VerdictStore = {
  projectId: string;
  currentVerdictId: string | null;
  versions: BusinessVerdict[];
  updatedAt: string;
};

export type VerdictScenarioId =
  | "go"
  | "conditional_go"
  | "no_go"
  | "insufficient_data";
