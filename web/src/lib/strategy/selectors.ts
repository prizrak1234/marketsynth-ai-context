/**
 * Display helpers for Strategy Workspace.
 */

import type {
  ExecutionReadinessStatus,
  SegmentValidationStatus,
  StrategyStatus,
} from "@/lib/strategy/types";

export function executionStatusLabel(status: ExecutionReadinessStatus): string {
  return status.replaceAll("_", " ");
}

export function strategyStatusLabel(status: StrategyStatus): string {
  return status.replaceAll("_", " ");
}

export function segmentValidationLabel(status: SegmentValidationStatus): string {
  switch (status) {
    case "confirmed":
      return "Confirmed segment";
    case "evidence_supported_hypothesis":
      return "Evidence-supported hypothesis";
    default:
      return "Unvalidated hypothesis";
  }
}

export function executionStatusColor(status: ExecutionReadinessStatus): string {
  switch (status) {
    case "ready_for_planning":
      return "var(--ms-status-success)";
    case "conditionally_ready":
      return "var(--ms-status-warning)";
    case "blocked":
      return "var(--ms-status-danger)";
    default:
      return "var(--ms-text-muted)";
  }
}
