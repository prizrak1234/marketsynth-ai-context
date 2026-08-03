/**
 * P0.6 — backend MarketingStrategy → Product Alpha Strategy view model.
 * Does not collapse with MarketingPlan.
 */

import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";
import type {
  AudienceSegment,
  ChannelId,
  FunnelStageId,
  MarketingStrategy,
  StrategyStatus,
} from "@/lib/strategy/types";
import type { BusinessVerdictType } from "@/lib/verdict/types";

const TYPE_MAP: Record<string, BusinessVerdictType> = {
  go: "GO",
  conditional_go: "CONDITIONAL_GO",
  no_go: "NO_GO",
  insufficient_data: "INSUFFICIENT_DATA",
};

const CHANNELS: ChannelId[] = [
  "seo",
  "content",
  "paid_search",
  "paid_social",
  "telegram",
  "email",
  "partnerships",
  "direct_sales",
  "events",
  "marketplaces",
  "referral",
  "influencer",
  "product_led",
  "offline_local",
];

const FUNNELS: FunnelStageId[] = [
  "awareness",
  "interest",
  "qualification",
  "validation",
  "conversion",
  "onboarding",
  "retention",
  "referral",
];

function mapStatus(lifecycle: string): StrategyStatus {
  if (lifecycle === "approved") return "approved";
  if (lifecycle === "under_review") return "under_review";
  if (lifecycle === "superseded") return "superseded";
  if (lifecycle === "rejected" || lifecycle === "archived") return "blocked";
  return "draft";
}

function asChannel(raw: string): ChannelId {
  return (CHANNELS.includes(raw as ChannelId) ? raw : "content") as ChannelId;
}

function asFunnel(raw: string): FunnelStageId {
  return (FUNNELS.includes(raw as FunnelStageId) ? raw : "awareness") as FunnelStageId;
}

export function mapBackendStrategyToProductAlpha(
  dto: BackendMarketingStrategyDto,
  projectName: string,
): MarketingStrategy {
  const segments: AudienceSegment[] = (dto.audience_segments || []).map((s, i) => ({
    id: String(s.id ?? `seg_${i}`),
    name: String(s.name ?? "Segment"),
    model: (["b2b", "b2c", "b2g", "mixed"].includes(String(s.market_type))
      ? String(s.market_type)
      : "mixed") as AudienceSegment["model"],
    problem: String(s.problem ?? ""),
    desiredOutcome: String(s.desired_outcome ?? ""),
    buyingTrigger: String(s.buying_trigger ?? ""),
    objections: String(s.objections ?? ""),
    decisionMaker: String(s.decision_maker ?? ""),
    userVsBuyer: String(s.buyer_user_distinction ?? ""),
    evidenceStrength: (["high", "medium", "low"].includes(String(s.evidence_strength))
      ? String(s.evidence_strength)
      : "low") as AudienceSegment["evidenceStrength"],
    priority: (["primary", "secondary", "experimental", "excluded"].includes(
      String(s.priority),
    )
      ? String(s.priority)
      : "secondary") as AudienceSegment["priority"],
    validationStatus: (String(s.validation_status) === "confirmed"
      ? "confirmed"
      : String(s.validation_status) === "evidence_supported_hypothesis"
        ? "evidence_supported_hypothesis"
        : "unvalidated_hypothesis") as AudienceSegment["validationStatus"],
  }));

  const pos = dto.positioning || {};
  const readiness =
    dto.readiness_status === "ready_for_planning" ||
    dto.readiness_status === "conditionally_ready" ||
    dto.readiness_status === "blocked" ||
    dto.readiness_status === "not_ready"
      ? dto.readiness_status
      : "not_ready";

  return {
    id: dto.id,
    projectId: dto.project_id,
    projectName,
    verdictId: dto.business_verdict_id,
    verdictVersion: dto.business_verdict_version,
    verdictType: TYPE_MAP[dto.business_verdict_type] ?? "CONDITIONAL_GO",
    version: dto.version,
    status: mapStatus(dto.lifecycle_status),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    updatedAtLabel: new Date(dto.updated_at).toLocaleString("ru-RU"),
    supersedesStrategyId: null,
    evidenceSnapshotId: dto.evidence_snapshot_id,
    localMockLabel: "",
    summary: {
      businessObjective: dto.primary_business_objective,
      targetMarket: String(pos.category ?? dto.strategic_horizon),
      primaryAudience: segments[0]?.name ?? "Audience",
      positioning: String(pos.key_message ?? dto.title),
      coreOffer: String((dto.offers || [])[0]?.name ?? "Offer"),
      channelMix: (dto.channel_strategy || [])
        .map((c) => String(c.channel ?? ""))
        .filter(Boolean)
        .join(", "),
      budgetRange: "Policy only — not budget approval",
      keyConstraints: (dto.execution_constraints || []).join("; "),
      criticalConditions: (dto.verdict_conditions || [])
        .map((c) => String(c.verdict_condition_id ?? ""))
        .join("; "),
    },
    objectives: (dto.objectives || []).map((o, i) => ({
      id: String(o.id ?? `obj_${i}`),
      title: String(o.title ?? ""),
      businessOutcome: String(o.business_outcome ?? ""),
      marketingOutcome: String(o.marketing_outcome ?? ""),
      priority: (["critical", "high", "medium", "low"].includes(String(o.priority))
        ? String(o.priority)
        : "medium") as "critical" | "high" | "medium" | "low",
      timeframe: String(o.timeframe ?? ""),
      successMetric: String(o.success_metric ?? ""),
      baseline: String(o.baseline ?? ""),
      target: String(o.target ?? ""),
      dependency: String(o.dependency ?? ""),
      linkedVerdictCriterion: String(o.linked_verdict_criterion ?? ""),
    })),
    segments,
    positioning: {
      targetCustomer: String(pos.target_customer ?? ""),
      category: String(pos.category ?? ""),
      coreProblem: String(pos.core_problem ?? ""),
      alternativeUsed: String(pos.alternative_used_today ?? ""),
      primaryDifferentiation: String(pos.primary_differentiation ?? ""),
      proof: String(pos.proof ?? ""),
      reasonToBelieve: String(pos.reason_to_believe ?? ""),
      keyMessage: String(pos.key_message ?? ""),
      positioningRisks: Array.isArray(pos.positioning_risks)
        ? (pos.positioning_risks as string[]).join("; ")
        : String(pos.positioning_risks ?? ""),
    },
    offers: (dto.offers || []).map((o, i) => ({
      id: String(o.id ?? `offer_${i}`),
      name: String(o.name ?? ""),
      kind: (["core", "entry", "validation", "premium", "retention"].includes(
        String(o.offer_type),
      )
        ? String(o.offer_type)
        : "core") as "core" | "entry" | "validation" | "premium" | "retention",
      targetSegmentId: String(o.target_segment_id ?? segments[0]?.id ?? ""),
      customerProblem: String(o.customer_problem ?? ""),
      promisedOutcome: String(o.promised_outcome ?? ""),
      scope: String(o.scope ?? ""),
      priceMode: (["exact", "range", "hypothesis", "unknown"].includes(String(o.price_model))
        ? String(o.price_model)
        : "unknown") as "exact" | "range" | "hypothesis" | "unknown",
      priceValue: String(o.price_value_or_range ?? "unknown"),
      proof: String(o.proof ?? ""),
      riskReversal: String(o.risk_reversal ?? ""),
      callToAction: String(o.call_to_action ?? ""),
      validationStatus: "unvalidated_hypothesis",
    })),
    channels: (dto.channel_strategy || []).map((c, i) => ({
      id: `ch_${i}`,
      channel: asChannel(String(c.channel ?? "content")),
      label: String(c.channel ?? "content"),
      role: String(c.role ?? ""),
      funnelStage: asFunnel(String(c.funnel_stage ?? "interest")),
      targetSegmentId: String(
        (Array.isArray(c.target_segment_ids) && c.target_segment_ids[0]) ||
          segments[0]?.id ||
          "",
      ),
      expectedSignal: String(c.expected_signal ?? ""),
      costClass: (["low", "medium", "high", "unknown"].includes(String(c.cost_class))
        ? String(c.cost_class)
        : "unknown") as "low" | "medium" | "high" | "unknown",
      evidenceNote: String(c.evidence_basis ?? ""),
      dependency: String(c.dependency ?? ""),
      risk: String(c.risk ?? ""),
      status: (["recommended", "test", "conditional", "excluded", "insufficient_data"].includes(
        String(c.status),
      )
        ? String(c.status)
        : "test") as
        | "recommended"
        | "test"
        | "conditional"
        | "excluded"
        | "insufficient_data",
    })),
    funnel: (dto.funnel || []).map((f) => ({
      id: asFunnel(String(f.stage ?? "awareness")),
      label: String(f.stage ?? "awareness"),
      userAction: String(f.customer_action ?? ""),
      businessAction: String(f.business_action ?? ""),
      channel: String(f.channel ?? ""),
      asset: String(f.asset ?? ""),
      metric: String(f.metric ?? ""),
      exitCriterion: String(f.exit_criterion ?? ""),
      risk: String(f.risk ?? ""),
    })),
    assets: (dto.asset_plan || []).map((a, i) => ({
      id: String(a.id ?? `asset_${i}`),
      kind: "landing_page" as const,
      label: String(a.asset_type ?? "landing_page"),
      purpose: String(a.purpose ?? ""),
      targetSegmentId: String(
        (Array.isArray(a.target_segment_ids) && a.target_segment_ids[0]) ||
          segments[0]?.id ||
          "",
      ),
      funnelStage: asFunnel(String(a.funnel_stage ?? "awareness")),
      linkedMessage: String(a.linked_message ?? ""),
      dependency: String(a.dependency ?? ""),
      priority: (["critical", "high", "medium", "low"].includes(String(a.priority))
        ? String(a.priority)
        : "medium") as "critical" | "high" | "medium" | "low",
      status: "planned" as const,
    })),
    budget: [
      {
        id: "budget_note",
        section: "policy",
        amountOrRange: "unknown",
        percentageLabel: "n/a",
        rationale: String((dto.budget_policy || {}).notes ?? "Budget policy only"),
        condition: "requires_approval",
        risk: "No guaranteed ROI",
        expectedLearning: "Validate CAC / willingness to pay",
      },
    ],
    metrics: (dto.metrics || []).map((m, i) => ({
      id: String(m.id ?? `met_${i}`),
      category: (["business", "marketing", "validation", "risk_indicator", "stop_loss"].includes(
        String(m.category),
      )
        ? String(m.category)
        : "marketing") as
        | "business"
        | "marketing"
        | "validation"
        | "risk_indicator"
        | "stop_loss",
      name: String(m.name ?? ""),
      purpose: String(m.purpose ?? ""),
      baseline: String(m.baseline ?? ""),
      target: String(m.target ?? ""),
      measurementPeriod: String(m.measurement_period ?? ""),
      dataSource: String(m.data_source ?? ""),
      decisionThreshold: String(m.decision_threshold ?? ""),
      actionIfMissed: String(m.action_if_missed ?? ""),
    })),
    conditions: (dto.verdict_conditions || []).map((c, i) => ({
      id: String(c.verdict_condition_id ?? `cond_${i}`),
      unresolvedCondition: String(c.current_status_snapshot ?? ""),
      requiredAction: String(c.validation_action ?? ""),
      successCriterion: "Verdict domain updates condition status",
      owner: "verdict_authority",
      deadline: "",
      evidenceRequired: "yes",
      effectOnStrategy: String(c.impact_on_strategy ?? ""),
      blocksExecution: Boolean(c.blocking_effect),
    })),
    risks: (dto.strategic_risks || []).map((r, i) => ({
      id: String(r.id ?? `risk_${i}`),
      title: String(r.title ?? ""),
      source: String(r.source ?? ""),
      probability: (["high", "medium", "low"].includes(String(r.probability))
        ? String(r.probability)
        : "medium") as "high" | "medium" | "low",
      severity: (["critical", "high", "medium", "low"].includes(String(r.severity))
        ? String(r.severity)
        : "medium") as "critical" | "high" | "medium" | "low",
      impact: String(r.business_impact ?? ""),
      mitigation: String(r.mitigation ?? ""),
      earlyWarning: String(r.early_warning_indicator ?? ""),
      stopCondition: String(r.stop_condition ?? ""),
      linkedVerdictRiskId: String(r.linked_verdict_risk_id ?? ""),
    })),
    assumptions: (dto.assumptions || []).map((a, i) => ({
      id: String(a.id ?? `asm_${i}`),
      statement: String(a.statement ?? ""),
      source: String(a.source ?? ""),
      confidence: (["high", "medium", "low"].includes(String(a.confidence))
        ? String(a.confidence)
        : "low") as "high" | "medium" | "low",
      validationMethod: String(a.validation_method ?? ""),
      validationStage: String(a.validation_stage ?? ""),
      owner: String(a.owner_role ?? ""),
      impactIfFalse: String(a.impact_if_false ?? ""),
      status: (String(a.status) === "confirmed"
        ? "confirmed"
        : String(a.status) === "invalidated"
          ? "invalidated"
          : String(a.status) === "accepted_for_planning"
            ? "accepted_for_planning"
            : "requires_validation") as
        | "accepted_for_planning"
        | "requires_validation"
        | "confirmed"
        | "invalidated",
    })),
    executionReadiness: {
      status: readiness,
      blockers:
        readiness === "blocked" || readiness === "not_ready"
          ? [`readiness=${readiness}`]
          : [],
      unresolvedConditions: (dto.verdict_conditions || [])
        .filter((c) => Boolean(c.blocking_effect))
        .map((c) => String(c.verdict_condition_id ?? "")),
      missingElements: [],
      nextRequiredAction:
        "Marketing Strategy — это коммерческая стратегия выхода на рынок. Она не является MarketingPlan и не разрешает исполнение.",
      notRealExecutionApproval: true,
    },
  };
}
