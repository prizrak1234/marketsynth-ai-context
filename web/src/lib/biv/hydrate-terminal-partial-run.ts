import type { BusinessIdeaValidationRunResponse } from "@/lib/api/types/business-idea-validation";
import { isPartialResearchOutput } from "@/lib/api/types/business-idea-validation";

export type HydrateTerminalPartialRun = (
  userRequestId: string,
  runId?: string | null,
) => Promise<BusinessIdeaValidationRunResponse>;

export async function tryHydrateTerminalPartialRun(input: {
  projectId: string;
  userRequestId: string;
  runId?: string | null;
  fetchLatest: HydrateTerminalPartialRun;
}): Promise<BusinessIdeaValidationRunResponse | null> {
  const latest = await input.fetchLatest(input.userRequestId, input.runId);
  if (
    latest.status === "failed" &&
    isPartialResearchOutput(latest.output) &&
    (latest.project_id ?? input.projectId) === input.projectId
  ) {
    return latest;
  }
  return null;
}
