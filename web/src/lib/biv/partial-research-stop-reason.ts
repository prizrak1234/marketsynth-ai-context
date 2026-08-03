/** RUNTIME-01D — customer-safe stop reason mapping for partial research. */

export const PARTIAL_RESEARCH_STOP_REASON_CODES = [
  "high_impact_insufficient_sources",
  "finding_without_evidence",
  "finding_unaccepted_evidence",
  "finding_uses_rejected_evidence",
  "citation_coverage_incomplete",
] as const;

export type PartialResearchStopReasonCode =
  (typeof PARTIAL_RESEARCH_STOP_REASON_CODES)[number];

const STOP_REASON_I18N_KEYS: Record<PartialResearchStopReasonCode, string> = {
  high_impact_insufficient_sources:
    "agency.biv.partialResearch.stopReason.highImpactInsufficientSources",
  finding_without_evidence:
    "agency.biv.partialResearch.stopReason.findingWithoutEvidence",
  finding_unaccepted_evidence:
    "agency.biv.partialResearch.stopReason.findingUnacceptedEvidence",
  finding_uses_rejected_evidence:
    "agency.biv.partialResearch.stopReason.findingUsesRejectedEvidence",
  citation_coverage_incomplete:
    "agency.biv.partialResearch.stopReason.citationCoverageIncomplete",
};

export const PARTIAL_RESEARCH_STOP_REASON_FALLBACK_KEY =
  "agency.biv.partialResearch.stopReason.fallback";

export function normalizePartialFailureCode(code: string | null | undefined): string {
  const normalized = (code ?? "").trim();
  if (!normalized) return "";
  return normalized.split(":")[0]?.trim() ?? "";
}

export function isKnownPartialStopReasonCode(
  code: string | null | undefined,
): code is PartialResearchStopReasonCode {
  const base = normalizePartialFailureCode(code);
  return (PARTIAL_RESEARCH_STOP_REASON_CODES as readonly string[]).includes(base);
}

export function partialStopReasonMessageKey(
  code: string | null | undefined,
): string {
  const base = normalizePartialFailureCode(code);
  if (isKnownPartialStopReasonCode(base)) {
    return STOP_REASON_I18N_KEYS[base];
  }
  return PARTIAL_RESEARCH_STOP_REASON_FALLBACK_KEY;
}

export function resolvePartialStopReasonText(input: {
  partialFailureCode?: string | null;
  researchStopReasonMessage?: string | null;
  partialSafeMessage?: string | null;
  translate: (key: string) => string;
}): string {
  const mapped = input.translate(
    partialStopReasonMessageKey(input.partialFailureCode),
  );
  if (mapped && !mapped.startsWith("agency.biv.")) {
    return mapped;
  }
  const customer = (input.researchStopReasonMessage ?? "").trim();
  if (customer) return customer;
  const safe = (input.partialSafeMessage ?? "").trim();
  if (safe) return safe;
  return input.translate(PARTIAL_RESEARCH_STOP_REASON_FALLBACK_KEY);
}
