import type { CommercialTimelineStage } from "./commercial-timeline-types";

export function commercialTimelineStageMark(
  status: CommercialTimelineStage["status"],
): string {
  if (status === "done") return "✓";
  if (status === "running") return "…";
  return "○";
}

export function commercialTimelineStageColor(
  status: CommercialTimelineStage["status"],
): string {
  if (status === "done") return "var(--ms-status-success)";
  if (status === "running") return "var(--ms-brand-primary)";
  return "var(--ms-text-muted)";
}
