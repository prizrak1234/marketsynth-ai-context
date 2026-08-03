/**
 * Display helpers for Execution Package Workspace.
 */

import type {
  DryRunResult,
  LocalGateStatus,
  PackageReadinessStatus,
  PackageStatus,
  PreflightResult,
} from "@/lib/execution-package/types";

export function packageStatusLabel(status: PackageStatus): string {
  return status.replace(/_/g, " ");
}

export function packageReadinessLabel(status: PackageReadinessStatus): string {
  return status.replace(/_/g, " ");
}

export function packageReadinessColor(status: PackageReadinessStatus): string {
  switch (status) {
    case "approved_for_dry_run":
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

export function dryRunResultLabel(result: DryRunResult): string {
  return result.replace(/_/g, " ");
}

export function preflightResultLabel(result: PreflightResult): string {
  return result.replace(/_/g, " ");
}

export function gateStatusLabel(status: LocalGateStatus): string {
  return status.replace(/_/g, " ");
}
