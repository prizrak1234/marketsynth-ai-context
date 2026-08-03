export type AgentChatMessageRole = "user" | "assistant" | "system";

export type ChatSessionEntrypoint = "general_delegation" | "direct_specialist";
export type ChatSessionDomain = "unknown" | "marketing" | "programmer" | "media";
export type ChatSessionStatus = "active" | "archived";

export type AgentChatSession = {
  id: string;
  owner_id: string;
  project_id: string;
  agent_id: string | null;
  entrypoint: ChatSessionEntrypoint;
  domain: ChatSessionDomain;
  title: string | null;
  status: ChatSessionStatus;
  created_at: string;
  updated_at: string;
};

export type AgentChatSessionListItem = AgentChatSession & {
  last_message_preview: string | null;
  last_message_at: string | null;
  message_count: number;
  unread_count: number;
};

export type AgentChatMessage = {
  id: string;
  session_id: string;
  role: AgentChatMessageRole;
  content: string;
  metadata: Record<string, unknown>;
  agent_run_id: string | null;
  created_at: string;
  blocks?: ChatAssistantMessageBlock[];
};

export type AgentChatWorkflowContext = {
  campaign_id: string;
  workflow_state: string;
  next_recommended_action: string;
  pending_review_assets: number;
};

export type AgentChatSendRequest = {
  message: string;
  session_id?: string;
  agent_id?: string;
  campaign_id?: string;
  /** @deprecated use message */
  content?: string;
};

export type AgentChatPlanDraftCreated = {
  draft_id: string;
  campaign_id: string;
  title?: string | null;
};

export type AgentChatGeneratedAssets = {
  campaign_id: string;
  draft_id: string;
  created_count: number;
  already_generated: boolean;
  asset_ids: string[];
};

export type AgentChatRevisedAsset = {
  asset_id: string;
  version: number;
};

export type AgentChatSubagentExecution = {
  subagent: string;
  agent_run_id: string;
};

export type AgentChatSubagentChainEntry = {
  subagent: string;
  agent_run_id: string;
  status?: string | null;
};

export type AgentChatGeneralDelegation = {
  domain: string;
  agent_run_id: string;
};

export type AgentChatExecutionMetadata = {
  entrypoint: "direct_specialist" | "general_delegation";
  domain: string;
};

export type ChatAssistantMessageBlockType =
  | "text"
  | "clarification"
  | "draft"
  | "brief"
  | "marketing_plan"
  | "error";

export type ChatAssistantMessageDomain =
  | "general"
  | "marketing"
  | "programmer"
  | "media"
  | "unknown";

export type ChatBlockActionType =
  | "create_marketing_asset"
  | "create_marketing_brief"
  | "create_revision_from_approved"
  | "save_marketing_plan"
  | "copy_text"
  | "export_markdown";

export type ChatBlockAction = {
  type: ChatBlockActionType;
  label: string;
  enabled: boolean;
  reason?: string | null;
  payload?: Record<string, unknown>;
};

export type ChatAssistantMessageBlock = {
  type: ChatAssistantMessageBlockType;
  domain: ChatAssistantMessageDomain;
  content: string;
  title?: string | null;
  data?: Record<string, unknown> | null;
  persisted?: boolean | null;
  created_at?: string | null;
  actions?: ChatBlockAction[];
};

export type ChatBlockActionRequest = {
  session_id: string;
  assistant_message_id: string;
  block_index: number;
  action_type: ChatBlockActionType;
  payload?: Record<string, unknown>;
};

export type ChatBlockActionResponse = {
  status: string;
  message: string;
  created_resource_type?: string | null;
  created_resource_id?: string | null;
  text?: string | null;
  markdown?: string | null;
};

export type AgentChatMessageSearchHit = {
  message_id: string;
  session_id: string;
  session_title?: string | null;
  role: AgentChatMessageRole;
  content_preview: string;
  created_at: string;
  domain: ChatSessionDomain;
  entrypoint: ChatSessionEntrypoint;
};

export type AgentChatMetricsResponse = {
  sessions_total: number;
  sessions_active: number;
  sessions_archived: number;
  messages_total: number;
  messages_user: number;
  messages_assistant: number;
  runs_total: number;
  runs_succeeded: number;
  runs_failed: number;
  block_actions_total: number;
  block_actions_by_type: Record<string, number>;
  searches_total: number;
  searches_by_type: Record<string, number>;
  sessions_by_domain: Record<string, number>;
  messages_by_domain: Record<string, number>;
  latest_activity_at: string | null;
};

export type ChatAuditEventRead = {
  id: string;
  owner_id: string;
  project_id: string;
  session_id: string | null;
  message_id: string | null;
  agent_id: string | null;
  event_type: string;
  domain: ChatSessionDomain;
  entrypoint: ChatSessionEntrypoint;
  status: string;
  safe_metadata: Record<string, unknown>;
  created_at: string;
};

export type AgentChatSendResponse = {
  session: AgentChatSession;
  session_id: string;
  user_message: AgentChatMessage;
  assistant_message: AgentChatMessage;
  assistant_message_id: string;
  agent_run_id: string;
  plan_draft?: AgentChatPlanDraftCreated | null;
  generated_assets?: AgentChatGeneratedAssets | null;
  revised_assets?: AgentChatRevisedAsset[] | null;
  subagent_execution?: AgentChatSubagentExecution | null;
  subagent_chain?: AgentChatSubagentChainEntry[] | null;
  general_delegation?: AgentChatGeneralDelegation | null;
  execution_metadata?: AgentChatExecutionMetadata | null;
  output?: Record<string, unknown>;
  blocks?: ChatAssistantMessageBlock[];
};
