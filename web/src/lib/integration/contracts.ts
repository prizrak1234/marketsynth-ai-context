/**
 * Frontend view models for Integration I1 — separate from backend API schemas.
 */

import type { AgencySpecialistStatus, WorkspaceProject } from "@/lib/workspace/types";
import type { IntegrationMode } from "@/lib/integration/mode";

/** Provenance of a displayed Runtime Monitor / specialist row. */
export type DataOrigin = "backend" | "derived" | "mock";

export type LoadState =
  | "idle"
  | "loading"
  | "success"
  | "empty"
  | "error"
  | "unauthorized"
  | "unavailable"
  | "unsupported";

export type WorkspaceProjectViewModel = WorkspaceProject & {
  /** ISO timestamp from backend when known */
  updatedAtIso: string | null;
  /** Campaign count when known from API; null = unavailable */
  activeCampaignCount: number | null;
  /** Next recommended step label when known; "Недоступно" when absent */
  nextRecommendedStep: string;
  /** Deep link to campaign Control Center when a campaign id is known */
  controlCenterHref: string | null;
  origin: DataOrigin;
  /** Latest BIV run lifecycle label when known from /latest-run */
  bivLifecycleLabel?: string | null;
  /** Set when latest-run hydration failed with server error (not "no run"). */
  bivHydrationError?: boolean;
};

export type RuntimeMonitorFindingView = {
  id: string;
  title: string;
  severity: string;
  description: string;
  origin: DataOrigin;
};

export type RuntimeMonitorSummaryView = {
  projectId: string;
  projectName: string;
  campaignId: string | null;
  campaignName: string | null;
  healthStatus: string | null;
  healthLabel: string;
  progressPercent: number | null;
  nextActionLabel: string;
  nextActionDescription: string;
  supervisorHealthScore: number | null;
  findingsCount: number | null;
  criticalFindingsCount: number | null;
  topFindings: RuntimeMonitorFindingView[];
  metricsSummary: string;
  safeWarnings: string[];
  controlCenterHref: string | null;
  /** Honest gaps — AI.591 overlay and similar */
  unavailableCapabilities: string[];
  specialists: AgencySpecialistStatusWithOrigin[];
  origin: DataOrigin;
  badgeLabel: string;
};

export type AgencySpecialistStatusWithOrigin = AgencySpecialistStatus & {
  origin: DataOrigin;
};

export type WorkspaceProjectsLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  projects: WorkspaceProjectViewModel[];
  message: string | null;
  errorStatus: number | null;
};

export type RuntimeMonitorLoadResult = {
  state: LoadState;
  mode: IntegrationMode;
  summary: RuntimeMonitorSummaryView | null;
  message: string | null;
  errorStatus: number | null;
};

/** Product Alpha domain classification for mapping docs / contracts. */
export type DomainMappingClass =
  | "A_direct"
  | "A_backend_sot"
  | "B_partial_adapter"
  | "C_multiple"
  | "D_additive_entity"
  | "E_frontend_view";
