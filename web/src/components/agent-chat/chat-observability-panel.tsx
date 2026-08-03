"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorPanel } from "@/components/data/error-panel";
import { LoadingSkeleton } from "@/components/data/loading-skeleton";
import { fetchAgentChatAuditEvents, fetchAgentChatMetrics } from "@/lib/api/endpoints/agent-chat";
import { queryKeys } from "@/lib/api/query-keys";
import { formatDateTime, formatNumber } from "@/lib/format";

type ChatObservabilityPanelProps = {
  projectId: string;
  sessionId?: string | null;
};

export function ChatObservabilityPanel({ projectId, sessionId }: ChatObservabilityPanelProps) {
  const metricsQuery = useQuery({
    queryKey: queryKeys.agentChatMetrics(projectId),
    queryFn: () => fetchAgentChatMetrics(projectId),
  });

  const auditQuery = useQuery({
    queryKey: queryKeys.agentChatAuditEvents(projectId, sessionId ?? undefined),
    queryFn: () =>
      fetchAgentChatAuditEvents(projectId, {
        session_id: sessionId ?? undefined,
        limit: 30,
      }),
  });

  return (
    <div className="mt-3 space-y-3 border-t border-border pt-3">
      <p className="px-1 text-[10px] font-medium uppercase text-muted-foreground">
        Chat observability
      </p>

      {metricsQuery.isLoading ? (
        <LoadingSkeleton variant="text" lines={3} />
      ) : metricsQuery.isError ? (
        <ErrorPanel message="Could not load chat metrics" />
      ) : metricsQuery.data ? (
        <div className="grid grid-cols-2 gap-1.5 px-1 text-[10px]">
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Sessions</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.sessions_total)}</p>
          </div>
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Messages</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.messages_total)}</p>
          </div>
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Runs OK</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.runs_succeeded)}</p>
          </div>
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Runs failed</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.runs_failed)}</p>
          </div>
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Block actions</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.block_actions_total)}</p>
          </div>
          <div className="rounded border border-border bg-background/60 px-2 py-1">
            <span className="text-muted-foreground">Searches</span>
            <p className="font-medium">{formatNumber(metricsQuery.data.searches_total)}</p>
          </div>
        </div>
      ) : null}

      {auditQuery.isLoading ? (
        <LoadingSkeleton variant="text" lines={4} />
      ) : auditQuery.isError ? (
        <ErrorPanel message="Could not load audit events" />
      ) : (auditQuery.data?.length ?? 0) === 0 ? (
        <p className="px-1 text-[10px] text-muted-foreground">No audit events yet.</p>
      ) : (
        <ul className="max-h-40 space-y-1 overflow-y-auto px-1">
          {auditQuery.data?.map((event) => (
            <li
              key={event.id}
              className="rounded border border-border bg-background/40 px-2 py-1 text-[10px]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-foreground">{event.event_type}</span>
                <span className="text-muted-foreground">{event.status}</span>
              </div>
              <p className="text-muted-foreground">{formatDateTime(event.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
