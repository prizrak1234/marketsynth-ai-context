export type MediaBrief = {
  id: string;
  owner_id: string;
  project_id: string;
  content_asset_id: string;
  source_content_asset_id: string;
  status: string;
  title: string;
  goal: string;
  target_audience: string;
  platform: string;
  creative_direction: string;
  visual_style: string;
  composition: string;
  text_overlay: string;
  references?: unknown[];
  submitted_for_review_at?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateMediaBriefFromAssetResponse = {
  content_asset_id: string;
  media_brief_id: string;
  media_brief_status: string;
};

export type CreateMediaAssetFromBriefResponse = {
  media_brief_id: string;
  media_asset_id: string;
  media_asset_status: string;
  media_type: string;
};
