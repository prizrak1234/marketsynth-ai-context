/**
 * Product Alpha Phase A6 — Implementation Plan types (frontend-only).
 */

import type { ConfidenceLevel, MissingSeverity } from "@/lib/investigation/types";
import type { BusinessVerdictType } from "@/lib/verdict/types";

export type PlanStatus =
  | "draft"
  | "under_review"
  | "approved"
  | "blocked"
  | "superseded";

export type WorkstreamType =
  | "validation"
  | "research"
  | "positioning"
  | "offer_development"
  | "acquisition"
  | "content_and_assets"
  | "sales_enablement"
  | "analytics"
  | "operations"
  | "compliance"
  | "customer_success"
  | "retention";

export type WorkstreamStatus =
  | "not_started"
  | "ready"
  | "blocked"
  | "in_progress"
  | "under_review"
  | "completed";

export type PlanPriority = "critical" | "high" | "medium" | "low";

export type TaskStatus =
  | "backlog"
  | "ready"
  | "blocked"
  | "in_progress"
  | "review"
  | "approved"
  | "completed"
  | "cancelled";

export type AgencyRole =
  | "CEO"
  | "Research Director"
  | "Market Analyst"
  | "Competitor Analyst"
  | "Audience Analyst"
  | "Risk Officer"
  | "Chief Marketing Strategist"
  | "Performance Marketer"
  | "Content Strategist"
  | "Copywriter"
  | "Designer"
  | "Analyst"
  | "Project Manager"
  | "Client Owner";

export type DependencyType =
  | "finish_to_start"
  | "approval_gate"
  | "evidence_gate"
  | "budget_gate"
  | "compliance_gate"
  | "resource_gate";

export type BudgetAmountMode = "exact" | "range" | "unknown" | "requires_approval";

export type GateStatus =
  | "not_required"
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "blocked";

export type PlanningReadinessStatus =
  | "not_ready"
  | "conditionally_ready"
  | "ready_for_approval"
  | "blocked";

export type HorizonLabel =
  | "Week 1–2"
  | "Month 1"
  | "Month 2"
  | "Quarter 1"
  | "TBD";

export type PlanAssumptionStatus =
  | "accepted_for_planning"
  | "requires_validation"
  | "confirmed"
  | "invalidated";

export type PlanWorkstream = {
  id: string;
  type: WorkstreamType;
  title: string;
  purpose: string;
  linkedObjectiveId: string;
  ownerRole: AgencyRole;
  status: WorkstreamStatus;
  priority: PlanPriority;
  plannedStart: HorizonLabel;
  plannedFinish: HorizonLabel;
  dependencyIds: string[];
  deliverableIds: string[];
  budgetRange: string;
  successCriteria: string;
  risks: string;
  blockers: string;
};

export type PlanMilestone = {
  id: string;
  title: string;
  description: string;
  targetPeriod: HorizonLabel;
  workstreamIds: string[];
  requiredDeliverableIds: string[];
  entryCriteria: string;
  exitCriteria: string;
  approvalRequired: boolean;
  blockingDependencyIds: string[];
  status: WorkstreamStatus;
};

export type PlanTask = {
  id: string;
  title: string;
  description: string;
  workstreamId: string;
  milestoneId: string;
  responsibleRole: AgencyRole;
  reviewerRole: AgencyRole;
  priority: PlanPriority;
  status: TaskStatus;
  dependencyIds: string[];
  requiredInput: string;
  expectedOutput: string;
  acceptanceCriteria: string;
  budgetImpact: string;
  riskLevel: MissingSeverity;
  approvalRequired: boolean;
};

export type RoleAssignment = {
  role: AgencyRole;
  responsibility: string;
  decisionAuthority: string;
  requiredInput: string;
  expectedOutput: string;
  reviewRelationship: string;
};

export type PlanDependency = {
  id: string;
  predecessor: string;
  successor: string;
  type: DependencyType;
  blocking: boolean;
  resolutionAction: string;
};

export type PlanDeliverable = {
  id: string;
  name: string;
  type: string;
  workstreamId: string;
  ownerRole: AgencyRole;
  format: string;
  status: TaskStatus;
  acceptanceCriteria: string;
  approvalRequired: boolean;
  linkedStrategyElement: string;
  duePeriod: HorizonLabel;
  dependencyIds: string[];
};

export type BudgetCategoryLine = {
  id: string;
  category: string;
  mode: BudgetAmountMode;
  minimum: string;
  recommendedRange: string;
  upperBoundary: string;
  rationale: string;
  releaseCondition: string;
  linkedWorkstreamId: string;
  risk: string;
  learningObjective: string;
};

export type BudgetGate = {
  id: string;
  name: string;
  amountOrRange: string;
  prerequisite: string;
  approvalOwner: AgencyRole;
  releaseCondition: string;
  blockedWorkstreamIds: string[];
  evidenceRequired: string;
  status: GateStatus;
};

export type ApprovalGate = {
  id: string;
  title: string;
  decisionOwner: AgencyRole;
  requiredArtifacts: string[];
  requiredEvidence: string;
  deadlineOrMilestone: string;
  status: GateStatus;
  consequenceIfRejected: string;
  affectedTaskIds: string[];
};

export type PlanCondition = {
  id: string;
  requiredAction: string;
  ownerRole: AgencyRole;
  validationMethod: string;
  successCriterion: string;
  deadlineOrMilestone: string;
  evidenceRequired: string;
  blockingTaskIds: string[];
  executionImpact: string;
  status: "open" | "in_progress" | "met" | "waived";
  blocksPlanning: boolean;
};

export type PlanRisk = {
  id: string;
  title: string;
  source: string;
  probability: ConfidenceLevel;
  severity: MissingSeverity;
  affectedWorkstreamId: string;
  earlyWarning: string;
  mitigation: string;
  contingencyAction: string;
  ownerRole: AgencyRole;
  stopCondition: string;
  status: "open" | "mitigating" | "accepted" | "closed";
  linkedStrategyRiskId: string;
};

export type PlanAssumption = {
  id: string;
  statement: string;
  source: string;
  confidence: ConfidenceLevel;
  validationAction: string;
  validationMilestone: string;
  owner: AgencyRole;
  impactIfFalse: string;
  linkedTaskId: string;
  status: PlanAssumptionStatus;
};

export type RoadmapPhase = {
  id: string;
  horizon: HorizonLabel;
  milestoneIds: string[];
  workstreamIds: string[];
  note: string;
};

export type PlanningReadinessResult = {
  status: PlanningReadinessStatus;
  blockers: string[];
  unresolvedGates: string[];
  incompleteWorkstreams: string[];
  criticalMissingInputs: string[];
  recommendedNextAction: string;
  notRealExecution: true;
};

export type PlanOverview = {
  strategicObjective: string;
  implementationHorizon: string;
  primaryWorkstreams: string[];
  criticalMilestones: string[];
  estimatedBudgetRange: string;
  mandatoryConditions: string[];
  currentBlockers: string[];
  readinessLabel: string;
  nextManagementDecision: string;
};

export type ImplementationPlan = {
  id: string;
  projectId: string;
  projectName: string;
  strategyId: string;
  strategyVersion: number;
  verdictId: string;
  verdictVersion: number;
  verdictType: BusinessVerdictType;
  version: number;
  status: PlanStatus;
  createdAt: string;
  updatedAt: string;
  updatedAtLabel: string;
  supersedesPlanId: string | null;
  evidenceSnapshotId: string;
  localMockLabel: string;
  overview: PlanOverview;
  workstreams: PlanWorkstream[];
  milestones: PlanMilestone[];
  tasks: PlanTask[];
  roles: RoleAssignment[];
  dependencies: PlanDependency[];
  deliverables: PlanDeliverable[];
  budgetPlan: BudgetCategoryLine[];
  budgetGates: BudgetGate[];
  approvalGates: ApprovalGate[];
  conditions: PlanCondition[];
  risks: PlanRisk[];
  assumptions: PlanAssumption[];
  roadmap: RoadmapPhase[];
  readiness: PlanningReadinessResult;
};

export type ImplementationPlanStore = {
  projectId: string;
  currentPlanId: string | null;
  versions: ImplementationPlan[];
  updatedAt: string;
};

export type ImplementationAccessDecision =
  | { allow: true; mode: "go" | "conditional_go" }
  | {
      allow: false;
      redirect: "pivot" | "investigation" | "strategy";
      reason: string;
    };
