"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import {
  ApiKeyMissing,
  ProjectIdMissing,
} from "@/components/data/config-missing";
import { ErrorPanel } from "@/components/data/error-panel";
import { LoadingSkeleton } from "@/components/data/loading-skeleton";
import { PageHeader } from "@/components/layout/page-header";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { AssistantMessageBlocks } from "@/components/agent-chat/assistant-message-blocks";
import { ChatObservabilityPanel } from "@/components/agent-chat/chat-observability-panel";
import { MarketingPlansPanel } from "@/components/agent-chat/marketing-plans-panel";
import { DirectSpecialistPanel } from "@/components/agent-chat/direct-specialist-panel";
import { GeneralDelegationPanel } from "@/components/agent-chat/general-delegation-panel";
import { SubagentChainPanel } from "@/components/agent-chat/subagent-chain-panel";
import {
  fetchAgentChatMessages,
  fetchAgentChatSessions,
  searchAgentChatMessages,
  fetchAgents,
  fetchCampaigns,
  fetchCampaignWorkflow,
  sendAgentChatMessage,
} from "@/lib/api";
import type {
  AgentChatExecutionMetadata,
  AgentChatGeneralDelegation,
  AgentChatSessionListItem,
  AgentChatSubagentChainEntry,
  ChatAssistantMessageBlock,
  ChatAssistantMessageBlockType,
  ChatAssistantMessageDomain,
  ChatSessionDomain,
  ChatSessionStatus,
  AgentChatMessageSearchHit,
} from "@/lib/api/types/agent-chat";
import { WorkflowStateBadge } from "@/components/ui/status-badge";
import { ApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type { AgentChatMessage, AgentChatSession } from "@/lib/api/types/agent-chat";
import { useEnvConfig } from "@/lib/hooks/use-env-config";
import { cn } from "@/lib/utils";

function formatSessionTime(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sessionDomainLabel(domain: ChatSessionDomain): string {
  switch (domain) {
    case "marketing":
      return "Marketing";
    case "programmer":
      return "Programmer";
    case "media":
      return "Media";
    default:
      return "General";
  }
}

function historyBlocksFromMessage(
  message: AgentChatMessage,
): ChatAssistantMessageBlock[] | null {
  if (message.role !== "assistant") {
    return null;
  }
  if (message.blocks && message.blocks.length > 0) {
    return message.blocks;
  }
  const blockTypes = message.metadata?.block_types;
  if (!Array.isArray(blockTypes) || blockTypes.length === 0) {
    return null;
  }
  const domain =
    (message.metadata?.domain as ChatAssistantMessageDomain | undefined) ?? "unknown";
  return blockTypes.map((rawType, index) => ({
    type: rawType as ChatAssistantMessageBlockType,
    domain,
    content: message.content,
    title: index === 0 ? undefined : undefined,
  }));
}

function MessageBubble({ message }: { message: AgentChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border bg-muted/50 text-foreground",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}

function ChatMessageRow({
  message,
  liveBlocks,
  projectId,
}: {
  message: AgentChatMessage;
  liveBlocks?: ChatAssistantMessageBlock[] | null;
  projectId?: string;
}) {
  if (message.role === "user") {
    return <MessageBubble message={message} />;
  }
  const blocks = liveBlocks ?? historyBlocksFromMessage(message);
  if (blocks && blocks.length > 0) {
    return (
      <AssistantMessageBlocks
        blocks={blocks}
        projectId={projectId}
        sessionId={message.session_id}
        assistantMessageId={message.id}
      />
    );
  }
  return <MessageBubble message={message} />;
}

export function AgentChatView() {
  const { hasApiKey, hasProjectId, projectId, isProjectScopeReady } = useEnvConfig();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [lastPlanDraft, setLastPlanDraft] = useState<{
    draftId: string;
    campaignId: string;
  } | null>(null);
  const [lastGeneratedAssets, setLastGeneratedAssets] = useState<{
    campaignId: string;
    draftId: string;
    createdCount: number;
    alreadyGenerated: boolean;
  } | null>(null);
  const [lastRevisedAssets, setLastRevisedAssets] = useState<
    { assetId: string; version: number }[]
  >([]);
  const [lastSubagentChain, setLastSubagentChain] = useState<
    AgentChatSubagentChainEntry[] | null
  >(null);
  const [lastGeneralDelegation, setLastGeneralDelegation] = useState<
    AgentChatGeneralDelegation | null
  >(null);
  const [lastExecutionMetadata, setLastExecutionMetadata] = useState<
    AgentChatExecutionMetadata | null
  >(null);
  const [lastAgentRunId, setLastAgentRunId] = useState<string | null>(null);
  const [liveAssistantBlocks, setLiveAssistantBlocks] = useState<
    ChatAssistantMessageBlock[] | null
  >(null);
  const [lastAssistantMessageId, setLastAssistantMessageId] = useState<
    string | null
  >(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [sessionSearchQuery, setSessionSearchQuery] = useState("");
  const [sessionDomainFilter, setSessionDomainFilter] = useState<ChatSessionDomain | "">("");
  const [sessionStatusFilter, setSessionStatusFilter] = useState<ChatSessionStatus>("active");
  const [messageSearchQuery, setMessageSearchQuery] = useState("");

  const campaignsQuery = useQuery({
    queryKey: queryKeys.campaigns(projectId ?? ""),
    queryFn: () => fetchCampaigns(projectId!),
    enabled: isProjectScopeReady,
  });

  const workflowQuery = useQuery({
    queryKey: queryKeys.campaignWorkflow(projectId ?? "", selectedCampaignId),
    queryFn: () => fetchCampaignWorkflow(projectId!, selectedCampaignId),
    enabled: isProjectScopeReady && selectedCampaignId.length > 0,
  });

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents(projectId ?? ""),
    queryFn: () => fetchAgents(projectId!),
    enabled: isProjectScopeReady,
  });

  const trimmedSessionSearch = sessionSearchQuery.trim();
  const sessionsQuery = useQuery({
    queryKey: queryKeys.agentChatSessions(projectId ?? "", {
      agentId: selectedAgentId,
      query: trimmedSessionSearch,
      domain: sessionDomainFilter || undefined,
      status: sessionStatusFilter,
    }),
    queryFn: () =>
      fetchAgentChatSessions(projectId!, {
        agent_id: selectedAgentId || undefined,
        status: sessionStatusFilter,
        query:
          trimmedSessionSearch.length >= 2 ? trimmedSessionSearch : undefined,
        domain: sessionDomainFilter || undefined,
      }),
    enabled:
      isProjectScopeReady &&
      Boolean(selectedAgentId) &&
      (trimmedSessionSearch.length === 0 || trimmedSessionSearch.length >= 2),
  });

  const trimmedMessageSearch = messageSearchQuery.trim();
  const messageSearchResults = useQuery({
    queryKey: queryKeys.agentChatMessageSearch(
      projectId ?? "",
      trimmedMessageSearch,
      selectedAgentId,
    ),
    queryFn: () =>
      searchAgentChatMessages(projectId!, {
        query: trimmedMessageSearch,
        agent_id: selectedAgentId || undefined,
        limit: 20,
      }),
    enabled:
      isProjectScopeReady &&
      Boolean(selectedAgentId) &&
      trimmedMessageSearch.length >= 2,
  });

  const messagesQuery = useQuery({
    queryKey: queryKeys.agentChatMessages(projectId ?? "", activeSessionId ?? ""),
    queryFn: () => fetchAgentChatMessages(projectId!, activeSessionId!),
    enabled: isProjectScopeReady && activeSessionId !== null,
  });

  useEffect(() => {
    if (activeSessionId !== null) {
      return;
    }
    const sessions = sessionsQuery.data;
    if (sessions && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [activeSessionId, sessionsQuery.data]);

  useEffect(() => {
    const agents = agentsQuery.data;
    if (!agents?.length || selectedAgentId) {
      return;
    }
    const general = agents.find((agent) => String(agent.type) === "general");
    const orchestrator = agents.find((agent) => String(agent.type) === "orchestrator");
    setSelectedAgentId(general?.id ?? orchestrator?.id ?? agents[0].id);
  }, [agentsQuery.data, selectedAgentId]);

  useEffect(() => {
    setActiveSessionId(null);
    setLastGeneralDelegation(null);
    setLastExecutionMetadata(null);
    setLastSubagentChain(null);
    setLiveAssistantBlocks(null);
    setLastAssistantMessageId(null);
  }, [selectedAgentId]);

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      sendAgentChatMessage(projectId!, {
        message,
        session_id: activeSessionId ?? undefined,
        campaign_id: selectedCampaignId || undefined,
        agent_id: selectedAgentId || undefined,
      }),
    onSuccess: (data) => {
      setSendError(null);
      setDraft("");
      setActiveSessionId(data.session.id);
      if (data.plan_draft?.draft_id && data.plan_draft.campaign_id) {
        setLastPlanDraft({
          draftId: data.plan_draft.draft_id,
          campaignId: data.plan_draft.campaign_id,
        });
      } else {
        setLastPlanDraft(null);
      }
      if (
        data.generated_assets?.campaign_id &&
        data.generated_assets?.draft_id
      ) {
        setLastGeneratedAssets({
          campaignId: data.generated_assets.campaign_id,
          draftId: data.generated_assets.draft_id,
          createdCount: data.generated_assets.created_count,
          alreadyGenerated: data.generated_assets.already_generated,
        });
      } else {
        setLastGeneratedAssets(null);
      }
      if (data.revised_assets && data.revised_assets.length > 0) {
        setLastRevisedAssets(
          data.revised_assets.map((item) => ({
            assetId: item.asset_id,
            version: item.version,
          })),
        );
      } else {
        setLastRevisedAssets([]);
      }
      if (data.general_delegation) {
        setLastGeneralDelegation(data.general_delegation);
      } else {
        setLastGeneralDelegation(null);
      }
      if (data.execution_metadata) {
        setLastExecutionMetadata(data.execution_metadata);
      } else {
        setLastExecutionMetadata(null);
      }
      setLastAgentRunId(data.agent_run_id);
      setLastAssistantMessageId(data.assistant_message_id);
      setLiveAssistantBlocks(data.blocks ?? null);
      if (data.subagent_chain && data.subagent_chain.length > 0) {
        setLastSubagentChain(data.subagent_chain);
      } else {
        setLastSubagentChain(null);
      }
      void queryClient.invalidateQueries({
        queryKey: queryKeys.agentChatSessions(projectId!, {
          agentId: selectedAgentId,
          query: trimmedSessionSearch,
          domain: sessionDomainFilter || undefined,
          status: sessionStatusFilter,
        }),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.agentChatMessages(projectId!, data.session.id),
      });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        setSendError(error.message);
      } else {
        setSendError("Failed to send message");
      }
    },
  });

  const handleSend = useCallback(() => {
    const trimmed = draft.trim();
    if (!trimmed || sendMutation.isPending || !projectId) {
      return;
    }
    sendMutation.mutate(trimmed);
  }, [draft, projectId, sendMutation]);

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="AI Chat" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="AI Chat" />
        <ProjectIdMissing />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col gap-4">
      <PageHeader
        title="AI Chat"
        description="Chat with General (routes to Marketer) or the orchestrator directly. Multi-step chains show each sub-agent run."
      />

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-muted/20 px-3 py-2">
        <label htmlFor="agent-chat-agent" className="text-sm font-medium">
          Agent
        </label>
        <select
          id="agent-chat-agent"
          value={selectedAgentId}
          onChange={(event) => setSelectedAgentId(event.target.value)}
          className="min-w-[12rem] rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
          disabled={agentsQuery.isLoading || sendMutation.isPending}
        >
          {agentsQuery.data?.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name} ({agent.type})
            </option>
          ))}
        </select>
        <label htmlFor="agent-chat-campaign" className="text-sm font-medium">
          Campaign context
        </label>
        <select
          id="agent-chat-campaign"
          value={selectedCampaignId}
          onChange={(event) => setSelectedCampaignId(event.target.value)}
          className="min-w-[12rem] rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
          disabled={campaignsQuery.isLoading || sendMutation.isPending}
        >
          <option value="">None (general chat)</option>
          {campaignsQuery.data?.map((campaign) => (
            <option key={campaign.id} value={campaign.id}>
              {campaign.title}
            </option>
          ))}
        </select>
        {selectedCampaignId ? (
          workflowQuery.isLoading ? (
            <span className="text-xs text-muted-foreground">Loading workflow…</span>
          ) : workflowQuery.data ? (
            <WorkflowStateBadge state={workflowQuery.data.workflow_state} />
          ) : workflowQuery.isError ? (
            <span className="text-xs text-destructive">Workflow unavailable</span>
          ) : null
        ) : null}
      </div>

      <div className="flex min-h-0 flex-1 gap-4">
        <aside className="flex w-56 shrink-0 flex-col gap-2 overflow-y-auto rounded-lg border border-border bg-muted/20 p-2">
          <p className="px-2 text-xs font-medium uppercase text-muted-foreground">Sessions</p>
          <input
            type="search"
            value={sessionSearchQuery}
            onChange={(event) => setSessionSearchQuery(event.target.value)}
            placeholder="Search sessions…"
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            aria-label="Search sessions"
          />
          <div className="flex gap-1 px-1">
            <select
              value={sessionDomainFilter}
              onChange={(event) =>
                setSessionDomainFilter(event.target.value as ChatSessionDomain | "")
              }
              className="min-w-0 flex-1 rounded-md border border-border bg-background px-1 py-1 text-[10px]"
              aria-label="Filter by domain"
            >
              <option value="">All domains</option>
              <option value="marketing">Marketing</option>
              <option value="programmer">Programmer</option>
              <option value="media">Media</option>
              <option value="unknown">General</option>
            </select>
            <select
              value={sessionStatusFilter}
              onChange={(event) =>
                setSessionStatusFilter(event.target.value as ChatSessionStatus)
              }
              className="min-w-0 flex-1 rounded-md border border-border bg-background px-1 py-1 text-[10px]"
              aria-label="Filter by status"
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div className="border-t border-border pt-2">
            <p className="px-2 text-[10px] font-medium uppercase text-muted-foreground">
              Message search
            </p>
            <input
              type="search"
              value={messageSearchQuery}
              onChange={(event) => setMessageSearchQuery(event.target.value)}
              placeholder="Search messages (2+ chars)…"
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
              aria-label="Search messages"
            />
            {trimmedMessageSearch.length >= 2 ? (
              <div className="mt-1 max-h-32 space-y-1 overflow-y-auto">
                {messageSearchResults.isLoading ? (
                  <p className="px-2 text-[10px] text-muted-foreground">Searching…</p>
                ) : messageSearchResults.isError ? (
                  <p className="px-2 text-[10px] text-destructive">Search failed</p>
                ) : (messageSearchResults.data?.length ?? 0) === 0 ? (
                  <p className="px-2 text-[10px] text-muted-foreground">No messages found</p>
                ) : (
                  messageSearchResults.data?.map((hit: AgentChatMessageSearchHit) => (
                    <button
                      key={hit.message_id}
                      type="button"
                      onClick={() => {
                        setActiveSessionId(hit.session_id);
                        setLiveAssistantBlocks(null);
                        setLastAssistantMessageId(null);
                      }}
                      className="w-full rounded-md px-2 py-1.5 text-left text-[10px] hover:bg-background/80"
                    >
                      <span className="line-clamp-1 font-medium text-foreground">
                        {hit.session_title ?? "Chat"}
                      </span>
                      <span className="line-clamp-2 text-muted-foreground">
                        {hit.content_preview}
                      </span>
                    </button>
                  ))
                )}
              </div>
            ) : null}
          </div>
          {trimmedSessionSearch.length === 1 ? (
            <p className="px-2 text-[10px] text-muted-foreground">
              Enter at least 2 characters to search sessions.
            </p>
          ) : null}
          {sessionsQuery.isLoading ? (
            <LoadingSkeleton variant="text" lines={4} />
          ) : sessionsQuery.isError ? (
            <ErrorPanel message="Could not load sessions" />
          ) : (sessionsQuery.data?.length ?? 0) === 0 ? (
            <p className="px-2 text-xs text-muted-foreground">
              {trimmedSessionSearch.length >= 2 || sessionDomainFilter
                ? "No sessions match your search."
                : "No chats yet — send a message."}
            </p>
          ) : (
            sessionsQuery.data?.map((session: AgentChatSessionListItem) => (
              <button
                key={session.id}
                type="button"
                onClick={() => setActiveSessionId(session.id)}
                className={cn(
                  "rounded-md px-2 py-2 text-left text-sm transition-colors",
                  activeSessionId === session.id
                    ? "bg-background font-medium shadow-sm"
                    : "text-muted-foreground hover:bg-background/60 hover:text-foreground",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {sessionDomainLabel(session.domain)}
                  </span>
                  <span className="text-[10px] uppercase text-muted-foreground">
                    {session.status}
                  </span>
                </div>
                <span className="line-clamp-1 font-medium text-foreground">
                  {session.title ?? "Chat"}
                </span>
                {session.last_message_preview ? (
                  <span className="line-clamp-2 text-xs text-muted-foreground">
                    {session.last_message_preview}
                  </span>
                ) : null}
                <span className="text-[10px] text-muted-foreground">
                  {formatSessionTime(session.last_message_at ?? session.updated_at)}
                  {session.message_count > 0 ? ` · ${session.message_count} msgs` : ""}
                </span>
              </button>
            ))
          )}
          {(sessionsQuery.data?.length ?? 0) > 0 ? (
            <p className="px-2 text-[10px] text-muted-foreground">
              {sessionsQuery.data?.length} session
              {(sessionsQuery.data?.length ?? 0) === 1 ? "" : "s"}
            </p>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => {
              setActiveSessionId(null);
              setLiveAssistantBlocks(null);
              setLastAssistantMessageId(null);
            }}
          >
            New chat
          </Button>
          {projectId ? (
            <>
              <MarketingPlansPanel projectId={projectId} />
              <ChatObservabilityPanel
                projectId={projectId}
                sessionId={activeSessionId}
              />
            </>
          ) : null}
        </aside>

        <div className="flex min-w-0 flex-1 flex-col rounded-lg border border-border">
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {activeSessionId === null ? (
              <p className="text-sm text-muted-foreground">
                Start a new conversation below.
              </p>
            ) : messagesQuery.isLoading ? (
              <LoadingSkeleton variant="text" lines={6} />
            ) : messagesQuery.isError ? (
              <ErrorPanel message="Could not load messages" />
            ) : (
              messagesQuery.data?.map((message, index, rows) => {
                const isLatestAssistant =
                  message.role === "assistant" &&
                  index === rows.length - 1 &&
                  message.id === lastAssistantMessageId;
                return (
                  <ChatMessageRow
                    key={message.id}
                    message={message}
                    projectId={projectId ?? undefined}
                    liveBlocks={
                      isLatestAssistant ? liveAssistantBlocks : undefined
                    }
                  />
                );
              })
            )}
            {sendMutation.isPending ? (
              <p className="text-xs text-muted-foreground">Agent is thinking…</p>
            ) : null}
          </div>

          <div className="border-t border-border p-3">
            {lastGeneralDelegation ? (
              <GeneralDelegationPanel delegation={lastGeneralDelegation} />
            ) : null}
            {lastExecutionMetadata?.entrypoint === "direct_specialist" &&
            lastAgentRunId ? (
              <DirectSpecialistPanel
                metadata={lastExecutionMetadata}
                agentRunId={lastAgentRunId}
              />
            ) : null}
            {lastSubagentChain ? (
              <SubagentChainPanel chain={lastSubagentChain} />
            ) : null}
            {lastRevisedAssets.length > 0 ? (
              <div className="mb-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
                <p className="font-medium">
                  Content revised ({lastRevisedAssets.length})
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link
                    href={`/assets/${lastRevisedAssets[0].assetId}`}
                    className={buttonVariants({ variant: "default", size: "sm" })}
                  >
                    Open Asset
                  </Link>
                  <Link
                    href="/review"
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Open Review Queue
                  </Link>
                </div>
              </div>
            ) : null}
            {lastGeneratedAssets ? (
              <div className="mb-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
                <p className="font-medium">
                  {lastGeneratedAssets.alreadyGenerated
                    ? "Draft assets already generated"
                    : `Draft assets created (${lastGeneratedAssets.createdCount})`}
                </p>
                <p className="text-xs text-muted-foreground">
                  draft_id: {lastGeneratedAssets.draftId}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link
                    href="/review"
                    className={buttonVariants({ variant: "default", size: "sm" })}
                  >
                    Open Review Queue
                  </Link>
                  <Link
                    href={`/campaigns/${lastGeneratedAssets.campaignId}#campaign-assets`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Open Campaign Assets
                  </Link>
                </div>
              </div>
            ) : null}
            {lastPlanDraft ? (
              <div className="mb-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
                <p className="font-medium">Campaign plan draft created</p>
                <p className="text-xs text-muted-foreground">
                  draft_id: {lastPlanDraft.draftId}
                </p>
                <Link
                  href={`/campaigns/${lastPlanDraft.campaignId}#create-plan-draft`}
                  className={cn(buttonVariants({ variant: "default", size: "sm" }), "mt-2")}
                >
                  Open campaign plan drafts
                </Link>
              </div>
            ) : null}
            {sendError ? (
              <p className="mb-2 text-sm text-destructive" role="alert">
                {sendError}
              </p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    handleSend();
                  }
                }}
                rows={3}
                placeholder="Message the agent…"
                disabled={sendMutation.isPending}
                className="min-h-[4.5rem] w-full flex-1 resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50"
              />
              <Button
                type="button"
                onClick={handleSend}
                disabled={sendMutation.isPending || !draft.trim()}
              >
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
