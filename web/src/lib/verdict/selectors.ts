/**
 * Display helpers for Business Verdict UI.
 */

import type { BusinessVerdictType, ScorecardRating, VerdictStatus } from "@/lib/verdict/types";

export function verdictTokenVar(type: BusinessVerdictType): string {
  switch (type) {
    case "GO":
      return "var(--ms-verdict-go)";
    case "CONDITIONAL_GO":
      return "var(--ms-verdict-conditional-go)";
    case "NO_GO":
      return "var(--ms-verdict-no-go)";
    default:
      return "var(--ms-verdict-insufficient-data)";
  }
}

export function verdictGlyph(type: BusinessVerdictType): string {
  switch (type) {
    case "GO":
      return "▣";
    case "CONDITIONAL_GO":
      return "◈";
    case "NO_GO":
      return "▢";
    default:
      return "◌";
  }
}

export function verdictPlainLabel(type: BusinessVerdictType): string {
  switch (type) {
    case "GO":
      return "GO — proceed to strategy planning within constraints";
    case "CONDITIONAL_GO":
      return "CONDITIONAL GO — proceed only if conditions are met";
    case "NO_GO":
      return "NO GO — do not proceed with the current concept";
    default:
      return "INSUFFICIENT DATA — responsible decision not possible yet";
  }
}

export function ratingLabel(rating: ScorecardRating): string {
  return rating.replaceAll("_", " ");
}

export function statusLabel(status: VerdictStatus): string {
  return status.replaceAll("_", " ");
}
