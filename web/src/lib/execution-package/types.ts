/**
 * Product Alpha Phase A7 — Execution Package types (frontend-only).
 */

import type { ConfidenceLevel, MissingSeverity } from "@/lib/investigation/types";
import type { AgencyRole } from "@/lib/implementation-plan/types";
import type { BusinessVerdictType } from "@/lib/verdict/types";

export type PackageStatus =
  | "draft"
  | "under_review"
  | "approval_pending"
  | "approved"
  | "blocked"
  | "superseded";

export type ActionClass =
  | "research"
  | "content_preparation"
  | "asset_preparation"
  | "campaign_planning"
  | "provider_configuration"
  | "publication"
  | "budget_change"
  | "data_export"
  | "reporting";

export type ScopeInclusion = "included" | "excluded";

export type ExecutionItemStatus =
  | "draft"
  | "ready"
  | "blocked"
  | "approval_pending"
  | "approved"
  | "dry_run_ready"
  | "excluded";

export type ProviderType =
  | "Yandex Direct"
  | "VK Ads"
  | "Telegram"
  | "Google Ads"
  | "Meta Ads"
  | "Email platform"
  | "CRM"
  | "Analytics"
  | "CMS"
  | "File storage";

export type ProviderState =
  | "not_required"
  | "missing"
  | "configuration_required"
  | "credentials_required"
  | "permission_required"
  | "mock_ready"
  | "ready";

export type ApprovalType =
  | "verdict_approval"
  | "strategy_approval"
  | "implementation_plan_approval"
  | "budget_approval"
  | "asset_approval"
  | "provider_configuration_approval"
  | "publication_approval"
  | "execution_approval";

export type LocalGateStatus =
  | "not_required"
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "blocked";

export type PreflightResult = "passed" | "warning" | "failed" | "not_applicable";

export type VerificationMethod =
  | "read_back"
  | "response_body_validation"
  | "provider_status_check"
  | "artifact_checksum"
  | "manual_review"
  | "analytics_confirmation"
  | "unavailable";

export type RollbackState = "defined" | "partial" | "unavailable" | "not_required";

export type DryRunResult = "passed" | "passed_with_warnings" | "blocked";

export type PackageReadinessStatus =
  | "not_ready"
  | "conditionally_ready"
  | "ready_for_approval"
  | "approved_for_dry_run"
  | "blocked";

export type ExecutionScopeItem = {
  id: string;
  title: string;
  type: string;
  linkedTaskId: string;
  linkedDeliverableId: string;
  ownerRole: AgencyRole;
  targetSystem: string;
  actionClass: ActionClass;
  riskClass: MissingSeverity;
  approvalRequired: boolean;
  verificationRequired: boolean;
  inclusion: ScopeInclusion;
};

export type ExecutionItem = {
  id: string;
  title: string;
  sourceTaskId: string;
  actionClass: ActionClass;
  ownerRole: AgencyRole;
  reviewerRole: AgencyRole;
  targetProvider: ProviderType | "none";
  targetObject: string;
  requiredInput: string;
  expectedOutput: string;
  preconditions: string;
  approvalGateId: string;
  budgetGateId: string;
  riskLevel: MissingSeverity;
  verificationMethod: VerificationMethod;
  rollbackMethod: string;
  status: ExecutionItemStatus;
};

export type ProviderRequirement = {
  id: string;
  providerType: ProviderType;
  purpose: string;
  requiredCapability: string;
  authenticationState: ProviderState;
  configurationState: ProviderState;
  permissionsRequired: string;
  dryRunAvailability: "available" | "mock_only" | "unavailable";
  verificationSupport: boolean;
  rollbackSupport: boolean;
  blocker: string;
};

export type ApprovalMatrixRow = {
  id: string;
  gate: ApprovalType;
  decisionOwner: AgencyRole;
  approvalScope: string;
  requiredArtifacts: string[];
  requiredEvidence: string;
  budgetImpact: string;
  riskClass: MissingSeverity;
  status: LocalGateStatus;
  expiry: string;
  consequenceIfRejected: string;
  affectedExecutionItemIds: string[];
};

export type BudgetAuthorization = {
  requestedAmountOrRange: string;
  approvedAmount: string;
  reservedAmount: string;
  providerAllocation: string;
  contingency: string;
  releaseGates: string[];
  stopLossThreshold: string;
  approvalState: LocalGateStatus;
  unresolvedGaps: string[];
  mode: "exact" | "range" | "unknown" | "requires_approval";
};

export type PreflightCheck = {
  id: string;
  category: string;
  title: string;
  result: PreflightResult;
  severity: MissingSeverity;
  evidence: string;
  blocking: boolean;
  resolutionAction: string;
};

export type VerificationPlanEntry = {
  id: string;
  executionItemId: string;
  expectedState: string;
  verificationMethod: VerificationMethod;
  verificationTiming: string;
  evidenceToCapture: string;
  failureCondition: string;
  retryPolicy: string;
  escalationPath: string;
  finalStatusMapping: string;
  acknowledgmentRequired: boolean;
};

export type RollbackPlanEntry = {
  id: string;
  executionItemId: string;
  rollbackTrigger: string;
  rollbackAction: string;
  rollbackOwner: AgencyRole;
  rollbackPrerequisites: string;
  expectedRestoredState: string;
  verificationAfterRollback: string;
  timeSensitivity: string;
  limitations: string;
  state: RollbackState;
};

export type RiskControl = {
  id: string;
  linkedRiskId: string;
  title: string;
  preventiveControl: string;
  detectiveControl: string;
  correctiveAction: string;
  ownerRole: AgencyRole;
  evidence: string;
  status: "open" | "in_place" | "accepted";
  residualRisk: MissingSeverity;
};

export type PackageBlocker = {
  id: string;
  origin: string;
  description: string;
  affectedItemIds: string[];
  owner: AgencyRole;
  requiredAction: string;
  evidenceRequired: string;
  unblockCriterion: string;
};

export type DryRunReport = {
  packageVersion: number;
  checkedItems: number;
  passedChecks: string[];
  warnings: string[];
  blockers: string[];
  simulatedSequence: string[];
  approvalGaps: string[];
  providerGaps: string[];
  verificationGaps: string[];
  rollbackGaps: string[];
  result: DryRunResult;
  externalActionsPerformed: false;
  generatedAt: string;
};

export type PackageReadinessResult = {
  status: PackageReadinessStatus;
  blockingReasons: string[];
  warnings: string[];
  missingApprovals: string[];
  missingProviderSetup: string[];
  verificationGaps: string[];
  rollbackGaps: string[];
  nextRequiredAction: string;
  notRealExecution: true;
};

export type PackageSummary = {
  executionObjective: string;
  selectedWorkstreams: string[];
  selectedMilestones: string[];
  taskCount: number;
  deliverableCount: number;
  requiredProviders: string[];
  estimatedBudgetRange: string;
  mandatoryConditions: string[];
  criticalRisks: string[];
  approvalGates: string[];
  verificationCoverage: string;
  rollbackCoverage: string;
  currentBlockers: string[];
};

export type ExecutionPackage = {
  id: string;
  projectId: string;
  projectName: string;
  verdictId: string;
  verdictVersion: number;
  verdictType: BusinessVerdictType;
  strategyId: string;
  strategyVersion: number;
  implementationPlanId: string;
  implementationPlanVersion: number;
  version: number;
  status: PackageStatus;
  createdAt: string;
  updatedAt: string;
  updatedAtLabel: string;
  supersedesPackageId: string | null;
  evidenceSnapshotId: string;
  localMockLabel: string;
  summary: PackageSummary;
  executionScope: ExecutionScopeItem[];
  executionItems: ExecutionItem[];
  providerRequirements: ProviderRequirement[];
  approvalMatrix: ApprovalMatrixRow[];
  budgetAuthorization: BudgetAuthorization;
  preflightChecks: PreflightCheck[];
  verificationPlan: VerificationPlanEntry[];
  rollbackPlan: RollbackPlanEntry[];
  riskControls: RiskControl[];
  blockers: PackageBlocker[];
  dryRunReport: DryRunReport | null;
  readiness: PackageReadinessResult;
  approvalReadinessLabel: string;
};

export type ExecutionPackageStore = {
  projectId: string;
  currentPackageId: string | null;
  versions: ExecutionPackage[];
  updatedAt: string;
};

export type PackageAccessDecision =
  | { allow: true; mode: "go" | "conditional_go" }
  | {
      allow: false;
      redirect: "pivot" | "investigation" | "strategy" | "implementation";
      reason: string;
    };

export type { AgencyRole, ConfidenceLevel };
