import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import {
  isPartialResearchOutput,
  isResearchTerminal,
} from "@/lib/api/types/business-idea-validation";

export type ResearchUiState =
  | "legacy_report"
  | "ready_to_rerun"
  | "rerun_starting"
  | "research_running"
  | "report_building"
  | "completed"
  | "partial_research"
  | "failed";

export function deriveResearchUiState(args: {
  loading: boolean;
  rerunStarting: boolean;
  validationResult: BusinessIdeaValidationOutput | null;
  runStatus?: string | null;
  error?: string | null;
}): ResearchUiState {
  const { loading, rerunStarting, validationResult, runStatus, error } = args;

  if (error && !loading && !validationResult?.customer_report) {
    return "failed";
  }
  if (rerunStarting) {
    return "rerun_starting";
  }
  if (loading || runStatus === "running") {
    return "research_running";
  }
  if (validationResult && isPartialResearchOutput(validationResult)) {
    return "partial_research";
  }
  if (validationResult && isResearchTerminal(validationResult) && !validationResult.customer_report) {
    return "legacy_report";
  }
  if (validationResult?.customer_report) {
    return "completed";
  }
  if (validationResult && isResearchTerminal(validationResult)) {
    return "ready_to_rerun";
  }
  return "ready_to_rerun";
}
