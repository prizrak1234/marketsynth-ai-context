export type ReviewQueueItem = {
  type: string;
  id: string;
  campaign_id: string | null;
  campaign_title: string | null;
  title: string;
  status: string;
  current_version_number: number;
  created_at: string;
  updated_at: string;
};

export type ReviewQueueResponse = {
  items: ReviewQueueItem[];
};
