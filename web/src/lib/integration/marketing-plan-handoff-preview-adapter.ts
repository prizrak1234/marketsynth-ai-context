/**
 * P1.2 — map backend handoff preview to workspace view.
 */

import type { BackendMarketingPlanHandoffPreviewDto } from "@/lib/api/types/marketing-plan-handoff";

export type MarketingPlanHandoffPreviewView = {
  handoffId: string;
  planId: string;
  planVersion: number;
  mappingVersion: string;
  mappingFingerprint: string;
  proposedTitle: string;
  proposedGoal: string;
  included: BackendMarketingPlanHandoffPreviewDto["included_tasks"];
  transformed: BackendMarketingPlanHandoffPreviewDto["transformed_tasks"];
  excluded: BackendMarketingPlanHandoffPreviewDto["excluded_tasks"];
  unsupported: BackendMarketingPlanHandoffPreviewDto["unsupported_tasks"];
  blocked: BackendMarketingPlanHandoffPreviewDto["blocked_tasks"];
  roleNotes: string[];
  dependencyWarnings: string[];
  acceptanceWarnings: string[];
  gateBlockers: string[];
  existingPlans: BackendMarketingPlanHandoffPreviewDto["existing_marketing_plans"];
  duplicateHandoffId: string | null;
  eligible: boolean;
  blockers: string[];
  warnings: string[];
  sideEffects: string[];
  createsDraft: false;
  createsApproval: false;
  createsAgentRun: false;
  createsCampaign: false;
  dispatchesTasks: false;
  ctaCheckLabel: string;
  ctaConfirmLabel: string;
  notice: string;
};

export function mapMarketingPlanHandoffPreview(
  dto: BackendMarketingPlanHandoffPreviewDto,
): MarketingPlanHandoffPreviewView {
  return {
    handoffId: dto.handoff_id,
    planId: dto.implementation_plan_id,
    planVersion: dto.implementation_plan_version,
    mappingVersion: dto.mapping_version,
    mappingFingerprint: dto.mapping_fingerprint,
    proposedTitle: dto.proposed_title,
    proposedGoal: dto.proposed_goal,
    included: dto.included_tasks,
    transformed: dto.transformed_tasks,
    excluded: dto.excluded_tasks,
    unsupported: dto.unsupported_tasks,
    blocked: dto.blocked_tasks,
    roleNotes: dto.role_mapping_notes,
    dependencyWarnings: dto.dependency_warnings,
    acceptanceWarnings: dto.acceptance_criteria_warnings,
    gateBlockers: dto.gate_blockers,
    existingPlans: dto.existing_marketing_plans,
    duplicateHandoffId: dto.duplicate_handoff_id,
    eligible: dto.eligible,
    blockers: dto.blockers,
    warnings: dto.warnings,
    sideEffects: dto.side_effects,
    createsDraft: false,
    createsApproval: false,
    createsAgentRun: false,
    createsCampaign: false,
    dispatchesTasks: false,
    ctaCheckLabel: "Проверить готовность к передаче",
    ctaConfirmLabel: "Создать черновик MarketingPlan",
    notice:
      "Подтверждение создаёт только черновик MarketingPlan. Approve / dispatch / Agent Run / Campaign не выполняются.",
  };
}
