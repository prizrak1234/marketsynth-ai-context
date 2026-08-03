import { apiJson } from "@/lib/api/client";
import type {
  AgentChatMessage,
  AgentChatMessageSearchHit,
  AgentChatMetricsResponse,
  ChatAuditEventRead,
  AgentChatSendRequest,
  AgentChatSendResponse,
  AgentChatSession,
  AgentChatSessionListItem,
  ChatBlockActionRequest,
  ChatBlockActionResponse,
  ChatSessionDomain,
  ChatSessionEntrypoint,
  ChatSessionStatus,
  AgentChatMessageRole,
} from "@/lib/api/types/agent-chat";

export type AgentChatSessionListParams = {
  query?: string;
  agent_id?: string;
  status?: ChatSessionStatus;
  domain?: ChatSessionDomain;
  entrypoint?: ChatSessionEntrypoint;
  limit?: number;
};

export type AgentChatMessageSearchParams = {
  query: string;
  session_id?: string;
  agent_id?: string;
  domain?: ChatSessionDomain;
  role?: AgentChatMessageRole;
  limit?: number;
};

export function fetchAgentChatSessions(
  projectId: string,
  params?: AgentChatSessionListParams,
): Promise<AgentChatSessionListItem[]> {
  const search = new URLSearchParams();
  if (params?.query) {
    search.set("query", params.query);
  }
  if (params?.agent_id) {
    search.set("agent_id", params.agent_id);
  }
  if (params?.status) {
    search.set("status", params.status);
  }
  if (params?.domain) {
    search.set("domain", params.domain);
  }
  if (params?.entrypoint) {
    search.set("entrypoint", params.entrypoint);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<AgentChatSessionListItem[]>(
    `/projects/${projectId}/agent-chat/sessions${suffix}`,
  );
}

export function fetchAgentChatMetrics(
  projectId: string,
  params?: { date_from?: string; date_to?: string },
): Promise<AgentChatMetricsResponse> {
  const search = new URLSearchParams();
  if (params?.date_from) {
    search.set("date_from", params.date_from);
  }
  if (params?.date_to) {
    search.set("date_to", params.date_to);
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<AgentChatMetricsResponse>(
    `/projects/${projectId}/agent-chat/metrics${suffix}`,
  );
}

export type AgentChatAuditEventsParams = {
  session_id?: string;
  event_type?: string;
  domain?: string;
  limit?: number;
};

export function fetchAgentChatAuditEvents(
  projectId: string,
  params?: AgentChatAuditEventsParams,
): Promise<ChatAuditEventRead[]> {
  const search = new URLSearchParams();
  if (params?.session_id) {
    search.set("session_id", params.session_id);
  }
  if (params?.event_type) {
    search.set("event_type", params.event_type);
  }
  if (params?.domain) {
    search.set("domain", params.domain);
  }
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<ChatAuditEventRead[]>(
    `/projects/${projectId}/agent-chat/audit-events${suffix}`,
  );
}

export function searchAgentChatMessages(
  projectId: string,
  params: AgentChatMessageSearchParams,
): Promise<AgentChatMessageSearchHit[]> {
  const search = new URLSearchParams();
  search.set("query", params.query);
  if (params.session_id) {
    search.set("session_id", params.session_id);
  }
  if (params.agent_id) {
    search.set("agent_id", params.agent_id);
  }
  if (params.domain) {
    search.set("domain", params.domain);
  }
  if (params.role) {
    search.set("role", params.role);
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  return apiJson<AgentChatMessageSearchHit[]>(
    `/projects/${projectId}/agent-chat/search-messages?${search.toString()}`,
  );
}

export function archiveAgentChatSession(
  projectId: string,
  sessionId: string,
): Promise<AgentChatSession> {
  return apiJson<AgentChatSession>(
    `/projects/${projectId}/agent-chat/sessions/${sessionId}/archive`,
    { method: "POST" },
  );
}

export function fetchAgentChatMessages(
  projectId: string,
  sessionId: string,
  params?: { limit?: number },
): Promise<AgentChatMessage[]> {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return apiJson<AgentChatMessage[]>(
    `/projects/${projectId}/agent-chat/sessions/${sessionId}/messages${suffix}`,
  );
}

export function executeChatBlockAction(
  projectId: string,
  body: ChatBlockActionRequest,
): Promise<ChatBlockActionResponse> {
  return apiJson<ChatBlockActionResponse>(
    `/projects/${projectId}/agent-chat/block-actions`,
    { method: "POST", body },
  );
}

export function sendAgentChatMessage(
  projectId: string,
  body: AgentChatSendRequest,
): Promise<AgentChatSendResponse> {
  const payload: AgentChatSendRequest = {
    message: body.message ?? body.content ?? "",
    session_id: body.session_id,
    agent_id: body.agent_id,
    campaign_id: body.campaign_id,
  };
  return apiJson<AgentChatSendResponse>(`/projects/${projectId}/agent-chat`, {
    method: "POST",
    body: payload,
  });
}
