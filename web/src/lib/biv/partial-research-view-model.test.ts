import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";

import { buildPartialResearchPanelViewModel } from "./partial-research-view-model";

const translate = (key: string) => {
  if (key === "agency.biv.partialResearch.stopReason.fallback") {
    return "Fallback stop reason";
  }
  if (key === "agency.biv.gap.unknown") {
    return "Unknown gap";
  }
  return key;
};

function basePartial(
  overrides: Partial<BusinessIdeaValidationOutput> = {},
): BusinessIdeaValidationOutput {
  return {
    run_id: "run-1",
    result_kind: "partial_research",
    research_terminal_state: "succeeded_insufficient",
    partial_failure_code: "finding_without_evidence",
    finding_items: [],
    evidence_items: [],
    research_gaps: [],
    remediation_questions: [],
    ...overrides,
  } as BusinessIdeaValidationOutput;
}

describe("buildPartialResearchPanelViewModel", () => {
  it("returns null for non-partial output", () => {
    assert.equal(
      buildPartialResearchPanelViewModel(
        { result_kind: "full_research" } as unknown as BusinessIdeaValidationOutput,
        translate,
      ),
      null,
    );
  });

  it("maps findings from persisted payload", () => {
    const vm = buildPartialResearchPanelViewModel(
      basePartial({
        finding_items: [
          {
            finding_id: "f1",
            category: "market",
            claim: "Demand exists",
            interpretation: "Early signal",
            business_impact: "",
            evidence_ids: ["e1"],
            confidence: 0.72,
          },
        ],
        evidence_items: [
          {
            evidence_id: "e1",
            source_url: "https://example.com/a",
            source_title: "Example",
            excerpt: "Excerpt",
            claim_supported: "Demand exists",
            accepted: true,
          },
        ],
      }),
      translate,
    );
    assert.ok(vm);
    assert.equal(vm!.findings.length, 1);
    assert.equal(vm!.findings[0]?.title, "Demand exists");
    assert.equal(vm!.findings[0]?.linkedEvidenceCount, 1);
  });

  it("does not treat rejected evidence as confirmation", () => {
    const vm = buildPartialResearchPanelViewModel(
      basePartial({
        finding_items: [
          {
            finding_id: "f1",
            category: "market",
            claim: "Maybe demand",
            interpretation: "",
            business_impact: "",
            evidence_ids: ["e-rejected"],
            confidence: 0.5,
          },
        ],
        evidence_items: [
          {
            evidence_id: "e-rejected",
            source_url: "https://example.com/b",
            source_title: "Rejected source",
            excerpt: "",
            claim_supported: "Maybe demand",
            accepted: false,
            rejection_reason: "low_quality",
          },
          {
            evidence_id: "e-accepted",
            source_url: "https://example.com/c",
            source_title: "Accepted source",
            excerpt: "",
            claim_supported: "Confirmed",
            accepted: true,
          },
        ],
      }),
      translate,
    );
    assert.ok(vm);
    assert.equal(vm!.findings[0]?.linkedEvidenceCount, 0);
    assert.equal(vm!.evidence.length, 1);
    assert.equal(vm!.evidence[0]?.title, "Accepted source");
  });

  it("shows gaps and remediation only when persisted", () => {
    const vm = buildPartialResearchPanelViewModel(
      basePartial({
        research_gap_items: [
          {
            code: "market_size",
            message_key: "x",
            customer_message: "Need market size data",
          },
        ],
        remediation_questions: [{ question: "What is your budget?", related_categories: [] }],
      }),
      translate,
    );
    assert.ok(vm);
    assert.equal(vm!.hasGapsSection, true);
    assert.equal(vm!.hasRemediationSection, true);
    assert.equal(vm!.gaps[0]?.message, "Need market size data");
  });

  it("handles minimal payload safely", () => {
    const vm = buildPartialResearchPanelViewModel(basePartial(), translate);
    assert.ok(vm);
    assert.equal(vm!.hasFindingsSection, false);
    assert.equal(vm!.hasEvidenceSection, false);
    assert.equal(vm!.hasGapsSection, false);
    assert.equal(vm!.hasRemediationSection, false);
    assert.equal(vm!.stopReasonText.length > 0, true);
  });

  it("maps next steps and established findings from partial report", () => {
    const vm = buildPartialResearchPanelViewModel(
      basePartial({
        partial_report: {
          established_findings: ["Confirmed market signal"],
          probable_signals: [],
          user_hypotheses: [],
          contradictions: [],
          interim_conclusion: "Partial interim text",
        },
        limitations: ["Limited geographic coverage"],
        next_steps: [{ id: "s1", label: "Refine segment", action: "refine_inputs" }],
      }),
      translate,
    );
    assert.ok(vm);
    assert.equal(vm!.interimConclusion, "Partial interim text");
    assert.equal(vm!.establishedFindings.length, 1);
    assert.equal(vm!.hasNextStepsSection, true);
    assert.equal(vm!.hasLimitationsSection, true);
  });

  it("blocks unsafe evidence URLs", () => {
    const vm = buildPartialResearchPanelViewModel(
      basePartial({
        evidence_items: [
          {
            evidence_id: "e1",
            source_url: "javascript:alert(1)",
            source_title: "Bad",
            excerpt: "",
            claim_supported: "",
            accepted: true,
          },
        ],
      }),
      translate,
    );
    assert.equal(vm!.evidence[0]?.url, null);
  });
});
