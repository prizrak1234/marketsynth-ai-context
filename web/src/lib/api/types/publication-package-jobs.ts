export type PublicationPackageJob = {
  id: string;
  owner_id: string;
  project_id: string;
  publication_package_id: string;
  channel_id: string;
  status: string;
  payload_snapshot?: Record<string, unknown>;
  result_metadata?: Record<string, unknown>;
  error?: Record<string, unknown> | null;
  scheduled_for?: string | null;
  schedule_status: string;
  dispatch_attempts?: number;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type SchedulePublicationPackageJobPayload = {
  scheduled_for: string;
};
