"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { AgentChatGeneralDelegation } from "@/lib/api/types/agent-chat";

type GeneralDelegationPanelProps = {
  delegation: AgentChatGeneralDelegation;
};

function shortRunId(agentRunId: string): string {
  return agentRunId.length > 8 ? `${agentRunId.slice(0, 8)}…` : agentRunId;
}

function delegationLabel(domain: string): string {
  switch (domain) {
    case "marketing":
      return "Marketer";
    case "programmer":
      return "Programmer";
    case "media":
      return "Media";
    default:
      return domain.charAt(0).toUpperCase() + domain.slice(1);
  }
}

export function GeneralDelegationPanel({ delegation }: GeneralDelegationPanelProps) {
  const label = delegationLabel(delegation.domain);

  return (
    <div className="mb-3 rounded-lg border border-dashed border-border bg-muted/20 px-3 py-2 text-sm">
      <p className="font-medium">Delegated to {label}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Domain: {delegation.domain} · run {shortRunId(delegation.agent_run_id)}
      </p>
      <Link
        href={`/agent-runs/${delegation.agent_run_id}`}
        className={buttonVariants({ variant: "outline", size: "sm", className: "mt-2" })}
      >
        Specialist run
      </Link>
    </div>
  );
}
