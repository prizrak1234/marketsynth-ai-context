export type MarketingSpecialistOutputStatus = "draft" | "approved" | "archived";

export type MarketingSpecialistType =
  | "strategist"
  | "researcher"
  | "content_planner"
  | "copywriter"
  | "critic"
  | "analyst"
  | "offer_strategist"
  | "funnel_architect"
  | "lead_magnet_specialist"
  | "sales_copywriter"
  | "email_dm_specialist"
  | "cro_specialist"
  | "smm_strategist"
  | "ad_creative_strategist";

export type CreateContentAssetFromCopywriterResponse = {
  specialist_output_id: string;
  content_asset_id: string;
  content_asset_status: string;
};

export type MarketingSpecialistOutput = {
  id: string;
  owner_id: string;
  project_id: string;
  marketing_plan_id: string;
  execution_run_id: string;
  task_index: number;
  specialist: MarketingSpecialistType;
  title: string;
  output_type: string;
  content: string;
  structured_data: Record<string, unknown> | null;
  status: MarketingSpecialistOutputStatus;
  current_version_number: number;
  approved_version_number: number | null;
  created_at: string;
  updated_at: string;
};

export type MarketingSpecialistOutputVersion = {
  id: string;
  specialist_output_id: string;
  version_number: number;
  title: string;
  output_type: string;
  content: string;
  structured_data: Record<string, unknown> | null;
  created_at: string;
  created_by_run_id: string | null;
};
