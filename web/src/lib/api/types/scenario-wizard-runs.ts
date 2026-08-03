export type ScenarioWizardRunStatus =
  | "draft"
  | "running"
  | "paused"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ScenarioWizardRun = {
  id: string;
  owner_id: string;
  project_id: string;
  scenario_id: string;
  scenario_name: string;
  source_campaign_id?: string | null;
  status: ScenarioWizardRunStatus;
  current_step: string;
  step_results: Record<string, unknown>;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
  finished_at?: string | null;
};

export const SCENARIO_WIZARD_STEPS = [
  "create_plan",
  "approve_plan",
  "create_execution_run",
  "execute_specialists",
  "approve_copywriter_output",
  "create_content_asset",
  "submit_asset",
  "approve_asset",
  "create_media_brief",
  "submit_media_brief",
  "approve_media_brief",
  "create_publication_package",
  "submit_package",
  "approve_package",
  "create_dry_run_job",
] as const;

export function wizardStepLabel(step: string) {
  return step.replace(/_/g, " ");
}
