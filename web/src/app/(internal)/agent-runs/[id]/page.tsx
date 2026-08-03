"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { ApiKeyMissing, ProjectIdMissing } from "@/components/data/config-missing";
import { ErrorPanel } from "@/components/data/error-panel";
import { LoadingSkeleton } from "@/components/data/loading-skeleton";
import { PageHeader } from "@/components/layout/page-header";
import { fetchAgentRun } from "@/lib/api/endpoints/agent-runs";
import { queryKeys } from "@/lib/api/query-keys";
import { useEnvConfig } from "@/lib/hooks/use-env-config";

export default function AgentRunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const { hasApiKey, hasProjectId } = useEnvConfig();

  const runQuery = useQuery({
    queryKey: queryKeys.agentRun(runId),
    queryFn: () => fetchAgentRun(runId),
    enabled: hasApiKey && Boolean(runId),
  });

  if (!hasApiKey) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Agent run" />
        <ApiKeyMissing />
      </div>
    );
  }

  if (!hasProjectId) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Agent run" />
        <ProjectIdMissing />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Agent run"
        description="Read-only run summary for marketer sub-agent chain steps."
      />
      {runQuery.isLoading ? (
        <LoadingSkeleton variant="text" lines={6} />
      ) : runQuery.isError ? (
        <ErrorPanel message="Could not load agent run" />
      ) : runQuery.data ? (
        <dl className="grid max-w-xl gap-3 rounded-lg border border-border bg-muted/20 p-4 text-sm">
          <div>
            <dt className="text-xs uppercase text-muted-foreground">Run ID</dt>
            <dd className="font-mono break-all">{runQuery.data.id}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted-foreground">Status</dt>
            <dd className="font-medium">{runQuery.data.status}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted-foreground">Agent ID</dt>
            <dd className="font-mono break-all">{runQuery.data.agent_id}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted-foreground">Parent run</dt>
            <dd className="font-mono break-all">
              {runQuery.data.parent_agent_run_id ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-muted-foreground">Project</dt>
            <dd className="font-mono break-all">{runQuery.data.project_id}</dd>
          </div>
        </dl>
      ) : null}
      <p className="text-xs text-muted-foreground">
        Full input/output payloads are not shown here — use API audit tools for deep
        inspection.
      </p>
    </div>
  );
}
