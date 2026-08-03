import { apiJson } from "@/lib/api/client";
import type { DemoFlowStatus } from "@/lib/api/types/demo-flow";

export function fetchDemoFlowStatus(projectId: string): Promise<DemoFlowStatus> {
  return apiJson<DemoFlowStatus>(`/projects/${projectId}/demo-flow/status`);
}
