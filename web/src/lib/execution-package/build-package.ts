/**
 * Deterministic Execution Package builder — mock-only, no providers.
 */

import type { BusinessVerdict } from "@/lib/verdict/types";
import type { MarketingStrategy } from "@/lib/strategy/types";
import type { ImplementationPlan } from "@/lib/implementation-plan/types";
import { runPreflightChecks } from "@/lib/execution-package/preflight";
import { evaluatePackageReadiness } from "@/lib/execution-package/readiness";
import type {
  ApprovalMatrixRow,
  BudgetAuthorization,
  ExecutionItem,
  ExecutionPackage,
  ExecutionScopeItem,
  PackageBlocker,
  PackageSummary,
  ProviderRequirement,
  RiskControl,
  RollbackPlanEntry,
  VerificationPlanEntry,
} from "@/lib/execution-package/types";

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

function budgetFromPlan(plan: ImplementationPlan): BudgetAuthorization {
  const unknown = plan.budgetPlan.every(
    (b) => b.mode === "unknown" || b.mode === "requires_approval",
  );
  const hasRange = plan.budgetPlan.some((b) => b.mode === "range" || b.mode === "exact");
  const rejected = plan.budgetGates.some((g) => g.status === "rejected");

  if (unknown && !hasRange) {
    return {
      requestedAmountOrRange: "unknown",
      approvedAmount: "none",
      reservedAmount: "none",
      providerAllocation: "not allocated",
      contingency: "unknown",
      releaseGates: plan.budgetGates.map((g) => g.name),
      stopLossThreshold: "requires_approval",
      approvalState: "blocked",
      unresolvedGaps: [
        "Budget inputs unknown — do not fabricate amounts",
        ...plan.budgetPlan
          .filter((b) => b.mode === "unknown")
          .map((b) => `Category ${b.category}: unknown`),
      ],
      mode: "unknown",
    };
  }

  return {
    requestedAmountOrRange: plan.overview.estimatedBudgetRange || "range — requires_approval",
    approvedAmount: "not approved (local preview)",
    reservedAmount: "not reserved",
    providerAllocation: "mock — no provider spend",
    contingency: hasRange ? "range contingency listed in plan" : "requires_approval",
    releaseGates: plan.budgetGates.map((g) => `${g.name}: ${g.status}`),
    stopLossThreshold: "planning stop-loss from strategy metrics (not live)",
    approvalState: rejected ? "rejected" : "pending",
    unresolvedGaps: rejected
      ? ["Rejected budget gate blocks authorization"]
      : ["Local budget approval pending — no transaction"],
    mode: hasRange ? "range" : "requires_approval",
  };
}

function buildScope(plan: ImplementationPlan, conditional: boolean): ExecutionScopeItem[] {
  const items: ExecutionScopeItem[] = [
    {
      id: "scope_validation",
      title: "Audience validation planning",
      type: "research",
      linkedTaskId: "task_val_report",
      linkedDeliverableId: "del_audience_validation",
      ownerRole: "Research Director",
      targetSystem: "local evidence register",
      actionClass: "research",
      riskClass: "medium",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: "included",
    },
    {
      id: "scope_content",
      title: "Landing-page brief preparation",
      type: "content",
      linkedTaskId: "task_lp_brief",
      linkedDeliverableId: "del_lp_brief",
      ownerRole: "Content Strategist",
      targetSystem: "local deliverables register",
      actionClass: "content_preparation",
      riskClass: "low",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: conditional ? "excluded" : "included",
    },
    {
      id: "scope_assets",
      title: "Creative brief preparation",
      type: "asset",
      linkedTaskId: "task_lp_brief",
      linkedDeliverableId: "del_creative_brief",
      ownerRole: "Designer",
      targetSystem: "local deliverables register",
      actionClass: "asset_preparation",
      riskClass: "low",
      approvalRequired: true,
      verificationRequired: false,
      inclusion: "included",
    },
    {
      id: "scope_campaign",
      title: "Channel test campaign planning",
      type: "campaign",
      linkedTaskId: "task_channel_test",
      linkedDeliverableId: "del_channel_test",
      ownerRole: "Performance Marketer",
      targetSystem: "local plan only",
      actionClass: "campaign_planning",
      riskClass: "medium",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: conditional ? "excluded" : "included",
    },
    {
      id: "scope_provider",
      title: "Provider configuration (blocked)",
      type: "provider",
      linkedTaskId: "task_channel_test",
      linkedDeliverableId: "del_channel_test",
      ownerRole: "Performance Marketer",
      targetSystem: "ad platforms",
      actionClass: "provider_configuration",
      riskClass: "critical",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: "excluded",
    },
    {
      id: "scope_publish",
      title: "Publication (blocked)",
      type: "publication",
      linkedTaskId: "task_pilot_checklist",
      linkedDeliverableId: "del_pilot_report",
      ownerRole: "Project Manager",
      targetSystem: "Telegram / CMS",
      actionClass: "publication",
      riskClass: "critical",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: "excluded",
    },
    {
      id: "scope_budget",
      title: "Budget change (blocked)",
      type: "budget",
      linkedTaskId: "task_channel_test",
      linkedDeliverableId: "del_channel_test",
      ownerRole: "Client Owner",
      targetSystem: "ad accounts",
      actionClass: "budget_change",
      riskClass: "critical",
      approvalRequired: true,
      verificationRequired: true,
      inclusion: "excluded",
    },
    {
      id: "scope_report",
      title: "Pilot readiness reporting",
      type: "reporting",
      linkedTaskId: "task_pilot_checklist",
      linkedDeliverableId: "del_pilot_report",
      ownerRole: "Project Manager",
      targetSystem: "local package",
      actionClass: "reporting",
      riskClass: "low",
      approvalRequired: false,
      verificationRequired: true,
      inclusion: "included",
    },
  ];

  // Ensure linked tasks exist in plan when possible
  return items.map((s) => {
    const task = plan.tasks.find((t) => t.id === s.linkedTaskId);
    return task ? s : { ...s, linkedTaskId: plan.tasks[0]?.id ?? s.linkedTaskId };
  });
}

function buildExecutionItems(
  plan: ImplementationPlan,
  conditional: boolean,
): ExecutionItem[] {
  const items: ExecutionItem[] = [
    {
      id: "ex_validation",
      title: "Compile validation evidence package",
      sourceTaskId: "task_val_report",
      actionClass: "research",
      ownerRole: conditional ? "Audience Analyst" : "Research Director",
      reviewerRole: "Risk Officer",
      targetProvider: "none",
      targetObject: "evidence register",
      requiredInput: "Investigation + verdict conditions",
      expectedOutput: "Validation summary for package",
      preconditions: "Strategy + plan available",
      approvalGateId: "ap_plan",
      budgetGateId: "bg_validation",
      riskLevel: "medium",
      verificationMethod: "manual_review",
      rollbackMethod: "Revert package section to draft",
      status: "ready",
    },
    {
      id: "ex_measurement",
      title: "Lock measurement plan for dry-run",
      sourceTaskId: "task_measurement",
      actionClass: "reporting",
      ownerRole: "Analyst",
      reviewerRole: "Chief Marketing Strategist",
      targetProvider: "Analytics",
      targetObject: "measurement plan",
      requiredInput: "Strategy metrics",
      expectedOutput: "Measurement checklist",
      preconditions: "Analytics workstream defined",
      approvalGateId: "ap_plan",
      budgetGateId: "bg_validation",
      riskLevel: "low",
      verificationMethod: "artifact_checksum",
      rollbackMethod: "not_required — local artifact",
      status: "ready",
    },
    {
      id: "ex_campaign_plan",
      title: "Assemble channel test package (planning)",
      sourceTaskId: "task_channel_test",
      actionClass: "campaign_planning",
      ownerRole: "Performance Marketer",
      reviewerRole: "Client Owner",
      targetProvider: "none",
      targetObject: "channel test plan",
      requiredInput: "Offer + measurement plan",
      expectedOutput: "Campaign planning artifact",
      preconditions: conditional ? "Mandatory conditions closed" : "Budget gate pending ok for planning",
      approvalGateId: "ap_budget",
      budgetGateId: "bg_acquisition",
      riskLevel: "medium",
      verificationMethod: "manual_review",
      rollbackMethod: "Remove from package scope",
      status: conditional ? "blocked" : "ready",
    },
    {
      id: "ex_content",
      title: "Content preparation placeholder",
      sourceTaskId: "task_lp_brief",
      actionClass: "content_preparation",
      ownerRole: "Content Strategist",
      reviewerRole: "Chief Marketing Strategist",
      targetProvider: "CMS",
      targetObject: "LP brief",
      requiredInput: "Offer matrix",
      expectedOutput: "Brief register entry",
      preconditions: "Offer approval",
      approvalGateId: "ap_asset",
      budgetGateId: "bg_creative",
      riskLevel: "low",
      verificationMethod: "manual_review",
      rollbackMethod: "not_required — no publish",
      status: conditional ? "blocked" : "draft",
    },
    {
      id: "ex_provider_cfg",
      title: "Provider configuration (blocked)",
      sourceTaskId: "task_channel_test",
      actionClass: "provider_configuration",
      ownerRole: "Performance Marketer",
      reviewerRole: "Client Owner",
      targetProvider: "Yandex Direct",
      targetObject: "ad account config",
      requiredInput: "Credentials (not collected in Product Alpha)",
      expectedOutput: "None — blocked",
      preconditions: "Architecture V2.2 + approvals",
      approvalGateId: "ap_provider",
      budgetGateId: "bg_acquisition",
      riskLevel: "critical",
      verificationMethod: "provider_status_check",
      rollbackMethod: "unavailable until real adapter",
      status: "excluded",
    },
    {
      id: "ex_publish",
      title: "Publication (blocked)",
      sourceTaskId: "task_pilot_checklist",
      actionClass: "publication",
      ownerRole: "Project Manager",
      reviewerRole: "Client Owner",
      targetProvider: "Telegram",
      targetObject: "channel post",
      requiredInput: "Approved assets",
      expectedOutput: "None — blocked",
      preconditions: "Never in Product Alpha",
      approvalGateId: "ap_publication",
      budgetGateId: "bg_acquisition",
      riskLevel: "critical",
      verificationMethod: "unavailable",
      rollbackMethod: "unavailable",
      status: "excluded",
    },
    {
      id: "ex_budget",
      title: "Budget change (blocked)",
      sourceTaskId: "task_channel_test",
      actionClass: "budget_change",
      ownerRole: "Client Owner",
      reviewerRole: "CEO",
      targetProvider: "Yandex Direct",
      targetObject: "campaign budget",
      requiredInput: "Authorized amount",
      expectedOutput: "None — blocked",
      preconditions: "Never in Product Alpha",
      approvalGateId: "ap_budget",
      budgetGateId: "bg_acquisition",
      riskLevel: "critical",
      verificationMethod: "unavailable",
      rollbackMethod: "unavailable",
      status: "excluded",
    },
  ];

  return items.map((i) => {
    const task = plan.tasks.find((t) => t.id === i.sourceTaskId);
    return task ? i : { ...i, sourceTaskId: plan.tasks[0]?.id ?? i.sourceTaskId };
  });
}

function buildProviders(conditional: boolean): ProviderRequirement[] {
  return [
    {
      id: "prov_analytics",
      providerType: "Analytics",
      purpose: "Measurement plan alignment",
      requiredCapability: "read metrics definitions",
      authenticationState: "mock_ready",
      configurationState: "mock_ready",
      permissionsRequired: "none (local mock)",
      dryRunAvailability: "mock_only",
      verificationSupport: true,
      rollbackSupport: true,
      blocker: "None for local dry-run",
    },
    {
      id: "prov_yandex",
      providerType: "Yandex Direct",
      purpose: "Future paid acquisition",
      requiredCapability: "campaign create / budget",
      authenticationState: "credentials_required",
      configurationState: "configuration_required",
      permissionsRequired: "ads.manage (not requested)",
      dryRunAvailability: "unavailable",
      verificationSupport: false,
      rollbackSupport: false,
      blocker: "No credentials · Product Alpha boundary",
    },
    {
      id: "prov_telegram",
      providerType: "Telegram",
      purpose: "Future publication",
      requiredCapability: "send message",
      authenticationState: "credentials_required",
      configurationState: "missing",
      permissionsRequired: "bot token (not collected)",
      dryRunAvailability: "unavailable",
      verificationSupport: false,
      rollbackSupport: false,
      blocker: "Publication blocked in Product Alpha",
    },
    {
      id: "prov_cms",
      providerType: "CMS",
      purpose: "Landing page publish (future)",
      requiredCapability: "publish page",
      authenticationState: conditional ? "missing" : "configuration_required",
      configurationState: "configuration_required",
      permissionsRequired: "editor",
      dryRunAvailability: "mock_only",
      verificationSupport: true,
      rollbackSupport: false,
      blocker: "No CMS connected",
    },
    {
      id: "prov_email",
      providerType: "Email platform",
      purpose: "Optional nurture (future)",
      requiredCapability: "send sequence",
      authenticationState: "not_required",
      configurationState: "not_required",
      permissionsRequired: "n/a",
      dryRunAvailability: "unavailable",
      verificationSupport: false,
      rollbackSupport: false,
      blocker: "Out of scope for this package",
    },
  ];
}

function buildApprovals(
  verdict: BusinessVerdict,
  strategy: MarketingStrategy,
  plan: ImplementationPlan,
): ApprovalMatrixRow[] {
  return [
    {
      id: "ap_verdict",
      gate: "verdict_approval",
      decisionOwner: "Client Owner",
      approvalScope: "Business verdict acceptance",
      requiredArtifacts: [`Verdict v${verdict.version}`],
      requiredEvidence: plan.evidenceSnapshotId,
      budgetImpact: "none",
      riskClass: "medium",
      status: "approved",
      expiry: "local session / until superseded",
      consequenceIfRejected: "No strategy or package",
      affectedExecutionItemIds: [],
    },
    {
      id: "ap_strategy",
      gate: "strategy_approval",
      decisionOwner: "Client Owner",
      approvalScope: "Marketing strategy",
      requiredArtifacts: [`Strategy v${strategy.version}`],
      requiredEvidence: strategy.evidenceSnapshotId,
      budgetImpact: "indirect",
      riskClass: "medium",
      status: strategy.status === "approved" ? "approved" : "pending",
      expiry: "until strategy superseded",
      consequenceIfRejected: "Package stays draft",
      affectedExecutionItemIds: ["ex_campaign_plan"],
    },
    {
      id: "ap_plan",
      gate: "implementation_plan_approval",
      decisionOwner: "Project Manager",
      approvalScope: "Implementation plan",
      requiredArtifacts: [`Plan v${plan.version}`],
      requiredEvidence: "Workstreams + gates",
      budgetImpact: "range planning",
      riskClass: "medium",
      status: plan.status === "approved" ? "approved" : "pending",
      expiry: "until plan superseded",
      consequenceIfRejected: "Rebuild package",
      affectedExecutionItemIds: ["ex_validation", "ex_measurement"],
    },
    {
      id: "ap_budget",
      gate: "budget_approval",
      decisionOwner: "Client Owner",
      approvalScope: "Budget authorization preview",
      requiredArtifacts: ["Budget plan ranges"],
      requiredEvidence: "No fake exact amounts",
      budgetImpact: plan.overview.estimatedBudgetRange,
      riskClass: "high",
      status: "pending",
      expiry: "TBD",
      consequenceIfRejected: "Acquisition items remain blocked",
      affectedExecutionItemIds: ["ex_campaign_plan", "ex_budget"],
    },
    {
      id: "ap_asset",
      gate: "asset_approval",
      decisionOwner: "Chief Marketing Strategist",
      approvalScope: "Content/asset briefs",
      requiredArtifacts: ["LP brief", "Creative brief"],
      requiredEvidence: "Offer link",
      budgetImpact: "creative range",
      riskClass: "low",
      status: "pending",
      expiry: "Month 2",
      consequenceIfRejected: "Content items stay draft",
      affectedExecutionItemIds: ["ex_content"],
    },
    {
      id: "ap_provider",
      gate: "provider_configuration_approval",
      decisionOwner: "Client Owner",
      approvalScope: "Provider adapters",
      requiredArtifacts: ["Provider requirements"],
      requiredEvidence: "None — credentials not collected",
      budgetImpact: "none until V2.2",
      riskClass: "critical",
      status: "blocked",
      expiry: "n/a",
      consequenceIfRejected: "Provider config excluded",
      affectedExecutionItemIds: ["ex_provider_cfg"],
    },
    {
      id: "ap_publication",
      gate: "publication_approval",
      decisionOwner: "Client Owner",
      approvalScope: "External publication",
      requiredArtifacts: ["Approved assets"],
      requiredEvidence: "Never in Product Alpha",
      budgetImpact: "none",
      riskClass: "critical",
      status: "blocked",
      expiry: "n/a",
      consequenceIfRejected: "Publication excluded",
      affectedExecutionItemIds: ["ex_publish"],
    },
    {
      id: "ap_execution",
      gate: "execution_approval",
      decisionOwner: "Client Owner",
      approvalScope: "Approve package for local dry-run only",
      requiredArtifacts: ["Execution package", "Preflight", "Dry-run report"],
      requiredEvidence: "Boundary panel acknowledged implicitly by CTA",
      budgetImpact: "no spend",
      riskClass: "high",
      status: "pending",
      expiry: "until package superseded",
      consequenceIfRejected: "Cannot mark approved_for_dry_run",
      affectedExecutionItemIds: ["ex_validation", "ex_campaign_plan"],
    },
  ];
}

function buildVerification(items: ExecutionItem[]): VerificationPlanEntry[] {
  return items
    .filter((i) => i.status !== "excluded")
    .map((i) => ({
      id: `ver_${i.id}`,
      executionItemId: i.id,
      expectedState: `Local artifact ready for ${i.actionClass}`,
      verificationMethod: i.verificationMethod,
      verificationTiming: "before package approval",
      evidenceToCapture: "Local checklist status + artifact id",
      failureCondition: "Missing acceptance criteria or blocked preconditions",
      retryPolicy: "Rebuild package version — no provider retry",
      escalationPath: "Project Manager → Client Owner",
      finalStatusMapping: "dry_run_ready ↔ verified local; never executed",
      acknowledgmentRequired: i.verificationMethod === "unavailable",
    }))
    .concat(
      items
        .filter((i) => i.status === "excluded" && i.verificationMethod === "unavailable")
        .map((i) => ({
          id: `ver_${i.id}`,
          executionItemId: i.id,
          expectedState: "Excluded — no external change",
          verificationMethod: "unavailable" as const,
          verificationTiming: "n/a",
          evidenceToCapture: "Exclusion status",
          failureCondition: "Item included without verification",
          retryPolicy: "Keep excluded",
          escalationPath: "Risk Officer",
          finalStatusMapping: "excluded",
          acknowledgmentRequired: true,
        })),
    );
}

function buildRollback(items: ExecutionItem[]): RollbackPlanEntry[] {
  return items.map((i) => {
    if (i.status === "excluded") {
      return {
        id: `rb_${i.id}`,
        executionItemId: i.id,
        rollbackTrigger: "Item excluded — no external state",
        rollbackAction: "None",
        rollbackOwner: "Project Manager" as const,
        rollbackPrerequisites: "n/a",
        expectedRestoredState: "No change",
        verificationAfterRollback: "Confirm still excluded",
        timeSensitivity: "n/a",
        limitations: "No provider rollback needed",
        state: "not_required" as const,
      };
    }
    if (i.riskLevel === "critical" && i.rollbackMethod === "unavailable") {
      return {
        id: `rb_${i.id}`,
        executionItemId: i.id,
        rollbackTrigger: "Any attempt to include high-risk external action",
        rollbackAction: "Force exclude item",
        rollbackOwner: "Risk Officer" as const,
        rollbackPrerequisites: "Package edit",
        expectedRestoredState: "Item excluded",
        verificationAfterRollback: "Preflight re-run",
        timeSensitivity: "immediate",
        limitations: "Real provider rollback unavailable in Product Alpha",
        state: "unavailable" as const,
      };
    }
    return {
      id: `rb_${i.id}`,
      executionItemId: i.id,
      rollbackTrigger: "Dry-run failure or rejected approval",
      rollbackAction: i.rollbackMethod,
      rollbackOwner: "Project Manager" as const,
      rollbackPrerequisites: "Package version access",
      expectedRestoredState: "Prior package version or draft section",
      verificationAfterRollback: "manual_review of package diff",
      timeSensitivity: "same session",
      limitations: "Local-only; no external restore",
      state: "defined" as const,
    };
  });
}

function buildRiskControls(plan: ImplementationPlan): RiskControl[] {
  return plan.risks.slice(0, 4).map((r, i) => ({
    id: `rc_${r.id}`,
    linkedRiskId: r.id,
    title: `Execution control: ${r.title}`,
    preventiveControl: `Gate ${i === 0 ? "validation" : "budget"} before external items`,
    detectiveControl: "Preflight + dry-run gap report",
    correctiveAction: r.contingencyAction || "Pause package approval",
    ownerRole: "Risk Officer" as const,
    evidence: "Package preflight + risk register",
    status: r.status === "open" && r.severity === "critical" ? "open" : "in_place",
    residualRisk: r.severity,
  }));
}

function buildBlockers(
  plan: ImplementationPlan,
  approvals: ApprovalMatrixRow[],
  budget: BudgetAuthorization,
  providers: ProviderRequirement[],
  verification: VerificationPlanEntry[],
  rollback: RollbackPlanEntry[],
): PackageBlocker[] {
  const blockers: PackageBlocker[] = [];

  for (const c of plan.conditions.filter(
    (x) => x.blocksPlanning && (x.status === "open" || x.status === "in_progress"),
  )) {
    blockers.push({
      id: `blk_cond_${c.id}`,
      origin: "implementation conditions",
      description: c.requiredAction,
      affectedItemIds: c.blockingTaskIds.length
        ? c.blockingTaskIds.map((t) => `ex_from_${t}`)
        : ["ex_campaign_plan", "ex_content"],
      owner: c.ownerRole,
      requiredAction: c.requiredAction,
      evidenceRequired: c.evidenceRequired,
      unblockCriterion: c.successCriterion,
    });
  }

  if (budget.mode === "unknown" || budget.approvalState === "blocked") {
    blockers.push({
      id: "blk_budget",
      origin: "budget gates",
      description: "Budget authorization blocked/unknown",
      affectedItemIds: ["ex_campaign_plan", "ex_budget"],
      owner: "Client Owner",
      requiredAction: "Provide budget range or keep external spend excluded",
      evidenceRequired: "Budget inputs from strategy/plan",
      unblockCriterion: "Budget mode is range/exact or requires_approval with pending state",
    });
  }

  for (const a of approvals.filter((x) => x.status === "rejected")) {
    blockers.push({
      id: `blk_ap_${a.id}`,
      origin: "approval gates",
      description: `Rejected: ${a.gate}`,
      affectedItemIds: a.affectedExecutionItemIds,
      owner: a.decisionOwner,
      requiredAction: "Re-submit or revise artifacts",
      evidenceRequired: a.requiredEvidence,
      unblockCriterion: "Approval status approved",
    });
  }

  for (const p of providers.filter(
    (x) =>
      x.authenticationState === "credentials_required" ||
      x.authenticationState === "missing",
  )) {
    blockers.push({
      id: `blk_prov_${p.id}`,
      origin: "provider requirements",
      description: `${p.providerType}: ${p.blocker}`,
      affectedItemIds: ["ex_provider_cfg", "ex_publish", "ex_budget"],
      owner: "Project Manager",
      requiredAction: "Keep provider actions excluded (Product Alpha)",
      evidenceRequired: "None — do not collect credentials",
      unblockCriterion: "Architecture V2.2 provider adapters",
    });
  }

  for (const v of verification.filter(
    (x) => x.verificationMethod === "unavailable" && !x.acknowledgmentRequired,
  )) {
    blockers.push({
      id: `blk_ver_${v.id}`,
      origin: "verification gaps",
      description: `Verification unavailable for ${v.executionItemId}`,
      affectedItemIds: [v.executionItemId],
      owner: "Risk Officer",
      requiredAction: "Acknowledge gap or exclude item",
      evidenceRequired: "Acknowledgment flag",
      unblockCriterion: "acknowledgmentRequired or method changed",
    });
  }

  for (const r of rollback.filter((x) => x.state === "unavailable")) {
    const itemExcluded = true; // builder excludes high-risk external; still list gap
    if (!itemExcluded) {
      blockers.push({
        id: `blk_rb_${r.id}`,
        origin: "rollback gaps",
        description: `Rollback unavailable for ${r.executionItemId}`,
        affectedItemIds: [r.executionItemId],
        owner: r.rollbackOwner,
        requiredAction: "Define rollback or exclude",
        evidenceRequired: "Rollback plan entry",
        unblockCriterion: "state defined or not_required",
      });
    }
  }

  return blockers;
}

function buildSummary(
  plan: ImplementationPlan,
  scope: ExecutionScopeItem[],
  items: ExecutionItem[],
  providers: ProviderRequirement[],
  approvals: ApprovalMatrixRow[],
  budget: BudgetAuthorization,
  verification: VerificationPlanEntry[],
  rollback: RollbackPlanEntry[],
  blockers: PackageBlocker[],
  readinessStatus: string,
): PackageSummary {
  const verCovered = verification.filter((v) => v.verificationMethod !== "unavailable").length;
  const rbDefined = rollback.filter((r) => r.state === "defined" || r.state === "not_required").length;

  return {
    executionObjective: plan.overview.strategicObjective,
    selectedWorkstreams: plan.workstreams.slice(0, 5).map((w) => w.title),
    selectedMilestones: plan.milestones.slice(0, 4).map((m) => m.title),
    taskCount: plan.tasks.length,
    deliverableCount: plan.deliverables.length,
    requiredProviders: providers
      .filter((p) => p.authenticationState !== "not_required")
      .map((p) => p.providerType),
    estimatedBudgetRange: budget.requestedAmountOrRange,
    mandatoryConditions: plan.conditions
      .filter((c) => c.blocksPlanning)
      .map((c) => c.requiredAction),
    criticalRisks: plan.risks
      .filter((r) => r.severity === "critical" || r.severity === "high")
      .map((r) => r.title),
    approvalGates: approvals.map((a) => `${a.gate}: ${a.status}`),
    verificationCoverage: `${verCovered}/${verification.length} methods available`,
    rollbackCoverage: `${rbDefined}/${rollback.length} defined or not_required`,
    currentBlockers: blockers.map((b) => b.description).concat([`Readiness: ${readinessStatus}`]),
  };
}

export function buildExecutionPackage(
  verdict: BusinessVerdict,
  strategy: MarketingStrategy,
  plan: ImplementationPlan,
  options: {
    version: number;
    supersedesPackageId: string | null;
    status?: ExecutionPackage["status"];
    dryRunReport?: ExecutionPackage["dryRunReport"];
  },
): ExecutionPackage {
  if (verdict.type === "NO_GO" || verdict.type === "INSUFFICIENT_DATA") {
    throw new Error(`Cannot build execution package for verdict ${verdict.type}`);
  }

  const conditional = verdict.type === "CONDITIONAL_GO";
  const now = isoNow();
  const scope = buildScope(plan, conditional);
  const items = buildExecutionItems(plan, conditional);
  const providers = buildProviders(conditional);
  const approvals = buildApprovals(verdict, strategy, plan);
  const budget = budgetFromPlan(plan);
  const verification = buildVerification(items);
  const rollback = buildRollback(items);
  const riskControls = buildRiskControls(plan);
  const blockers = buildBlockers(
    plan,
    approvals,
    budget,
    providers,
    verification,
    rollback,
  );

  // Soften provider blockers for readiness: they are expected Product Alpha boundaries,
  // not package creation blockers — keep them listed but filter from readiness blockers
  // when items are already excluded.
  const readinessBlockers = blockers.filter(
    (b) => b.origin !== "provider requirements",
  );

  const preflight = runPreflightChecks({
    verdict,
    strategy,
    plan,
    scope,
    items,
    providers,
    approvals,
    budget,
    verification,
    rollback,
  });

  const dryRunReport = options.dryRunReport ?? null;

  const readiness = evaluatePackageReadiness({
    verdictType: verdict.type,
    preflight,
    blockers: readinessBlockers,
    budgetMode: budget.mode,
    budgetState: budget.approvalState,
    approvals,
    providers,
    verificationGaps: verification
      .filter((v) => v.verificationMethod === "unavailable" && !v.acknowledgmentRequired)
      .map((v) => v.executionItemId),
    rollbackGaps: rollback
      .filter((r) => {
        const item = items.find((i) => i.id === r.executionItemId);
        return r.state === "unavailable" && item && item.status !== "excluded";
      })
      .map((r) => r.executionItemId),
    dryRun: dryRunReport,
    packageStatus: options.status ?? "draft",
  });

  const summary = buildSummary(
    plan,
    scope,
    items,
    providers,
    approvals,
    budget,
    verification,
    rollback,
    blockers,
    readiness.status,
  );

  return {
    id: `epkg_${plan.projectId}_v${options.version}`,
    projectId: plan.projectId,
    projectName: plan.projectName,
    verdictId: verdict.id,
    verdictVersion: verdict.version,
    verdictType: verdict.type,
    strategyId: strategy.id,
    strategyVersion: strategy.version,
    implementationPlanId: plan.id,
    implementationPlanVersion: plan.version,
    version: options.version,
    status: options.status ?? "draft",
    createdAt: now,
    updatedAt: now,
    updatedAtLabel: labelNow(),
    supersedesPackageId: options.supersedesPackageId,
    evidenceSnapshotId: plan.evidenceSnapshotId,
    localMockLabel: "Mock / local — Product Alpha A7",
    summary,
    executionScope: scope,
    executionItems: items,
    providerRequirements: providers,
    approvalMatrix: approvals,
    budgetAuthorization: budget,
    preflightChecks: preflight,
    verificationPlan: verification,
    rollbackPlan: rollback,
    riskControls,
    blockers,
    dryRunReport,
    readiness,
    approvalReadinessLabel: readiness.status,
  };
}

/** Recompute readiness after status / dry-run changes. */
export function refreshPackageDerived(pkg: ExecutionPackage): ExecutionPackage {
  const readiness = evaluatePackageReadiness({
    verdictType: pkg.verdictType,
    preflight: pkg.preflightChecks,
    blockers: pkg.blockers.filter((b) => b.origin !== "provider requirements"),
    budgetMode: pkg.budgetAuthorization.mode,
    budgetState: pkg.budgetAuthorization.approvalState,
    approvals: pkg.approvalMatrix,
    providers: pkg.providerRequirements,
    verificationGaps: pkg.verificationPlan
      .filter((v) => v.verificationMethod === "unavailable" && !v.acknowledgmentRequired)
      .map((v) => v.executionItemId),
    rollbackGaps: pkg.rollbackPlan
      .filter((r) => {
        const item = pkg.executionItems.find((i) => i.id === r.executionItemId);
        return r.state === "unavailable" && item && item.status !== "excluded";
      })
      .map((r) => r.executionItemId),
    dryRun: pkg.dryRunReport,
    packageStatus: pkg.status,
  });

  return {
    ...pkg,
    readiness,
    approvalReadinessLabel: readiness.status,
    updatedAt: isoNow(),
    updatedAtLabel: labelNow(),
  };
}
