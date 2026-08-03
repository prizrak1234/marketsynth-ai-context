/**
 * I3 — Skill runs are research ARTIFACTS, not InvestigationSource records.
 * LLM responses / tool payloads are never promoted to Source.
 */

import type { MarketingSkillRun, MarketingSkillType } from "@/lib/api/types/marketing-skills";
import type { DataOrigin } from "@/lib/integration/contracts";

/** Explicit allow-list — unrelated skill runs excluded. */
export const INVESTIGATION_RELATED_SKILL_TYPES: readonly MarketingSkillType[] = [
  "segment_research",
  "wordstat_research",
  "metrica_analysis",
  "meaning_unpacking",
] as const;

export type ResearchArtifactView = {
  id: string;
  skillType: MarketingSkillType;
  status: string;
  title: string;
  campaignId: string | null;
  createdAt: string;
  finishedAt: string | null;
  /** Never "evidence" — candidacy for later InvestigationSource mapping */
  role: "research_artifact_candidate";
  origin: DataOrigin;
  disclaimer: string;
};

export function isInvestigationRelatedSkillRun(run: MarketingSkillRun): boolean {
  return (INVESTIGATION_RELATED_SKILL_TYPES as readonly string[]).includes(
    run.skill_type,
  );
}

/**
 * Map skill runs → research artifact candidates.
 * Does NOT create InvestigationSource or EvidenceItem.
 */
export function mapSkillRunsToResearchArtifacts(
  runs: MarketingSkillRun[],
): ResearchArtifactView[] {
  return runs.filter(isInvestigationRelatedSkillRun).map((run) => ({
    id: run.id,
    skillType: run.skill_type,
    status: run.status,
    title: `Skill run: ${run.skill_type}`,
    campaignId: run.campaign_id ?? null,
    createdAt: run.created_at,
    finishedAt: run.finished_at ?? null,
    role: "research_artifact_candidate" as const,
    origin: "backend" as const,
    disclaimer:
      "MarketingSkillRun — not InvestigationSource. Не подтверждённое evidence.",
  }));
}

export function mapSkillTypeToStageHint(
  skillType: MarketingSkillType,
): "audience_analysis" | "demand_signals" | "market_research" | null {
  switch (skillType) {
    case "segment_research":
    case "meaning_unpacking":
      return "audience_analysis";
    case "wordstat_research":
      return "demand_signals";
    case "metrica_analysis":
      return "market_research";
    default:
      return null;
  }
}
