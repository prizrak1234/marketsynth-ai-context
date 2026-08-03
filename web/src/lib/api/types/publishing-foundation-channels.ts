export type PublishingFoundationChannel = {
  id: string;
  owner_id: string;
  project_id: string;
  name: string;
  channel_type: string;
  status: string;
  config_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CreatePublishingFoundationChannelPayload = {
  name: string;
  channel_type: string;
  config_metadata?: Record<string, unknown>;
  status?: string;
};

export type UpdatePublishingFoundationChannelPayload = {
  name?: string;
  status?: string;
  config_metadata?: Record<string, unknown>;
};
