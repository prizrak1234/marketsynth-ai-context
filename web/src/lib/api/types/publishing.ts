export type PublishingChannel = {
  id: string;
  owner_id: string;
  project_id: string;
  name: string;
  type: string;
  status: string;
  config_preview: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PublicationJob = {
  id: string;
  owner_id: string;
  project_id: string;
  asset_id: string;
  asset_version_number: number;
  channel_id: string;
  campaign_id: string | null;
  status: string;
  attempts: number;
  payload_preview: Record<string, unknown>;
  error: string | null;
  created_at: string;
  scheduled_at: string | null;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type PublicationJobCreateBody = {
  asset_id: string;
  channel_id: string;
  campaign_id?: string;
  scheduled_at: string;
};

export type PublicationJobRescheduleBody = {
  scheduled_at: string;
};

export type PublishingChannelCreateBody = {
  name: string;
  type: "telegram";
  config: {
    chat_id: string;
    parse_mode?: "HTML" | "MarkdownV2";
    disable_web_page_preview?: boolean;
  };
};

export type PublishingChannelUpdateBody = {
  name?: string;
  status?: "active" | "paused" | "archived";
  config?: PublishingChannelCreateBody["config"];
};
