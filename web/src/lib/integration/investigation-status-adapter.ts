/**
 * I3 — InvestigationViewStatus is a frontend display projection only.
 * Do not invent backend Investigation status enums.
 */

import type { CampaignHealthStatus } from "@/lib/api/types/business-campaigns";
import type { DataOrigin } from "@/lib/integration/contracts";
import type { InvestigationStatus } from "@/lib/investigation/types";

/** UI-only view status — may differ from Product Alpha InvestigationStatus labels. */
export type InvestigationViewStatus =
  | "not_started"
  | "context_available"
  | "campaign_linked"
  | "quality_signals_available"
  | "research_artifacts_available"
  | "blocked"
  | "unsupported_backend_lifecycle"
  | "mock_only";

export type InvestigationViewStatusResult = {
  viewStatus: InvestigationViewStatus;
  /** Legacy Product Alpha status string for shell compatibility — display-only mapping */
  legacyStatusLabel: InvestigationStatus | "partial_integration";
  origin: DataOrigin;
  rationale: string;
};

/**
 * Map known backend campaign health → display status.
 * Never claims Investigation lifecycle persistence.
 */
export function mapCampaignHealthToViewStatus(
  health: CampaignHealthStatus | null | undefined,
): InvestigationViewStatusResult {
  if (!health) {
    return {
      viewStatus: "context_available",
      legacyStatusLabel: "partial_integration",
      origin: "derived",
      rationale: "Project loaded; no Campaign Control Center health yet.",
    };
  }
  if (health === "blocked" || health === "failed") {
    return {
      viewStatus: "blocked",
      legacyStatusLabel: "blocked_by_missing_data",
      origin: "derived",
      rationale: `Campaign health=${health} — campaign ops block, not Investigation lifecycle.`,
    };
  }
  if (health === "completed") {
    return {
      viewStatus: "campaign_linked",
      legacyStatusLabel: "partial_integration",
      origin: "derived",
      rationale: "Campaign completed ≠ Investigation completed.",
    };
  }
  return {
    viewStatus: "campaign_linked",
    legacyStatusLabel: "collecting_context",
    origin: "derived",
    rationale: `Campaign health=${health} projected as investigation display only.`,
  };
}

export function mockOnlyViewStatus(): InvestigationViewStatusResult {
  return {
    viewStatus: "mock_only",
    legacyStatusLabel: "queued",
    origin: "mock",
    rationale: "Integration mode=mock — Product Alpha local scenario.",
  };
}

export function unsupportedLifecycleStatus(): InvestigationViewStatusResult {
  return {
    viewStatus: "unsupported_backend_lifecycle",
    legacyStatusLabel: "partial_integration",
    origin: "derived",
    rationale:
      "No durable Investigation status entity on backend. Display is projected.",
  };
}
