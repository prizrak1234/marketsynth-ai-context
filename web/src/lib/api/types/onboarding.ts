export type OnboardingStep =
  | "project_created"
  | "agents_seeded"
  | "demo_seeded"
  | "first_chat_done"
  | "first_asset_created"
  | "first_publication_job_created";

export type OnboardingStepStatus = {
  step: OnboardingStep;
  completed: boolean;
  derived: boolean;
  manual_allowed: boolean;
};

export type OnboardingStatus = {
  project_id: string | null;
  steps: OnboardingStepStatus[];
  completed_count: number;
  total_count: number;
};
