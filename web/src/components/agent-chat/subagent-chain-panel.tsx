"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { AgentChatSubagentChainEntry } from "@/lib/api/types/agent-chat";
import { cn } from "@/lib/utils";

function formatSubagentLabel(subagent: string): string {
  return subagent.charAt(0).toUpperCase() + subagent.slice(1);
}

function shortRunId(agentRunId: string): string {
  return agentRunId.length > 8 ? `${agentRunId.slice(0, 8)}…` : agentRunId;
}

function statusClass(status: string | null | undefined): string {
  switch (status) {
    case "succeeded":
      return "text-emerald-700 dark:text-emerald-400";
    case "failed":
      return "text-destructive";
    case "running":
    case "queued":
      return "text-amber-700 dark:text-amber-400";
    default:
      return "text-muted-foreground";
  }
}

type SubagentChainPanelProps = {
  chain: AgentChatSubagentChainEntry[];
};

export function SubagentChainPanel({ chain }: SubagentChainPanelProps) {
  if (chain.length === 0) {
    return null;
  }

  const summary = chain.map((entry) => formatSubagentLabel(entry.subagent)).join(" → ");

  return (
    <div className="mb-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
      <p className="font-medium">Handled by</p>
      <p className="mt-1 text-xs text-muted-foreground">{summary}</p>
      <ol className="mt-3 space-y-2 border-t border-border pt-2">
        {chain.map((entry, index) => (
          <li
            key={entry.agent_run_id}
            className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs"
          >
            <span className="font-medium text-foreground">
              {index + 1}. {formatSubagentLabel(entry.subagent)}
            </span>
            {entry.status ? (
              <span className={cn("font-mono uppercase", statusClass(entry.status))}>
                {entry.status}
              </span>
            ) : null}
            <span
              className="font-mono text-muted-foreground"
              title={entry.agent_run_id}
            >
              run {shortRunId(entry.agent_run_id)}
            </span>
            <Link
              href={`/agent-runs/${entry.agent_run_id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Run details
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
