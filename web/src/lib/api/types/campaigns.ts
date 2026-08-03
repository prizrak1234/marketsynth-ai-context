export type EditableCampaignStatus = "draft" | "active" | "paused" | "completed";

export type MarketingCampaignCreateBody = {
  title: string;
  description?: string | null;
  status?: EditableCampaignStatus;
  start_at?: string | null;
  end_at?: string | null;
};

export type MarketingCampaignUpdateBody = {
  title?: string;
  description?: string | null;
  status?: EditableCampaignStatus;
  start_at?: string | null;
  end_at?: string | null;
};

export type MarketingCampaign = {
  id: string;
  project_id: string;
  brief_id: string | null;
  title: string;
  description: string | null;
  status: string;
  start_at: string | null;
  end_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CampaignWorkflowCounts = {
  plan_drafts: number;
  assets_total: number;
  assets_approved: number;
  assets_draft: number;
  pending_review_assets: number;
};

export type CampaignWorkflowResponse = {
  campaign_id: string;
  workflow_state: string;
  counts: CampaignWorkflowCounts;
  next_recommended_action: string;
};

export type CampaignAssetListItem = {
  id: string;
  owner_id: string;
  project_id: string;
  brief_id: string | null;
  campaign_id: string | null;
  type: string;
  title: string;
  status: string;
  current_version_number: number;
  approved_version_number: number | null;
  created_at: string;
  updated_at: string;
};

export type CampaignOverviewCounts = {
  assets_total: number;
  assets_draft: number;
  assets_approved: number;
  assets_archived: number;
  jobs_total: number;
  jobs_scheduled: number;
  jobs_queued: number;
  jobs_running: number;
  jobs_succeeded: number;
  jobs_failed: number;
  jobs_cancelled: number;
  jobs_skipped: number;
};

export type CampaignOverviewSchedule = {
  next_scheduled_publication_at: string | null;
  last_successful_publication_at: string | null;
};

export type CampaignOverviewResponse = {
  campaign: Record<string, unknown>;
  counts: CampaignOverviewCounts;
  schedule: CampaignOverviewSchedule;
  recent_jobs: unknown[];
};

export type PublicationCalendarEntry = {
  job_id: string;
  asset_id: string;
  asset_title: string;
  channel_id: string;
  channel_type: string;
  channel_name: string;
  status: string;
  scheduled_at: string | null;
  queued_at: string | null;
  asset_version_number: number;
  campaign_id: string | null;
  campaign_title: string | null;
};
