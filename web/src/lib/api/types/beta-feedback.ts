export type BetaFeedbackSource =
  | "onboarding"
  | "chat"
  | "marketing_pipeline"
  | "content"
  | "media"
  | "publishing"
  | "other";

export type BetaFeedbackSeverity = "low" | "medium" | "high" | "blocker";

export type BetaFeedbackStatus = "open" | "triaged" | "resolved" | "archived";

export type BetaFeedbackReport = {
  id: string;
  owner_id: string;
  project_id: string | null;
  source: BetaFeedbackSource;
  severity: BetaFeedbackSeverity;
  status: BetaFeedbackStatus;
  title: string;
  description: string;
  safe_context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type BetaFeedbackCreateBody = {
  title: string;
  description: string;
  project_id?: string | null;
  source?: BetaFeedbackSource;
  severity?: BetaFeedbackSeverity;
  safe_context?: Record<string, unknown>;
};

export type BetaQaExport = {
  generated_at: string;
  projects: Array<{
    project_id: string;
    project_name: string;
    publication_job_status: string | null;
    failed_step: string | null;
    last_error_code: string | null;
  }>;
  demo_completion: {
    demo_projects_total: number;
    publication_queued_count: number;
    with_failed_step_count: number;
  };
  feedback_counts: {
    open: number;
    triaged: number;
    resolved: number;
    archived: number;
    blocker: number;
    high: number;
  };
  failed_jobs: {
    failed_package_jobs: number;
    failed_generation_jobs: number;
    failed_legacy_publication_jobs: number;
    window_hours: number;
  };
};
