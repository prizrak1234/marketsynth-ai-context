export type MarketingPlanExecutionStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type MarketingPlanExecutionTaskStatus =
  | "pending"
  | "skipped"
  | "placeholder_completed"
  | "specialist_completed";

export type ExecuteMarketingSpecialistTaskResponse = {
  execution_run_id: string;
  task_index: number;
  specialist: string;
  specialist_output_id: string;
  status: "draft" | "approved" | "archived";
  safe_summary: string;
  execution_run_status: MarketingPlanExecutionStatus;
  run_completed: boolean;
};

export type MarketingPlanExecutionTaskSnapshot = {
  specialist: string;
  objective: string;
  expected_output: string;
  status: MarketingPlanExecutionTaskStatus;
  output_ref?: string | null;
  safe_notes?: string | null;
};

export type MarketingPlanExecutionRun = {
  id: string;
  owner_id: string;
  project_id: string;
  marketing_plan_id: string;
  marketing_plan_version_number: number;
  status: MarketingPlanExecutionStatus;
  task_snapshots: MarketingPlanExecutionTaskSnapshot[];
  result_summary?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};
