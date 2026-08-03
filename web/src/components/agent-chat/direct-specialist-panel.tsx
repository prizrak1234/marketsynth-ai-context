"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { AgentChatExecutionMetadata } from "@/lib/api/types/agent-chat";

type DirectSpecialistPanelProps = {
  metadata: AgentChatExecutionMetadata;
  agentRunId: string;
};

function shortRunId(agentRunId: string): string {
  return agentRunId.length > 8 ? `${agentRunId.slice(0, 8)}…` : agentRunId;
}

function directChatLabel(domain: string): string {
  switch (domain) {
    case "marketing":
      return "Marketing";
    case "programmer":
      return "Programmer";
    case "media":
      return "Media";
    default:
      return domain.charAt(0).toUpperCase() + domain.slice(1);
  }
}

export function DirectSpecialistPanel({
  metadata,
  agentRunId,
}: DirectSpecialistPanelProps) {
  if (metadata.entrypoint !== "direct_specialist") {
    return null;
  }

  const label = directChatLabel(metadata.domain);

  return (
    <div className="mb-3 rounded-lg border border-dashed border-border bg-muted/20 px-3 py-2 text-sm">
      <p className="font-medium">Direct chat with {label}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Domain: {metadata.domain} · run {shortRunId(agentRunId)}
      </p>
      <Link
        href={`/agent-runs/${agentRunId}`}
        className={buttonVariants({ variant: "outline", size: "sm", className: "mt-2" })}
      >
        Specialist run
      </Link>
    </div>
  );
}
