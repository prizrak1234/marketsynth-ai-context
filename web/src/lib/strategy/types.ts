/**
 * Product Alpha Phase A5 — Marketing Strategy types (frontend-only).
 */

import type { ConfidenceLevel, MissingSeverity } from "@/lib/investigation/types";
import type { BusinessVerdictType } from "@/lib/verdict/types";

export type StrategyStatus =
  | "draft"
  | "under_review"
  | "approved"
  | "blocked"
  | "superseded";

export type StrategyPriority = "critical" | "high" | "medium" | "low";

export type SegmentPriority =
  | "primary"
  | "secondary"
  | "experimental"
  | "excluded";

export type SegmentValidationStatus =
  | "confirmed"
  | "evidence_supported_hypothesis"
  | "unvalidated_hypothesis";

export type PriceMode = "exact" | "range" | "hypothesis" | "unknown";

export type OfferKind =
  | "core"
  | "entry"
  | "validation"
  | "premium"
  | "retention";

export type ChannelId =
  | "seo"
  | "content"
  | "paid_search"
  | "paid_social"
  | "telegram"
  | "email"
  | "partnerships"
  | "direct_sales"
  | "events"
  | "marketplaces"
  | "referral"
  | "influencer"
  | "product_led"
  | "offline_local";

export type ChannelStatus =
  | "recommended"
  | "test"
  | "conditional"
  | "excluded"
  | "insufficient_data";

export type FunnelStageId =
  | "awareness"
  | "interest"
  | "qualification"
  | "validation"
  | "conversion"
  | "onboarding"
  | "retention"
  | "referral";

export type AssetKind =
  | "landing_page"
  | "offer_page"
  | "lead_magnet"
  | "comparison_page"
  | "case_study"
  | "sales_deck"
  | "email_sequence"
  | "onboarding_material"
  | "ad_creative"
  | "webinar"
  | "research_report";

export type StrategyAssumptionStatus =
  | "accepted_for_planning"
  | "requires_validation"
  | "confirmed"
  | "invalidated";

export type ExecutionReadinessStatus =
  | "not_ready"
  | "conditionally_ready"
  | "ready_for_planning"
  | "blocked";

export type StrategyObjective = {
  id: string;
  title: string;
  businessOutcome: string;
  marketingOutcome: string;
  priority: StrategyPriority;
  timeframe: string;
  successMetric: string;
  baseline: string;
  target: string;
  dependency: string;
  linkedVerdictCriterion: string;
};

export type AudienceSegment = {
  id: string;
  name: string;
  model: "b2b" | "b2c" | "b2g" | "mixed";
  problem: string;
  desiredOutcome: string;
  buyingTrigger: string;
  objections: string;
  decisionMaker: string;
  userVsBuyer: string;
  evidenceStrength: ConfidenceLevel;
  priority: SegmentPriority;
  validationStatus: SegmentValidationStatus;
};

export type PositioningBlock = {
  targetCustomer: string;
  category: string;
  coreProblem: string;
  alternativeUsed: string;
  primaryDifferentiation: string;
  proof: string;
  reasonToBelieve: string;
  keyMessage: string;
  positioningRisks: string;
};

export type StrategyOffer = {
  id: string;
  name: string;
  kind: OfferKind;
  targetSegmentId: string;
  customerProblem: string;
  promisedOutcome: string;
  scope: string;
  priceMode: PriceMode;
  priceValue: string;
  proof: string;
  riskReversal: string;
  callToAction: string;
  validationStatus: SegmentValidationStatus;
};

export type ChannelPlanItem = {
  id: string;
  channel: ChannelId;
  label: string;
  role: string;
  funnelStage: FunnelStageId;
  targetSegmentId: string;
  expectedSignal: string;
  costClass: "low" | "medium" | "high" | "unknown";
  evidenceNote: string;
  dependency: string;
  risk: string;
  status: ChannelStatus;
};

export type FunnelStage = {
  id: FunnelStageId;
  label: string;
  userAction: string;
  businessAction: string;
  channel: string;
  asset: string;
  metric: string;
  exitCriterion: string;
  risk: string;
};

export type AssetPlanItem = {
  id: string;
  kind: AssetKind;
  label: string;
  purpose: string;
  targetSegmentId: string;
  funnelStage: FunnelStageId;
  linkedMessage: string;
  dependency: string;
  priority: StrategyPriority;
  status: "planned" | "blocked" | "deferred";
};

export type BudgetLine = {
  id: string;
  section: string;
  amountOrRange: string;
  percentageLabel: string;
  rationale: string;
  condition: string;
  risk: string;
  expectedLearning: string;
};

export type StrategyMetric = {
  id: string;
  category:
    | "business"
    | "marketing"
    | "validation"
    | "risk_indicator"
    | "stop_loss";
  name: string;
  purpose: string;
  baseline: string;
  target: string;
  measurementPeriod: string;
  dataSource: string;
  decisionThreshold: string;
  actionIfMissed: string;
};

export type StrategyCondition = {
  id: string;
  unresolvedCondition: string;
  requiredAction: string;
  successCriterion: string;
  owner: string;
  deadline: string;
  evidenceRequired: string;
  effectOnStrategy: string;
  blocksExecution: boolean;
};

export type StrategyRisk = {
  id: string;
  title: string;
  source: string;
  probability: ConfidenceLevel;
  severity: MissingSeverity;
  impact: string;
  mitigation: string;
  earlyWarning: string;
  stopCondition: string;
  linkedVerdictRiskId: string;
};

export type StrategyAssumption = {
  id: string;
  statement: string;
  source: string;
  confidence: ConfidenceLevel;
  validationMethod: string;
  validationStage: string;
  owner: string;
  impactIfFalse: string;
  status: StrategyAssumptionStatus;
};

export type ExecutionReadinessResult = {
  status: ExecutionReadinessStatus;
  blockers: string[];
  unresolvedConditions: string[];
  missingElements: string[];
  nextRequiredAction: string;
  notRealExecutionApproval: true;
};

export type StrategySummary = {
  businessObjective: string;
  targetMarket: string;
  primaryAudience: string;
  positioning: string;
  coreOffer: string;
  channelMix: string;
  budgetRange: string;
  keyConstraints: string;
  criticalConditions: string;
};

export type MarketingStrategy = {
  id: string;
  projectId: string;
  projectName: string;
  verdictId: string;
  verdictVersion: number;
  verdictType: BusinessVerdictType;
  version: number;
  status: StrategyStatus;
  createdAt: string;
  updatedAt: string;
  updatedAtLabel: string;
  supersedesStrategyId: string | null;
  evidenceSnapshotId: string;
  localMockLabel: string;
  summary: StrategySummary;
  objectives: StrategyObjective[];
  segments: AudienceSegment[];
  positioning: PositioningBlock;
  offers: StrategyOffer[];
  channels: ChannelPlanItem[];
  funnel: FunnelStage[];
  assets: AssetPlanItem[];
  budget: BudgetLine[];
  metrics: StrategyMetric[];
  conditions: StrategyCondition[];
  risks: StrategyRisk[];
  assumptions: StrategyAssumption[];
  executionReadiness: ExecutionReadinessResult;
};

export type StrategyStore = {
  projectId: string;
  currentStrategyId: string | null;
  versions: MarketingStrategy[];
  updatedAt: string;
};

export type StrategyAccessDecision =
  | { allow: true; mode: "go" | "conditional_go" }
  | { allow: false; redirect: "pivot" | "investigation"; reason: string };
