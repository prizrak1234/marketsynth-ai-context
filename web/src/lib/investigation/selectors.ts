/**
 * Stage templates and specialist helpers for investigation scenarios.
 */

import type {
  InvestigationSpecialistRow,
  InvestigationStage,
  InvestigationStageId,
  StageRunState,
} from "@/lib/investigation/types";

export const STAGE_DEFS: ReadonlyArray<{
  id: InvestigationStageId;
  label: string;
  order: number;
}> = [
  { id: "project_context", label: "Project Context", order: 1 },
  { id: "market_research", label: "Market Research", order: 2 },
  { id: "competitor_analysis", label: "Competitor Analysis", order: 3 },
  { id: "audience_analysis", label: "Audience Analysis", order: 4 },
  { id: "demand_signals", label: "Demand Signals", order: 5 },
  { id: "economics", label: "Economics", order: 6 },
  { id: "risk_assessment", label: "Risk Assessment", order: 7 },
  { id: "evidence_review", label: "Evidence Review", order: 8 },
  { id: "verdict_preparation", label: "Verdict Preparation", order: 9 },
];

export function buildStages(
  states: Partial<Record<InvestigationStageId, StageRunState>>,
  notes: Partial<Record<InvestigationStageId, string>> = {},
): InvestigationStage[] {
  return STAGE_DEFS.map((d) => ({
    ...d,
    state: states[d.id] ?? "not_started",
    note: notes[d.id],
  }));
}

export function specialistsFromStages(
  rows: Array<Omit<InvestigationSpecialistRow, "id"> & { id?: string }>,
): InvestigationSpecialistRow[] {
  return rows.map((r, i) => ({
    id: r.id ?? `spec_${i}`,
    role: r.role,
    area: r.area,
    state: r.state,
    progress: r.progress,
    detail: r.detail,
    artifactCount: r.artifactCount,
    blocker: r.blocker,
    lastActivityLabel: r.lastActivityLabel,
  }));
}
