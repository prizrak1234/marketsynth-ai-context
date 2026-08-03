export type ContentAsset = {
  id: string;
  project_id: string;
  brief_id: string | null;
  campaign_id: string | null;
  type: string;
  title: string;
  status: string;
  current_version_number: number;
  approved_version_number: number | null;
  body?: string;
  metadata?: Record<string, unknown>;
  submitted_for_review_at?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ContentAssetVersion = {
  version_number: number;
  title: string;
  body?: string;
  metadata?: Record<string, unknown>;
  created_by_source: string;
  created_at: string;
};
