import type { MarketingSkillRun, MarketingSkillType } from "@/lib/api/types/marketing-skills";

export type CampaignSkillSuggestion = {
  skill_type: MarketingSkillType;
  reason: string;
  priority: number;
  expected_output: string;
  related_brief_fields: string[];
  related_next_action?: string | null;
  label: string;
};

export type CampaignSkillContext = {
  segment_summary?: Record<string, unknown> | null;
  offer_summary?: Record<string, unknown> | null;
  demand_summary?: Record<string, unknown> | null;
  analytics_summary?: Record<string, unknown> | null;
  source_run_ids?: Record<string, string>;
  updated_at?: string | null;
};

export type CampaignSupervisorSeverity = "info" | "warning" | "critical";

export type CampaignSupervisorCategory =
  | "brief"
  | "strategy"
  | "offer"
  | "content"
  | "media"
  | "publishing"
  | "data"
  | "execution";

export type CampaignSupervisorFinding = {
  severity: CampaignSupervisorSeverity;
  category: CampaignSupervisorCategory;
  title: string;
  description: string;
  affected_resource_type?: string | null;
  affected_resource_id?: string | null;
  recommended_action_type?: CampaignActionType | null;
  safe_metadata: Record<string, unknown>;
};

export type CampaignSupervisorReport = {
  campaign_id: string;
  health_score: number;
  findings: CampaignSupervisorFinding[];
  missing_inputs: string[];
  contradictions: string[];
  risks: string[];
  recommended_next_actions: CampaignActionType[];
};

export type CampaignWorkflowRunStatus = "draft" | "active" | "completed" | "archived";

export type CampaignWorkflowStepStatus = "pending" | "current" | "completed";

export type CampaignWorkflowSuggestion = {
  template_id: string;
  label: string;
  reason: string;
  priority: number;
  expected_artifacts: string[];
};

export type CampaignWorkflowStepView = {
  step_index: number;
  step_id: string;
  label: string;
  safe_description: string;
  status: CampaignWorkflowStepStatus;
  recommended_action_type?: CampaignActionType | null;
  recommended_skill_type?: MarketingSkillType | null;
  recommended_tool_type?: "wordstat" | "metrica" | "image_generation" | null;
};

export type CampaignWorkflowRun = {
  id: string;
  owner_id: string;
  project_id: string;
  campaign_id: string;
  template_id: string;
  status: CampaignWorkflowRunStatus;
  current_step_index: number;
  step_results: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CampaignWorkflowRunSummary = {
  run: CampaignWorkflowRun;
  template_name: string;
  template_goal: string;
  steps: CampaignWorkflowStepView[];
  progress_percent: number;
};

export type CampaignStatus =
  | "draft"
  | "active"
  | "paused"
  | "completed"
  | "archived";

export type BusinessCampaign = {
  id: string;
  owner_id: string;
  project_id: string;
  name: string;
  goal: string;
  scenario_id?: string | null;
  status: CampaignStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CampaignMetrics = {
  plans_total: number;
  outputs_total: number;
  assets_total: number;
  media_total: number;
  packages_total: number;
  jobs_total: number;
  wizard_runs_total: number;
};

export type CampaignDashboard = {
  campaign: BusinessCampaign;
  metrics: CampaignMetrics;
  latest_plan_status?: string | null;
  latest_execution_status?: string | null;
};

export type CampaignHealthStatus =
  | "healthy"
  | "waiting_for_user"
  | "blocked"
  | "failed"
  | "completed";

export type CampaignActionType =
  | "start_wizard"
  | "advance_wizard"
  | "approve_plan"
  | "start_execution"
  | "execute_next_specialist"
  | "approve_copywriter_output"
  | "create_content_asset"
  | "submit_asset_review"
  | "approve_asset"
  | "create_media_brief"
  | "submit_media_brief_review"
  | "approve_media_brief"
  | "create_publication_package"
  | "submit_package_review"
  | "approve_package"
  | "create_publication_job"
  | "schedule_job"
  | "dry_run_dispatch"
  | "run_segment_research"
  | "run_meaning_unpacking"
  | "run_offer_packaging"
  | "run_offer_justification"
  | "run_wordstat_research"
  | "run_metrica_analysis"
  | "run_visual_report";

export type CampaignAction = {
  type: CampaignActionType;
  label: string;
  enabled: boolean;
  disabled_reason?: string | null;
  target_resource_type?: string | null;
  target_resource_id?: string | null;
  confirmation_required: boolean;
  safe_payload: Record<string, unknown>;
};

export type CampaignActionResult = {
  status: "succeeded" | "already_applied" | "failed";
  message: string;
  action_type: CampaignActionType;
  created_resource_type?: string | null;
  created_resource_id?: string | null;
  updated_resource_type?: string | null;
  updated_resource_id?: string | null;
  next_action_after: CampaignNextAction;
  control_center_snapshot?: CampaignControlCenter | null;
};

export type CampaignNextActionType =
  | "attach_scenario"
  | "start_wizard"
  | "advance_wizard"
  | "approve_plan"
  | "start_execution"
  | "execute_next_specialist"
  | "approve_copywriter_output"
  | "create_content_asset"
  | "approve_asset"
  | "create_media_brief"
  | "approve_media_brief"
  | "create_publication_package"
  | "schedule_or_dry_run"
  | "none";

export type CampaignTimelineEvent = {
  event_type: string;
  label: string;
  status?: string | null;
  resource_id: string;
  occurred_at: string;
  safe_summary?: string | null;
};

export type CampaignNextAction = {
  action_type: CampaignNextActionType;
  label: string;
  safe_description: string;
  resource_ids: Record<string, string>;
};

export type CampaignHealth = {
  status: CampaignHealthStatus;
  blocking_reason?: string | null;
  progress_percent: number;
};

export type CampaignResourceIds = {
  wizard_run_id?: string | null;
  marketing_plan_id?: string | null;
  execution_run_id?: string | null;
  copywriter_output_id?: string | null;
  content_asset_id?: string | null;
  media_brief_id?: string | null;
  media_asset_id?: string | null;
  publication_package_id?: string | null;
  publication_package_job_id?: string | null;
};

export type CampaignFailureRecoveryHint = {
  failed_object_type: string;
  failed_object_id: string;
  error_code?: string | null;
  suggested_recovery: string;
};

export type CampaignControlCenter = {
  campaign: BusinessCampaign;
  health: CampaignHealth;
  next_action: CampaignNextAction;
  timeline: CampaignTimelineEvent[];
  metrics: CampaignMetrics;
  resource_ids: CampaignResourceIds;
  safe_warnings: string[];
  recovery_hint?: CampaignFailureRecoveryHint | null;
  primary_action?: CampaignAction | null;
  available_actions?: CampaignAction[];
  tool_suggestions?: MarketingToolSuggestion[];
  skill_suggestions?: CampaignSkillSuggestion[];
  latest_skill_runs?: MarketingSkillRun[];
  skill_context?: CampaignSkillContext | null;
  supervisor_health_score?: number;
  supervisor_findings_count?: number;
  critical_findings_count?: number;
  top_findings?: CampaignSupervisorFinding[];
  workflow_suggestions?: CampaignWorkflowSuggestion[];
  active_workflow?: CampaignWorkflowRunSummary | null;
};

export type MarketingToolSuggestion = {
  tool_type: "wordstat" | "metrica" | "image_generation";
  label: string;
  safe_description: string;
  recommended: boolean;
};

export type CampaignControlCenterSummary = {
  campaign: BusinessCampaign;
  health: CampaignHealth;
  next_action_type: CampaignNextActionType;
};

export type CreateBusinessCampaignInput = {
  name: string;
  goal: string;
  scenario_id?: string | null;
  status?: CampaignStatus;
  metadata?: Record<string, unknown>;
};

export type UpdateBusinessCampaignInput = Partial<CreateBusinessCampaignInput>;
