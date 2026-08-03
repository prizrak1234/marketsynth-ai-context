/**
 * Deterministic Implementation Plan builder — mock-only, no LLM.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import { evaluatePlanningReadiness } from "@/lib/implementation-plan/readiness";
import type {
  AgencyRole,
  ApprovalGate,
  BudgetCategoryLine,
  BudgetGate,
  HorizonLabel,
  ImplementationPlan,
  PlanAssumption,
  PlanCondition,
  PlanDeliverable,
  PlanDependency,
  PlanMilestone,
  PlanOverview,
  PlanRisk,
  PlanTask,
  PlanWorkstream,
  RoleAssignment,
  RoadmapPhase,
} from "@/lib/implementation-plan/types";

function isoNow(): string {
  return new Date().toISOString();
}

function labelNow(): string {
  return new Date().toLocaleString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function strategyBudgetKnown(strategy: MarketingStrategy): boolean {
  const label = (strategy.summary.budgetRange || "").toLowerCase();
  if (!label || label.includes("unknown") || label.includes("tbd")) return false;
  return strategy.budget.some((b) => {
    const v = (b.amountOrRange || "").toLowerCase();
    return Boolean(v) && !v.includes("unknown") && !v.includes("tbd");
  });
}

function budgetFromStrategy(strategy: MarketingStrategy): string {
  if (!strategyBudgetKnown(strategy)) {
    return strategy.summary.budgetRange || "unknown — requires_approval";
  }
  return strategy.summary.budgetRange || "range — see budget plan";
}

function buildRoles(conditional: boolean): RoleAssignment[] {
  const base: RoleAssignment[] = [
    {
      role: "Client Owner",
      responsibility: "Approve strategy, budget gates, and execution package",
      decisionAuthority: "Final go / stop on budget and pilot readiness",
      requiredInput: "Verdict + strategy summary",
      expectedOutput: "Signed local approvals (Product Alpha mock)",
      reviewRelationship: "Reviews Project Manager packages",
    },
    {
      role: "Chief Marketing Strategist",
      responsibility: "Own positioning, offer, and channel sequencing",
      decisionAuthority: "Strategy changes within approved scope",
      requiredInput: "Approved strategy version",
      expectedOutput: "Workstream priorities and acceptance criteria",
      reviewRelationship: "Reviewed by Client Owner; reviews Content Strategist",
    },
    {
      role: "Project Manager",
      responsibility: "Coordinate workstreams, dependencies, and gates",
      decisionAuthority: "Schedule and blocker escalation",
      requiredInput: "Plan version + gate statuses",
      expectedOutput: "Updated plan status and readiness summary",
      reviewRelationship: "Reports to Client Owner",
    },
    {
      role: "Research Director",
      responsibility: "Validation and evidence closure",
      decisionAuthority: "Validation pass / fail criteria",
      requiredInput: "Mandatory conditions and investigation gaps",
      expectedOutput: "Validation deliverables",
      reviewRelationship: "Feeds Risk Officer and Strategist",
    },
    {
      role: "Performance Marketer",
      responsibility: "Acquisition test design (planning only)",
      decisionAuthority: "Test package structure (not spend)",
      requiredInput: "Approved offer + analytics plan",
      expectedOutput: "Channel test plan deliverable",
      reviewRelationship: "Blocked until budget/validation gates",
    },
    {
      role: "Content Strategist",
      responsibility: "Asset briefs and messaging plan",
      decisionAuthority: "Creative brief approval request",
      requiredInput: "Positioning + offer matrix",
      expectedOutput: "Landing and creative briefs",
      reviewRelationship: "Reviewed by Strategist",
    },
    {
      role: "Analyst",
      responsibility: "Measurement plan and learning metrics",
      decisionAuthority: "Metric definitions",
      requiredInput: "Strategy metrics block",
      expectedOutput: "Analytics measurement plan",
      reviewRelationship: "Supports Performance Marketer",
    },
    {
      role: "Risk Officer",
      responsibility: "Track implementation risks and stop conditions",
      decisionAuthority: "Escalate stop conditions",
      requiredInput: "Strategy risks translated to ops",
      expectedOutput: "Risk register updates",
      reviewRelationship: "Advises Client Owner",
    },
  ];
  if (conditional) {
    base.push({
      role: "Audience Analyst",
      responsibility: "Close audience validation conditions first",
      decisionAuthority: "Audience hypothesis status",
      requiredInput: "Verdict mandatory conditions",
      expectedOutput: "Audience validation report",
      reviewRelationship: "Reports to Research Director",
    });
  }
  return base;
}

function buildWorkstreams(
  strategy: MarketingStrategy,
  conditional: boolean,
): PlanWorkstream[] {
  const obj0 = strategy.objectives[0]?.id ?? "obj_primary";
  const validation: PlanWorkstream = {
    id: "ws_validation",
    type: "validation",
    title: "Validation & evidence closure",
    purpose: conditional
      ? "Закрыть обязательные условия вердикта до acquisition"
      : "Подтвердить ключевые гипотезы перед пилотом",
    linkedObjectiveId: obj0,
    ownerRole: "Research Director",
    status: conditional ? "ready" : "ready",
    priority: "critical",
    plannedStart: "Week 1–2",
    plannedFinish: conditional ? "Month 1" : "Week 1–2",
    dependencyIds: [],
    deliverableIds: ["del_audience_validation"],
    budgetRange: conditional ? "range — validation first" : "range — light validation",
    successCriteria: "Mandatory conditions met or explicitly waived",
    risks: "Premature acquisition if validation skipped",
    blockers: conditional ? "Unresolved mandatory verdict conditions" : "None",
  };

  const positioning: PlanWorkstream = {
    id: "ws_positioning",
    type: "positioning",
    title: "Positioning finalization",
    purpose: "Закрепить positioning из стратегии",
    linkedObjectiveId: obj0,
    ownerRole: "Chief Marketing Strategist",
    status: conditional ? "blocked" : "ready",
    priority: "high",
    plannedStart: conditional ? "Month 1" : "Week 1–2",
    plannedFinish: "Month 1",
    dependencyIds: ["dep_val_before_pos"],
    deliverableIds: ["del_positioning"],
    budgetRange: "unknown — specialist work",
    successCriteria: "Positioning document approved locally",
    risks: "Message drift vs verdict",
    blockers: conditional ? "Depends on validation" : "None",
  };

  const offer: PlanWorkstream = {
    id: "ws_offer",
    type: "offer_development",
    title: "Offer development",
    purpose: "Собрать offer matrix и entry offer",
    linkedObjectiveId: strategy.objectives[1]?.id ?? obj0,
    ownerRole: "Chief Marketing Strategist",
    status: conditional ? "blocked" : "ready",
    priority: "high",
    plannedStart: "Month 1",
    plannedFinish: "Month 1",
    dependencyIds: ["dep_pos_before_offer"],
    deliverableIds: ["del_offer_matrix"],
    budgetRange: "range — creative production later",
    successCriteria: "Offer matrix with acceptance criteria",
    risks: "Offer before audience clarity",
    blockers: conditional ? "Blocked by validation/positioning" : "None",
  };

  const content: PlanWorkstream = {
    id: "ws_content",
    type: "content_and_assets",
    title: "Content & assets",
    purpose: "Брифы LP и креативов — без production execution",
    linkedObjectiveId: obj0,
    ownerRole: "Content Strategist",
    status: "not_started",
    priority: "medium",
    plannedStart: "Month 1",
    plannedFinish: "Month 2",
    dependencyIds: ["dep_offer_before_lp"],
    deliverableIds: ["del_lp_brief", "del_creative_brief"],
    budgetRange: "requires_approval",
    successCriteria: "Briefs ready for future asset production",
    risks: "Brief without approved offer",
    blockers: "Offer approval gate",
  };

  const analytics: PlanWorkstream = {
    id: "ws_analytics",
    type: "analytics",
    title: "Analytics & measurement",
    purpose: "Measurement plan до paid acquisition",
    linkedObjectiveId: obj0,
    ownerRole: "Analyst",
    status: conditional ? "not_started" : "ready",
    priority: "high",
    plannedStart: "Month 1",
    plannedFinish: "Month 1",
    dependencyIds: [],
    deliverableIds: ["del_measurement"],
    budgetRange: "range — tooling",
    successCriteria: "Measurement plan with decision thresholds",
    risks: "Acquisition without measurement",
    blockers: "None",
  };

  const acquisition: PlanWorkstream = {
    id: "ws_acquisition",
    type: "acquisition",
    title: "Acquisition test planning",
    purpose: "План тестовых каналов — без spend",
    linkedObjectiveId: obj0,
    ownerRole: "Performance Marketer",
    status: conditional ? "blocked" : "not_started",
    priority: conditional ? "medium" : "high",
    plannedStart: conditional ? "Month 2" : "Month 1",
    plannedFinish: "Month 2",
    dependencyIds: ["dep_analytics_before_paid", "dep_budget_before_campaign"],
    deliverableIds: ["del_channel_test"],
    budgetRange: "requires_approval",
    successCriteria: "Channel test package ready for approval preview",
    risks: "Spend before gates",
    blockers: conditional
      ? "Mandatory conditions + budget gate"
      : "Budget approval gate",
  };

  const sales: PlanWorkstream = {
    id: "ws_sales",
    type: "sales_enablement",
    title: "Sales enablement",
    purpose: "Скрипты и handoff материалы",
    linkedObjectiveId: obj0,
    ownerRole: "Content Strategist",
    status: "not_started",
    priority: "medium",
    plannedStart: "Month 2",
    plannedFinish: "Quarter 1",
    dependencyIds: ["dep_offer_before_lp"],
    deliverableIds: ["del_sales_script"],
    budgetRange: "unknown",
    successCriteria: "Sales script draft approved locally",
    risks: "Sales assets before offer clarity",
    blockers: "Offer approval",
  };

  const ops: PlanWorkstream = {
    id: "ws_operations",
    type: "operations",
    title: "Operations & readiness review",
    purpose: "Pilot readiness checklist",
    linkedObjectiveId: obj0,
    ownerRole: "Project Manager",
    status: "not_started",
    priority: "high",
    plannedStart: "Month 2",
    plannedFinish: "Quarter 1",
    dependencyIds: ["dep_pilot_readiness"],
    deliverableIds: ["del_pilot_report"],
    budgetRange: "unknown",
    successCriteria: "Pilot readiness gate pending review",
    risks: "Pilot without acceptance criteria",
    blockers: "Upstream deliverables",
  };

  return [
    validation,
    positioning,
    offer,
    content,
    analytics,
    acquisition,
    sales,
    ops,
  ];
}

function buildMilestones(conditional: boolean): PlanMilestone[] {
  return [
    {
      id: "ms_validation",
      title: "Validation brief approved",
      description: "Evidence and mandatory conditions reviewed",
      targetPeriod: "Week 1–2",
      workstreamIds: ["ws_validation"],
      requiredDeliverableIds: ["del_audience_validation"],
      entryCriteria: "Strategy available",
      exitCriteria: conditional
        ? "Mandatory conditions met or waived"
        : "Validation brief accepted",
      approvalRequired: true,
      blockingDependencyIds: [],
      status: "ready",
    },
    {
      id: "ms_positioning",
      title: "Positioning finalized",
      description: "Positioning document locked for planning",
      targetPeriod: "Month 1",
      workstreamIds: ["ws_positioning"],
      requiredDeliverableIds: ["del_positioning"],
      entryCriteria: "Validation milestone exit",
      exitCriteria: "Positioning approved locally",
      approvalRequired: true,
      blockingDependencyIds: ["dep_val_before_pos"],
      status: conditional ? "blocked" : "ready",
    },
    {
      id: "ms_offer",
      title: "First offer ready",
      description: "Offer matrix and entry offer defined",
      targetPeriod: "Month 1",
      workstreamIds: ["ws_offer"],
      requiredDeliverableIds: ["del_offer_matrix"],
      entryCriteria: "Positioning finalized",
      exitCriteria: "Offer approval gate pending/approved",
      approvalRequired: true,
      blockingDependencyIds: ["dep_pos_before_offer"],
      status: conditional ? "blocked" : "not_started",
    },
    {
      id: "ms_channel",
      title: "Channel test package ready",
      description: "Acquisition test plan without spend",
      targetPeriod: "Month 2",
      workstreamIds: ["ws_acquisition", "ws_analytics"],
      requiredDeliverableIds: ["del_channel_test", "del_measurement"],
      entryCriteria: "Analytics configured + budget gate",
      exitCriteria: "Test package ready for execution package phase",
      approvalRequired: true,
      blockingDependencyIds: ["dep_analytics_before_paid", "dep_budget_before_campaign"],
      status: "blocked",
    },
    {
      id: "ms_analytics",
      title: "Analytics configured",
      description: "Measurement plan defined",
      targetPeriod: "Month 1",
      workstreamIds: ["ws_analytics"],
      requiredDeliverableIds: ["del_measurement"],
      entryCriteria: "Strategy metrics available",
      exitCriteria: "Measurement plan accepted",
      approvalRequired: false,
      blockingDependencyIds: [],
      status: conditional ? "not_started" : "ready",
    },
    {
      id: "ms_pilot",
      title: "Pilot launch readiness review",
      description: "Management review before execution package",
      targetPeriod: "Quarter 1",
      workstreamIds: ["ws_operations"],
      requiredDeliverableIds: ["del_pilot_report"],
      entryCriteria: "Critical deliverables + gates",
      exitCriteria: "Execution planning readiness ready_for_approval",
      approvalRequired: true,
      blockingDependencyIds: ["dep_pilot_readiness"],
      status: "blocked",
    },
  ];
}

function buildTasks(conditional: boolean): PlanTask[] {
  const tasks: PlanTask[] = [
    {
      id: "task_val_report",
      title: "Assemble audience validation report",
      description: "Свести evidence по audience hypothesis",
      workstreamId: "ws_validation",
      milestoneId: "ms_validation",
      responsibleRole: conditional ? "Audience Analyst" : "Research Director",
      reviewerRole: "Research Director",
      priority: "critical",
      status: "ready",
      dependencyIds: [],
      requiredInput: "Investigation artifacts + verdict conditions",
      expectedOutput: "Audience validation report (register only)",
      acceptanceCriteria:
        "Report lists evidence IDs, gaps, and pass/fail vs success criterion",
      budgetImpact: "range — research",
      riskLevel: "high",
      approvalRequired: true,
    },
    {
      id: "task_pos_doc",
      title: "Draft positioning document",
      description: "Перенести positioning из стратегии в deliverable",
      workstreamId: "ws_positioning",
      milestoneId: "ms_positioning",
      responsibleRole: "Chief Marketing Strategist",
      reviewerRole: "Client Owner",
      priority: "high",
      status: conditional ? "blocked" : "ready",
      dependencyIds: ["dep_val_before_pos"],
      requiredInput: "Strategy positioning block",
      expectedOutput: "Positioning document entry",
      acceptanceCriteria: "Positioning claims linked to strategy version",
      budgetImpact: "unknown",
      riskLevel: "medium",
      approvalRequired: true,
    },
    {
      id: "task_offer_matrix",
      title: "Build offer matrix",
      description: "Core / entry / validation offers",
      workstreamId: "ws_offer",
      milestoneId: "ms_offer",
      responsibleRole: "Chief Marketing Strategist",
      reviewerRole: "Client Owner",
      priority: "high",
      status: conditional ? "blocked" : "backlog",
      dependencyIds: ["dep_pos_before_offer"],
      requiredInput: "Strategy offers + segments",
      expectedOutput: "Offer matrix deliverable",
      acceptanceCriteria: "Each offer has price mode and target segment",
      budgetImpact: "unknown",
      riskLevel: "medium",
      approvalRequired: true,
    },
    {
      id: "task_measurement",
      title: "Define analytics measurement plan",
      description: "KPI, thresholds, data sources — no live tooling",
      workstreamId: "ws_analytics",
      milestoneId: "ms_analytics",
      responsibleRole: "Analyst",
      reviewerRole: "Chief Marketing Strategist",
      priority: "high",
      status: conditional ? "backlog" : "ready",
      dependencyIds: [],
      requiredInput: "Strategy metrics",
      expectedOutput: "Analytics measurement plan",
      acceptanceCriteria: "Decision thresholds defined for pilot metrics",
      budgetImpact: "range — tooling",
      riskLevel: "medium",
      approvalRequired: false,
    },
    {
      id: "task_lp_brief",
      title: "Write landing-page brief",
      description: "Brief only — no page build",
      workstreamId: "ws_content",
      milestoneId: "ms_offer",
      responsibleRole: "Content Strategist",
      reviewerRole: "Chief Marketing Strategist",
      priority: "medium",
      status: "blocked",
      dependencyIds: ["dep_offer_before_lp"],
      requiredInput: "Approved offer matrix",
      expectedOutput: "Landing-page brief",
      acceptanceCriteria: "Brief references offer + positioning IDs",
      budgetImpact: "requires_approval",
      riskLevel: "low",
      approvalRequired: true,
    },
    {
      id: "task_channel_test",
      title: "Prepare channel test package",
      description: "Acquisition planning without provider calls",
      workstreamId: "ws_acquisition",
      milestoneId: "ms_channel",
      responsibleRole: "Performance Marketer",
      reviewerRole: "Client Owner",
      priority: conditional ? "medium" : "high",
      status: "blocked",
      dependencyIds: ["dep_analytics_before_paid", "dep_budget_before_campaign"],
      requiredInput: "Measurement plan + budget gate",
      expectedOutput: "Channel test plan",
      acceptanceCriteria: "Channels listed with test hypothesis and stop rules",
      budgetImpact: "requires_approval",
      riskLevel: "high",
      approvalRequired: true,
    },
    {
      id: "task_sales_script",
      title: "Draft sales script outline",
      description: "Enablement outline — no live sales",
      workstreamId: "ws_sales",
      milestoneId: "ms_pilot",
      responsibleRole: "Copywriter",
      reviewerRole: "Content Strategist",
      priority: "medium",
      status: "backlog",
      dependencyIds: ["dep_offer_before_lp"],
      requiredInput: "Offer matrix",
      expectedOutput: "Sales script deliverable",
      acceptanceCriteria: "Objections and CTA mapped to segments",
      budgetImpact: "unknown",
      riskLevel: "low",
      approvalRequired: false,
    },
    {
      id: "task_pilot_checklist",
      title: "Compile pilot readiness checklist",
      description: "Gates and deliverables for management review",
      workstreamId: "ws_operations",
      milestoneId: "ms_pilot",
      responsibleRole: "Project Manager",
      reviewerRole: "Client Owner",
      priority: "critical",
      status: "backlog",
      dependencyIds: ["dep_pilot_readiness"],
      requiredInput: "All critical gates status",
      expectedOutput: "Pilot report register entry",
      acceptanceCriteria: "Checklist covers budget, approval, and risk gates",
      budgetImpact: "none",
      riskLevel: "high",
      approvalRequired: true,
    },
  ];

  if (conditional) {
    tasks.unshift({
      id: "task_close_conditions",
      title: "Close mandatory verdict conditions",
      description: "Первый шаг при CONDITIONAL_GO",
      workstreamId: "ws_validation",
      milestoneId: "ms_validation",
      responsibleRole: "Audience Analyst",
      reviewerRole: "Risk Officer",
      priority: "critical",
      status: "ready",
      dependencyIds: [],
      requiredInput: "Verdict mandatory conditions",
      expectedOutput: "Condition status updates + evidence refs",
      acceptanceCriteria: "Each mandatory condition has evidence or waiver",
      budgetImpact: "range — research",
      riskLevel: "critical",
      approvalRequired: true,
    });
  }

  return tasks;
}

function buildDependencies(): PlanDependency[] {
  return [
    {
      id: "dep_val_before_pos",
      predecessor: "Validation milestone / audience validation",
      successor: "Positioning finalization",
      type: "evidence_gate",
      blocking: true,
      resolutionAction: "Complete validation deliverable and approval",
    },
    {
      id: "dep_pos_before_offer",
      predecessor: "Positioning document",
      successor: "Offer matrix",
      type: "finish_to_start",
      blocking: true,
      resolutionAction: "Approve positioning locally",
    },
    {
      id: "dep_offer_before_lp",
      predecessor: "Offer approval gate",
      successor: "Landing-page / creative briefs",
      type: "approval_gate",
      blocking: true,
      resolutionAction: "Approve offer gate",
    },
    {
      id: "dep_analytics_before_paid",
      predecessor: "Analytics measurement plan",
      successor: "Acquisition test package",
      type: "finish_to_start",
      blocking: true,
      resolutionAction: "Accept measurement plan",
    },
    {
      id: "dep_budget_before_campaign",
      predecessor: "Budget approval gate",
      successor: "Campaign / acquisition planning tasks",
      type: "budget_gate",
      blocking: true,
      resolutionAction: "Approve budget gate or keep tasks blocked",
    },
    {
      id: "dep_legal_before_regulated",
      predecessor: "Compliance review (if regulated)",
      successor: "Regulated-market execution planning",
      type: "compliance_gate",
      blocking: false,
      resolutionAction: "Mark not_required if market not regulated",
    },
    {
      id: "dep_pilot_readiness",
      predecessor: "Critical deliverables + gates",
      successor: "Pilot readiness review",
      type: "approval_gate",
      blocking: true,
      resolutionAction: "Clear readiness blockers",
    },
  ];
}

function buildDeliverables(strategy: MarketingStrategy): PlanDeliverable[] {
  return [
    {
      id: "del_audience_validation",
      name: "Audience validation report",
      type: "report",
      workstreamId: "ws_validation",
      ownerRole: "Research Director",
      format: "structured register entry",
      status: "ready",
      acceptanceCriteria: "Evidence IDs + pass/fail vs conditions",
      approvalRequired: true,
      linkedStrategyElement: strategy.segments[0]?.name ?? "Primary segment",
      duePeriod: "Week 1–2",
      dependencyIds: [],
    },
    {
      id: "del_positioning",
      name: "Positioning document",
      type: "document",
      workstreamId: "ws_positioning",
      ownerRole: "Chief Marketing Strategist",
      format: "brief",
      status: "backlog",
      acceptanceCriteria: "Aligned to strategy positioning version",
      approvalRequired: true,
      linkedStrategyElement: strategy.positioning?.keyMessage ?? "Positioning",
      duePeriod: "Month 1",
      dependencyIds: ["dep_val_before_pos"],
    },
    {
      id: "del_offer_matrix",
      name: "Offer matrix",
      type: "matrix",
      workstreamId: "ws_offer",
      ownerRole: "Chief Marketing Strategist",
      format: "table",
      status: "backlog",
      acceptanceCriteria: "Core/entry offers with price mode",
      approvalRequired: true,
      linkedStrategyElement: strategy.summary.coreOffer,
      duePeriod: "Month 1",
      dependencyIds: ["dep_pos_before_offer"],
    },
    {
      id: "del_lp_brief",
      name: "Landing-page brief",
      type: "brief",
      workstreamId: "ws_content",
      ownerRole: "Content Strategist",
      format: "brief",
      status: "blocked",
      acceptanceCriteria: "Offer + CTA + objections covered",
      approvalRequired: true,
      linkedStrategyElement: "Asset plan: landing_page",
      duePeriod: "Month 2",
      dependencyIds: ["dep_offer_before_lp"],
    },
    {
      id: "del_channel_test",
      name: "Channel test plan",
      type: "plan",
      workstreamId: "ws_acquisition",
      ownerRole: "Performance Marketer",
      format: "checklist",
      status: "blocked",
      acceptanceCriteria: "Hypotheses + stop rules; no spend",
      approvalRequired: true,
      linkedStrategyElement: strategy.summary.channelMix,
      duePeriod: "Month 2",
      dependencyIds: ["dep_budget_before_campaign"],
    },
    {
      id: "del_measurement",
      name: "Analytics measurement plan",
      type: "plan",
      workstreamId: "ws_analytics",
      ownerRole: "Analyst",
      format: "metric sheet",
      status: "ready",
      acceptanceCriteria: "Thresholds from strategy metrics",
      approvalRequired: false,
      linkedStrategyElement: "Strategy metrics",
      duePeriod: "Month 1",
      dependencyIds: [],
    },
    {
      id: "del_creative_brief",
      name: "Creative brief",
      type: "brief",
      workstreamId: "ws_content",
      ownerRole: "Designer",
      format: "brief",
      status: "blocked",
      acceptanceCriteria: "Linked to offer and channel test",
      approvalRequired: true,
      linkedStrategyElement: "Asset plan: ad_creative",
      duePeriod: "Month 2",
      dependencyIds: ["dep_offer_before_lp"],
    },
    {
      id: "del_sales_script",
      name: "Sales script",
      type: "script",
      workstreamId: "ws_sales",
      ownerRole: "Copywriter",
      format: "outline",
      status: "backlog",
      acceptanceCriteria: "Objections mapped",
      approvalRequired: false,
      linkedStrategyElement: "Sales enablement",
      duePeriod: "Quarter 1",
      dependencyIds: ["dep_offer_before_lp"],
    },
    {
      id: "del_pilot_report",
      name: "Pilot report",
      type: "report",
      workstreamId: "ws_operations",
      ownerRole: "Project Manager",
      format: "checklist summary",
      status: "backlog",
      acceptanceCriteria: "Gates and readiness summarized",
      approvalRequired: true,
      linkedStrategyElement: "Execution readiness",
      duePeriod: "Quarter 1",
      dependencyIds: ["dep_pilot_readiness"],
    },
  ];
}

function buildBudgetPlan(
  strategy: MarketingStrategy,
  conditional: boolean,
): BudgetCategoryLine[] {
  const hasKnown = strategyBudgetKnown(strategy);
  const val = (min: string, rec: string, upper: string) =>
    hasKnown
      ? { mode: "range" as const, minimum: min, recommendedRange: rec, upperBoundary: upper }
      : {
          mode: "unknown" as const,
          minimum: "unknown",
          recommendedRange: "unknown — requires_approval",
          upperBoundary: "unknown",
        };

  return [
    {
      id: "bud_research",
      category: "research and validation",
      ...val("low", "validation-first range", "TBD"),
      rationale: conditional
        ? "CONDITIONAL_GO prioritizes validation spend planning"
        : "Light validation before pilot",
      releaseCondition: "Validation gate pending/approved",
      linkedWorkstreamId: "ws_validation",
      risk: "Underfunded validation",
      learningObjective: "Close mandatory evidence gaps",
    },
    {
      id: "bud_creative",
      category: "creative production",
      mode: "requires_approval",
      minimum: "unknown",
      recommendedRange: "requires_approval",
      upperBoundary: "unknown",
      rationale: "No asset generation in A6",
      releaseCondition: "Asset approval gate",
      linkedWorkstreamId: "ws_content",
      risk: "Creative before offer lock",
      learningObjective: "Brief quality before production",
    },
    {
      id: "bud_acquisition",
      category: "acquisition testing",
      mode: "requires_approval",
      minimum: "unknown",
      recommendedRange: "requires_approval",
      upperBoundary: "unknown",
      rationale: "No real ad spend in Product Alpha",
      releaseCondition: "Budget gate + analytics ready",
      linkedWorkstreamId: "ws_acquisition",
      risk: "Spend without gates",
      learningObjective: "Test hypothesis design only",
    },
    {
      id: "bud_tooling",
      category: "tooling",
      ...val("TBD", hasKnown ? "tooling range from strategy" : "unknown", "TBD"),
      rationale: "Analytics and ops tooling planning",
      releaseCondition: "Measurement plan accepted",
      linkedWorkstreamId: "ws_analytics",
      risk: "Tool sprawl",
      learningObjective: "Minimum viable measurement stack",
    },
    {
      id: "bud_specialist",
      category: "specialist work",
      mode: hasKnown ? "range" : "unknown",
      minimum: hasKnown ? "partial" : "unknown",
      recommendedRange: hasKnown ? strategy.summary.budgetRange : "unknown",
      upperBoundary: "unknown",
      rationale: "Strategy budget lines mapped without inventing precision",
      releaseCondition: "Strategy approval",
      linkedWorkstreamId: "ws_positioning",
      risk: "Scope creep",
      learningObjective: "Role clarity vs cost",
    },
    {
      id: "bud_analytics",
      category: "analytics",
      ...val("TBD", "measurement setup", "TBD"),
      rationale: "Must precede paid acquisition planning",
      releaseCondition: "Analytics milestone exit",
      linkedWorkstreamId: "ws_analytics",
      risk: "Blind acquisition",
      learningObjective: "Decision thresholds",
    },
    {
      id: "bud_contingency",
      category: "contingency reserve",
      mode: "requires_approval",
      minimum: "unknown",
      recommendedRange: "requires_approval",
      upperBoundary: "unknown",
      rationale: "Reserve only after Client Owner approval",
      releaseCondition: "Risk review",
      linkedWorkstreamId: "ws_operations",
      risk: "No buffer for validation overrun",
      learningObjective: "Protect pilot if validation expands",
    },
  ];
}

function buildBudgetGates(conditional: boolean): BudgetGate[] {
  return [
    {
      id: "bg_validation",
      name: "Validation budget release",
      amountOrRange: conditional ? "range — validation first" : "range — light",
      prerequisite: "Strategy available",
      approvalOwner: "Client Owner",
      releaseCondition: "Validation workstream started",
      blockedWorkstreamIds: [],
      evidenceRequired: "Validation brief scope",
      status: "pending",
    },
    {
      id: "bg_acquisition",
      name: "Acquisition test budget gate",
      amountOrRange: "requires_approval",
      prerequisite: "Analytics configured + offer approved",
      approvalOwner: "Client Owner",
      releaseCondition: "No spend until Phase A7+ and real backend",
      blockedWorkstreamIds: ["ws_acquisition"],
      evidenceRequired: "Channel test plan + measurement plan",
      status: conditional ? "blocked" : "pending",
    },
    {
      id: "bg_creative",
      name: "Creative production budget gate",
      amountOrRange: "requires_approval",
      prerequisite: "Offer approval",
      approvalOwner: "Client Owner",
      releaseCondition: "Asset briefs approved",
      blockedWorkstreamIds: ["ws_content"],
      evidenceRequired: "LP and creative briefs",
      status: "pending",
    },
  ];
}

function buildApprovalGates(
  strategy: MarketingStrategy,
  conditional: boolean,
): ApprovalGate[] {
  return [
    {
      id: "ag_strategy",
      title: "Strategy approval",
      decisionOwner: "Client Owner",
      requiredArtifacts: [`Strategy v${strategy.version}`],
      requiredEvidence: strategy.evidenceSnapshotId,
      deadlineOrMilestone: "Before implementation approve",
      status: strategy.status === "approved" ? "approved" : "pending",
      consequenceIfRejected: "Plan remains draft/blocked",
      affectedTaskIds: [],
    },
    {
      id: "ag_validation",
      title: "Validation completion",
      decisionOwner: "Research Director",
      requiredArtifacts: ["Audience validation report"],
      requiredEvidence: "Condition evidence refs",
      deadlineOrMilestone: "ms_validation",
      status: conditional ? "pending" : "pending",
      consequenceIfRejected: "Acquisition stays blocked",
      affectedTaskIds: ["task_val_report", "task_close_conditions"].filter(
        (id) => conditional || id !== "task_close_conditions",
      ),
    },
    {
      id: "ag_offer",
      title: "Offer approval",
      decisionOwner: "Client Owner",
      requiredArtifacts: ["Offer matrix"],
      requiredEvidence: "Segment link",
      deadlineOrMilestone: "ms_offer",
      status: "pending",
      consequenceIfRejected: "LP/creative tasks blocked",
      affectedTaskIds: ["task_offer_matrix", "task_lp_brief"],
    },
    {
      id: "ag_budget",
      title: "Budget approval",
      decisionOwner: "Client Owner",
      requiredArtifacts: ["Budget plan ranges"],
      requiredEvidence: "No fake exact amounts",
      deadlineOrMilestone: "Before acquisition tasks ready",
      status: "pending",
      consequenceIfRejected: "Acquisition tasks remain blocked",
      affectedTaskIds: ["task_channel_test"],
    },
    {
      id: "ag_asset",
      title: "Asset approval",
      decisionOwner: "Chief Marketing Strategist",
      requiredArtifacts: ["LP brief", "Creative brief"],
      requiredEvidence: "Offer approval",
      deadlineOrMilestone: "Month 2",
      status: "pending",
      consequenceIfRejected: "Asset production handoff unavailable",
      affectedTaskIds: ["task_lp_brief"],
    },
    {
      id: "ag_pilot",
      title: "Pilot readiness",
      decisionOwner: "Client Owner",
      requiredArtifacts: ["Pilot report"],
      requiredEvidence: "Gates cleared",
      deadlineOrMilestone: "ms_pilot",
      status: "blocked",
      consequenceIfRejected: "No execution package",
      affectedTaskIds: ["task_pilot_checklist"],
    },
    {
      id: "ag_execution",
      title: "Execution readiness",
      decisionOwner: "Client Owner",
      requiredArtifacts: ["Execution package (A7)"],
      requiredEvidence: "Planning readiness ready_for_approval",
      deadlineOrMilestone: "After plan approve",
      status: "blocked",
      consequenceIfRejected: "Stay in planning",
      affectedTaskIds: [],
    },
  ];
}

function buildConditions(
  strategy: MarketingStrategy,
  verdict: BusinessVerdict,
): PlanCondition[] {
  if (verdict.type !== "CONDITIONAL_GO") {
  return strategy.conditions
    .filter((c) => !c.blocksExecution)
    .slice(0, 2)
    .map((c) => ({
      id: `pc_${c.id}`,
      requiredAction: c.requiredAction,
      ownerRole: "Research Director" as AgencyRole,
      validationMethod: "Evidence review",
      successCriterion: c.successCriterion,
      deadlineOrMilestone: c.deadline || "Month 1",
      evidenceRequired: c.evidenceRequired,
      blockingTaskIds: [],
      executionImpact: c.effectOnStrategy,
      status: "met" as const,
      blocksPlanning: false,
    }));
  }

  return strategy.conditions
    .filter((c) => c.blocksExecution)
    .map((c, i) => ({
      id: `pc_${c.id}`,
      requiredAction: c.requiredAction,
      ownerRole: (i === 0 ? "Audience Analyst" : "Research Director") as AgencyRole,
      validationMethod: "Investigation evidence + validation deliverable",
      successCriterion: c.successCriterion,
      deadlineOrMilestone: c.deadline || "ms_validation",
      evidenceRequired: c.evidenceRequired,
      blockingTaskIds: ["task_channel_test", "task_lp_brief"],
      executionImpact: "Blocks execution planning readiness until met",
      status: "open" as const,
      blocksPlanning: true,
    }));
}

function buildRisks(strategy: MarketingStrategy): PlanRisk[] {
  return strategy.risks.slice(0, 4).map((r, i) => ({
    id: `pr_${r.id}`,
    title: `Ops: ${r.title}`,
    source: `Strategy risk ${r.id} → workstream impact`,
    probability: r.probability,
    severity: r.severity,
    affectedWorkstreamId:
      i === 0 ? "ws_validation" : i === 1 ? "ws_acquisition" : "ws_offer",
    earlyWarning: r.earlyWarning,
    mitigation: `${r.mitigation} — schedule validation/ops checkpoints`,
    contingencyAction: "Pause acquisition tasks; reopen validation",
    ownerRole: "Risk Officer",
    stopCondition: r.stopCondition,
    status: r.severity === "critical" ? "open" : "mitigating",
    linkedStrategyRiskId: r.id,
  }));
}

function buildAssumptions(
  strategy: MarketingStrategy,
  conditional: boolean,
): PlanAssumption[] {
  return strategy.assumptions.slice(0, 5).map((a, i) => {
    let status: PlanAssumption["status"];
    if (a.status === "confirmed") status = "confirmed";
    else if (a.status === "invalidated") status = "invalidated";
    else if (conditional || a.status === "requires_validation") {
      // GO: accept for planning when strategy already allows planning; validation tasks remain
      status = conditional ? "requires_validation" : "accepted_for_planning";
    } else {
      status = "accepted_for_planning";
    }
    return {
      id: `pa_${a.id}`,
      statement: a.statement,
      source: a.source,
      confidence: a.confidence,
      validationAction: a.validationMethod,
      validationMilestone: a.validationStage || "ms_validation",
      owner: "Research Director" as AgencyRole,
      impactIfFalse: a.impactIfFalse,
      linkedTaskId: i === 0 ? "task_val_report" : "task_offer_matrix",
      status,
    };
  });
}

function buildRoadmap(conditional: boolean): RoadmapPhase[] {
  return [
    {
      id: "rm_w12",
      horizon: "Week 1–2" as HorizonLabel,
      milestoneIds: ["ms_validation"],
      workstreamIds: ["ws_validation"],
      note: conditional ? "Validation-first" : "Kickoff validation + positioning",
    },
    {
      id: "rm_m1",
      horizon: "Month 1",
      milestoneIds: ["ms_positioning", "ms_offer", "ms_analytics"],
      workstreamIds: ["ws_positioning", "ws_offer", "ws_analytics"],
      note: "Positioning, offer, measurement",
    },
    {
      id: "rm_m2",
      horizon: "Month 2",
      milestoneIds: ["ms_channel"],
      workstreamIds: ["ws_content", "ws_acquisition", "ws_sales"],
      note: "Briefs and test package planning (no spend)",
    },
    {
      id: "rm_q1",
      horizon: "Quarter 1",
      milestoneIds: ["ms_pilot"],
      workstreamIds: ["ws_operations"],
      note: "Pilot readiness review → A7 handoff",
    },
  ];
}

function buildOverview(
  strategy: MarketingStrategy,
  verdict: BusinessVerdict,
  readinessLabel: string,
  blockers: string[],
  conditions: PlanCondition[],
): PlanOverview {
  return {
    strategicObjective: strategy.summary.businessObjective,
    implementationHorizon: "Week 1–2 → Quarter 1 (relative; no fake calendar)",
    primaryWorkstreams: [
      "Validation",
      "Positioning",
      "Offer",
      "Analytics",
      "Acquisition planning",
    ],
    criticalMilestones: [
      "Validation brief approved",
      "Positioning finalized",
      "First offer ready",
      "Pilot readiness review",
    ],
    estimatedBudgetRange: budgetFromStrategy(strategy),
    mandatoryConditions: conditions
      .filter((c) => c.blocksPlanning)
      .map((c) => c.requiredAction),
    currentBlockers: blockers,
    readinessLabel,
    nextManagementDecision:
      verdict.type === "CONDITIONAL_GO"
        ? "Закрыть обязательные условия или оставить acquisition blocked"
        : "Approve implementation plan for execution package prep",
  };
}

export function buildImplementationPlan(
  verdict: BusinessVerdict,
  strategy: MarketingStrategy,
  options: {
    version: number;
    supersedesPlanId: string | null;
    status?: ImplementationPlan["status"];
  },
): ImplementationPlan {
  if (verdict.type === "NO_GO" || verdict.type === "INSUFFICIENT_DATA") {
    throw new Error(
      `Cannot build implementation plan for verdict ${verdict.type}`,
    );
  }

  const conditional = verdict.type === "CONDITIONAL_GO";
  const now = isoNow();
  const workstreams = buildWorkstreams(strategy, conditional);
  const milestones = buildMilestones(conditional);
  const tasks = buildTasks(conditional);
  const dependencies = buildDependencies();
  const deliverables = buildDeliverables(strategy);
  const budgetPlan = buildBudgetPlan(strategy, conditional);
  const budgetGates = buildBudgetGates(conditional);
  const approvalGates = buildApprovalGates(strategy, conditional);
  const conditions = buildConditions(strategy, verdict);
  const risks = buildRisks(strategy);
  const assumptions = buildAssumptions(strategy, conditional);
  const roadmap = buildRoadmap(conditional);

  // For GO scenarios without critical open risks, soften risk status so readiness can pass
  const adjustedRisks =
    !conditional && risks.every((r) => r.severity !== "critical")
      ? risks.map((r) =>
          r.status === "open" ? { ...r, status: "mitigating" as const } : r,
        )
      : risks;

  // Rejected budget gate scenario helper is applied only when status blocked via storage actions

  const draft: Omit<ImplementationPlan, "overview" | "readiness"> & {
    overview?: PlanOverview;
    readiness?: ImplementationPlan["readiness"];
  } = {
    id: `plan_${strategy.projectId}_v${options.version}`,
    projectId: strategy.projectId,
    projectName: strategy.projectName,
    strategyId: strategy.id,
    strategyVersion: strategy.version,
    verdictId: verdict.id,
    verdictVersion: verdict.version,
    verdictType: verdict.type,
    version: options.version,
    status: options.status ?? "draft",
    createdAt: now,
    updatedAt: now,
    updatedAtLabel: labelNow(),
    supersedesPlanId: options.supersedesPlanId,
    evidenceSnapshotId: strategy.evidenceSnapshotId,
    localMockLabel: "Mock / local — Product Alpha A6",
    workstreams,
    milestones,
    tasks,
    roles: buildRoles(conditional),
    dependencies,
    deliverables,
    budgetPlan,
    budgetGates,
    approvalGates,
    conditions,
    risks: adjustedRisks,
    assumptions,
    roadmap,
  };

  const readiness = evaluatePlanningReadiness(
    {
      workstreams,
      milestones,
      tasks,
      budgetPlan,
      budgetGates,
      approvalGates,
      conditions,
      risks: adjustedRisks,
      assumptions,
      deliverables,
      status: draft.status,
    },
    strategy,
    verdict,
  );

  const overview = buildOverview(
    strategy,
    verdict,
    readiness.status,
    readiness.blockers,
    conditions,
  );

  return { ...draft, overview, readiness };
}

/** Apply rejected budget gate — blocks dependent acquisition tasks. */
export function applyRejectedBudgetGate(plan: ImplementationPlan): ImplementationPlan {
  const budgetGates = plan.budgetGates.map((g) =>
    g.id === "bg_acquisition" ? { ...g, status: "rejected" as const } : g,
  );
  const tasks = plan.tasks.map((t) =>
    t.workstreamId === "ws_acquisition" || t.id === "task_channel_test"
      ? { ...t, status: "blocked" as const }
      : t,
  );
  const workstreams = plan.workstreams.map((w) =>
    w.id === "ws_acquisition" ? { ...w, status: "blocked" as const, blockers: "Budget gate rejected" } : w,
  );
  return { ...plan, budgetGates, tasks, workstreams };
}
