/** Backend MarketingPlan handoff DTOs (Commercial MVP P1.2). */

export type BackendHandoffTaskMappingItem = {
  implementation_task_id: string;
  title: string;
  classification: "exact" | "transformable" | "excluded" | "unsupported" | "blocked";
  reason: string;
  mapped_specialist: string | null;
  mapped_objective: string | null;
  mapped_expected_output: string | null;
  acceptance_criteria_mode: string;
  dependency_mode: string;
  responsible_role: string;
};

export type BackendMarketingPlanHandoffPreviewDto = {
  handoff_id: string;
  implementation_plan_id: string;
  implementation_plan_version: number;
  mapping_version: string;
  mapping_fingerprint: string;
  project_id: string;
  proposed_title: string;
  proposed_goal: string;
  included_tasks: BackendHandoffTaskMappingItem[];
  transformed_tasks: BackendHandoffTaskMappingItem[];
  excluded_tasks: BackendHandoffTaskMappingItem[];
  unsupported_tasks: BackendHandoffTaskMappingItem[];
  blocked_tasks: BackendHandoffTaskMappingItem[];
  role_mapping_notes: string[];
  dependency_warnings: string[];
  acceptance_criteria_warnings: string[];
  gate_blockers: string[];
  existing_marketing_plans: Array<{
    id: string;
    title: string;
    status: string;
    version: number;
  }>;
  duplicate_handoff_id: string | null;
  eligible: boolean;
  blockers: string[];
  warnings: string[];
  side_effects: string[];
  creates_marketing_plan_draft: boolean;
  creates_marketing_plan_approval: boolean;
  creates_agent_run: boolean;
  creates_campaign: boolean;
  dispatches_specialist_tasks: boolean;
};

export type BackendMarketingPlanHandoffConfirmDto = {
  handoff_id: string;
  lifecycle_status: string;
  marketing_plan_id: string;
  marketing_plan_version: number;
  marketing_plan_status: string;
  mapping_fingerprint: string;
  included_task_count: number;
  excluded_task_count: number;
  blocked_task_count: number;
  warnings: string[];
  idempotent_replay: boolean;
  creates_marketing_plan_approval: boolean;
  creates_agent_run: boolean;
  creates_campaign: boolean;
  dispatches_specialist_tasks: boolean;
  side_effects: string[];
};
