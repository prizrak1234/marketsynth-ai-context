import { apiJson } from "@/lib/api/client";
import type { AgentRun } from "@/lib/api/types/agent-runs";

export function fetchAgentRun(runId: string): Promise<AgentRun> {
  return apiJson<AgentRun>(`/agent-runs/${runId}`);
}
