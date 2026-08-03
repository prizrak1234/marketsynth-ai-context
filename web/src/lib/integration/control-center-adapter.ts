/**
 * Campaign Control Center → Agency Runtime Monitor view model.
 * Maps only factual fields. AI.591 overlay fields are recorded as gaps.
 */

import type { CampaignControlCenter } from "@/lib/api/types/business-campaigns";
import type {
  AgencySpecialistStatusWithOrigin,
  RuntimeMonitorFindingView,
  RuntimeMonitorSummaryView,
} from "@/lib/integration/contracts";
import { unavailableLabel } from "@/lib/integration/errors";

/** Capabilities claimed by AI.591 overlay but absent from Campaign Control Center. */
export const AI591_ABSENT_CAPABILITIES: readonly string[] = [
  "workforce overlay",
  "current_stage (project-wide)",
  "current_owner_role",
  "project-wide timeline summary",
  "project-level decisions ledger",
  "specialist progress board (dedicated)",
] as const;

export function mapControlCenterToRuntimeMonitor(
  projectId: string,
  projectName: string,
  center: CampaignControlCenter,
): RuntimeMonitorSummaryView {
  const findings: RuntimeMonitorFindingView[] = (center.top_findings ?? []).map(
    (f, i) => ({
      id: `finding_${i}_${f.title}`,
      title: f.title,
      severity: f.severity,
      description: f.description,
      origin: "backend" as const,
    }),
  );

  const specialists = deriveMonitorRowsFromControlCenter(center);

  const metrics = center.metrics;
  const metricsSummary = metrics
    ? `plans ${metrics.plans_total} · outputs ${metrics.outputs_total} · assets ${metrics.assets_total} · jobs ${metrics.jobs_total}`
    : unavailableLabel();

  return {
    projectId,
    projectName,
    campaignId: center.campaign.id,
    campaignName: center.campaign.name,
    healthStatus: center.health.status,
    healthLabel: center.health.status.replace(/_/g, " "),
    progressPercent: center.health.progress_percent,
    nextActionLabel: center.next_action.label,
    nextActionDescription: center.next_action.safe_description,
    supervisorHealthScore: center.supervisor_health_score ?? null,
    findingsCount: center.supervisor_findings_count ?? null,
    criticalFindingsCount: center.critical_findings_count ?? null,
    topFindings: findings,
    metricsSummary,
    safeWarnings: center.safe_warnings ?? [],
    controlCenterHref: null,
    unavailableCapabilities: [...AI591_ABSENT_CAPABILITIES],
    specialists,
    origin: "backend",
    badgeLabel: "Campaign Control Center · live read",
  };
}

/**
 * Deterministic derived rows from CC — not a fake workforce board.
 * Uses health / next action / supervisor signals only.
 */
export function deriveMonitorRowsFromControlCenter(
  center: CampaignControlCenter,
): AgencySpecialistStatusWithOrigin[] {
  const health = center.health.status;
  const blocked = health === "blocked" || health === "failed";
  const completed = health === "completed";
  const waiting = health === "waiting_for_user";

  const rows: AgencySpecialistStatusWithOrigin[] = [
    {
      id: "cc_health",
      role: "Campaign health",
      state: completed ? "completed" : blocked ? "blocked" : waiting ? "waiting" : "running",
      progress: center.health.progress_percent,
      detail: center.health.blocking_reason
        ? `Blocking: ${center.health.blocking_reason}`
        : `Status: ${health}`,
      origin: "derived",
    },
    {
      id: "cc_next",
      role: "Recommended next action",
      state: center.next_action.action_type === "none" ? "completed" : "waiting",
      progress: center.next_action.action_type === "none" ? 100 : 0,
      detail: `${center.next_action.label} — ${center.next_action.safe_description}`,
      origin: "backend",
    },
    {
      id: "cc_supervisor",
      role: "Supervisor findings",
      state:
        (center.critical_findings_count ?? 0) > 0
          ? "blocked"
          : (center.supervisor_findings_count ?? 0) > 0
            ? "waiting"
            : "completed",
      progress: center.supervisor_health_score ?? 0,
      detail: `Score ${center.supervisor_health_score ?? "—"} · findings ${center.supervisor_findings_count ?? 0} · critical ${center.critical_findings_count ?? 0}`,
      origin: "backend",
    },
  ];

  if (center.active_workflow) {
    rows.push({
      id: "cc_workflow",
      role: "Active workflow",
      state:
        center.active_workflow.run.status === "completed"
          ? "completed"
          : center.active_workflow.run.status === "active"
            ? "running"
            : "waiting",
      progress: center.active_workflow.progress_percent,
      detail: `${center.active_workflow.template_name} — ${center.active_workflow.template_goal}`,
      origin: "backend",
    });
  }

  return rows;
}

/** Empty/unavailable monitor when CC cannot be loaded. */
export function unavailableRuntimeMonitor(
  projectId: string,
  projectName: string,
  message: string,
): RuntimeMonitorSummaryView {
  return {
    projectId,
    projectName,
    campaignId: null,
    campaignName: null,
    healthStatus: null,
    healthLabel: unavailableLabel(),
    progressPercent: null,
    nextActionLabel: unavailableLabel(),
    nextActionDescription: message,
    supervisorHealthScore: null,
    findingsCount: null,
    criticalFindingsCount: null,
    topFindings: [],
    metricsSummary: unavailableLabel(),
    safeWarnings: [],
    controlCenterHref: null,
    unavailableCapabilities: [...AI591_ABSENT_CAPABILITIES],
    specialists: [],
    origin: "derived",
    badgeLabel: "Capability not integrated / data unavailable",
  };
}
