import { apiJson } from "@/lib/api/client";
import type { Agent } from "@/lib/api/types/agents";

export function fetchAgents(projectId: string): Promise<Agent[]> {
  return apiJson<Agent[]>(`/agents?project_id=${encodeURIComponent(projectId)}`);
}
