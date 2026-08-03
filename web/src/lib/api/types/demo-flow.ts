export type DemoFlowStatus = {
  marketing_plan_status: string | null;
  execution_run_status: string | null;
  completed_specialists: string[];
  content_asset_status: string | null;
  media_brief_status: string | null;
  media_asset_status: string | null;
  publication_package_status: string | null;
  publication_job_status: string | null;
  publication_schedule_status: string | null;
  next_available_action: string | null;
  resource_links: Record<string, string>;
  failed_step?: string | null;
  blocking_reason?: string | null;
  last_error_code?: string | null;
  suggested_next_action?: string | null;
};
