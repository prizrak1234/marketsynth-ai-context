/** PRODUCT-01.3B.1 — customer-safe research gap presentation (frontend). */

import type {
  BivResearchGapPresentation,
  BusinessIdeaValidationOutput,
} from "@/lib/api/types/business-idea-validation";

const INTERNAL_CODE = /^[a-z][a-z0-9_]{2,127}$/;

export function isInternalGapCode(value: string): boolean {
  const normalized = (value || "").trim();
  if (!normalized) return false;
  return INTERNAL_CODE.test(normalized);
}

export function semanticGapGroups(
  output: BusinessIdeaValidationOutput,
): NonNullable<BusinessIdeaValidationOutput["semantic_gap_groups"]> {
  if (output.semantic_gap_groups?.length) {
    return output.semantic_gap_groups;
  }
  return [];
}

/** Never show raw backend codes in customer UI — prefer structured gap items. */
export function customerGapItems(
  output: BusinessIdeaValidationOutput,
): BivResearchGapPresentation[] {
  const groups = output.semantic_gap_groups ?? [];
  if (groups.length) {
    return groups.map((group) => ({
      code: group.group_id,
      message_key: "agency.biv.gap.semanticGroup",
      customer_message: group.summary,
      recommended_action: group.questions[0]?.question,
      semantic_group: group.group_id,
    }));
  }
  if (output.research_gap_items?.length) {
    return output.research_gap_items;
  }
  return (output.research_gaps ?? [])
    .filter((code) => isInternalGapCode(code))
    .map((code) => ({
      code,
      message_key: "agency.biv.gap.unknown",
      customer_message: "Недостаточно данных для надёжного вывода по этому блоку.",
    }));
}

export function isInsufficientEvidence(
  output: BusinessIdeaValidationOutput | null | undefined,
): boolean {
  if (!output) return false;
  if (output.research_terminal_state === "succeeded_insufficient") return true;
  if (output.verdict === "insufficient_evidence") return true;
  if (!output.business_verdict_id) return true;
  return false;
}

export function hasValidVerdictForLaunchPack(
  output: BusinessIdeaValidationOutput | null | undefined,
): boolean {
  if (!output) return false;
  if (isInsufficientEvidence(output)) return false;
  return (
    Boolean(output.business_verdict_id) &&
    output.research_terminal_state === "succeeded_complete"
  );
}

export function intakeFieldsFromGaps(
  items: BivResearchGapPresentation[],
): string[] {
  const seen = new Set<string>();
  const fields: string[] = [];
  for (const item of items) {
    const field = item.intake_field?.trim();
    if (!field || seen.has(field)) continue;
    seen.add(field);
    fields.push(field);
  }
  return fields;
}

export function uniqueRecommendedActions(
  items: BivResearchGapPresentation[],
): string[] {
  const seen = new Set<string>();
  const actions: string[] = [];
  for (const item of items) {
    const action = item.recommended_action?.trim();
    if (!action || seen.has(action)) continue;
    seen.add(action);
    actions.push(action);
  }
  return actions;
}
