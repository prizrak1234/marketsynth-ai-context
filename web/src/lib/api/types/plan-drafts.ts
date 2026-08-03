export type CampaignPlanDraft = {
  id: string;
  owner_id: string;
  project_id: string;
  campaign_id: string;
  source_agent_run_id: string | null;
  title: string;
  plan_payload: PlanPayload;
  status: "draft" | "archived";
  created_at: string;
  updated_at: string;
};

export type PlanContentItem = {
  title: string;
  channel: string;
  format: string;
  scheduled_at?: string | null;
  notes?: string | null;
};

export type PlanPayload = {
  goal?: string;
  target_audience?: string;
  key_message?: string;
  content_items?: PlanContentItem[];
};

export type CampaignPlanDraftCreateBody = {
  title: string;
  plan_payload: PlanPayload;
};

export type PlanDraftGenerateAssetsResponse = {
  created_count: number;
  asset_ids: string[];
  already_generated: boolean;
};
