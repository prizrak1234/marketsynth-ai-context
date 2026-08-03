import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  isKnownPartialStopReasonCode,
  normalizePartialFailureCode,
  partialStopReasonMessageKey,
  resolvePartialStopReasonText,
} from "./partial-research-stop-reason";

const translate = (key: string) => {
  const map: Record<string, string> = {
    "agency.biv.partialResearch.stopReason.highImpactInsufficientSources":
      "Для ключевых выводов найдено недостаточно независимых источников.",
    "agency.biv.partialResearch.stopReason.fallback":
      "Исследование остановлено из-за недостаточности подтверждающих данных.",
  };
  return map[key] ?? key;
};

describe("partial-research-stop-reason", () => {
  it("maps whitelist codes to customer-safe i18n keys", () => {
    assert.equal(
      partialStopReasonMessageKey("high_impact_insufficient_sources"),
      "agency.biv.partialResearch.stopReason.highImpactInsufficientSources",
    );
    assert.equal(
      partialStopReasonMessageKey("finding_without_evidence:detail"),
      "agency.biv.partialResearch.stopReason.findingWithoutEvidence",
    );
  });

  it("uses fallback key for unknown codes", () => {
    assert.equal(
      partialStopReasonMessageKey("pipeline_fetch_failed"),
      "agency.biv.partialResearch.stopReason.fallback",
    );
    assert.equal(isKnownPartialStopReasonCode("pipeline_fetch_failed"), false);
  });

  it("normalizes suffixed failure codes", () => {
    assert.equal(
      normalizePartialFailureCode("citation_coverage_incomplete:foo"),
      "citation_coverage_incomplete",
    );
  });

  it("prefers mapped translation over raw backend message", () => {
    assert.equal(
      resolvePartialStopReasonText({
        partialFailureCode: "high_impact_insufficient_sources",
        researchStopReasonMessage: "internal raw",
        partialSafeMessage: "safe",
        translate,
      }),
      "Для ключевых выводов найдено недостаточно независимых источников.",
    );
  });

  it("falls back to neutral copy for unknown whitelist-compatible reason", () => {
    assert.equal(
      resolvePartialStopReasonText({
        partialFailureCode: "unknown_internal_code",
        translate,
      }),
      "Исследование остановлено из-за недостаточности подтверждающих данных.",
    );
  });
});
