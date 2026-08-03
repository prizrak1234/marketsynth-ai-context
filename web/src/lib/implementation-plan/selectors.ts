/**
 * Display helpers for Implementation Plan Workspace.
 */

import type {
  GateStatus,
  PlanningReadinessStatus,
  PlanStatus,
  TaskStatus,
  WorkstreamStatus,
} from "@/lib/implementation-plan/types";

export function planStatusLabel(status: PlanStatus): string {
  switch (status) {
    case "draft":
      return "Draft";
    case "under_review":
      return "Under review";
    case "approved":
      return "Approved";
    case "blocked":
      return "Blocked";
    case "superseded":
      return "Superseded";
    default:
      return status;
  }
}

export function planningReadinessLabel(status: PlanningReadinessStatus): string {
  switch (status) {
    case "not_ready":
      return "Not ready";
    case "conditionally_ready":
      return "Conditionally ready";
    case "ready_for_approval":
      return "Ready for approval";
    case "blocked":
      return "Blocked";
    default:
      return status;
  }
}

export function planningReadinessColor(status: PlanningReadinessStatus): string {
  switch (status) {
    case "ready_for_approval":
      return "var(--ms-verdict-go)";
    case "conditionally_ready":
      return "var(--ms-verdict-conditional-go)";
    case "not_ready":
      return "var(--ms-text-muted)";
    case "blocked":
      return "var(--ms-verdict-no-go)";
    default:
      return "var(--ms-text-secondary)";
  }
}

export function workstreamStatusLabel(status: WorkstreamStatus): string {
  return status.replace(/_/g, " ");
}

export function taskStatusLabel(status: TaskStatus): string {
  return status.replace(/_/g, " ");
}

export function gateStatusLabel(status: GateStatus): string {
  return status.replace(/_/g, " ");
}
