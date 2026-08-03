/**
 * Evidence register filters / selectors.
 */

import type {
  ConfidenceLevel,
  EvidenceItem,
  EvidenceState,
  InvestigationArea,
  InvestigationSource,
  SourceType,
} from "@/lib/investigation/types";

export type EvidenceFilters = {
  state: EvidenceState | "all";
  area: InvestigationArea | "all";
  confidence: ConfidenceLevel | "all";
  sourceType: SourceType | "all";
};

export const DEFAULT_EVIDENCE_FILTERS: EvidenceFilters = {
  state: "all",
  area: "all",
  confidence: "all",
  sourceType: "all",
};

export function filterEvidence(
  items: EvidenceItem[],
  sources: InvestigationSource[],
  filters: EvidenceFilters,
): EvidenceItem[] {
  const sourceTypeById = new Map(sources.map((s) => [s.id, s.sourceType]));

  return items.filter((item) => {
    if (filters.state !== "all" && item.state !== filters.state) return false;
    if (filters.area !== "all" && item.area !== filters.area) return false;
    if (filters.confidence !== "all" && item.confidence !== filters.confidence) {
      return false;
    }
    if (filters.sourceType !== "all") {
      const related = [...item.supportingSourceIds, ...item.contradictingSourceIds];
      const match = related.some(
        (id) => sourceTypeById.get(id) === filters.sourceType,
      );
      if (!match) return false;
    }
    return true;
  });
}

export function sourceTitleMap(
  sources: InvestigationSource[],
): Map<string, string> {
  return new Map(sources.map((s) => [s.id, s.title]));
}
