export type MarketingPlanStatus = "draft" | "approved" | "archived";

export type MarketingSpecialistTask = {
  specialist: string;
  objective: string;
  expected_output: string;
};

export type MarketingPlan = {
  id: string;
  owner_id: string;
  project_id: string;
  source_run_id?: string | null;
  source_session_id?: string | null;
  source_scenario_id?: string | null;
  source_scenario_name?: string | null;
  title: string;
  goal: string;
  project_context?: Record<string, unknown>;
  specialist_tasks: MarketingSpecialistTask[];
  execution_mode: string;
  status: MarketingPlanStatus;
  current_version_number: number;
  approved_version_number?: number | null;
  created_at: string;
  updated_at: string;
};

export type MarketingPlanVersion = {
  id: string;
  marketing_plan_id: string;
  version_number: number;
  goal: string;
  project_context?: Record<string, unknown>;
  specialist_tasks: MarketingSpecialistTask[];
  execution_mode: string;
  created_at: string;
  created_by_run_id?: string | null;
};
