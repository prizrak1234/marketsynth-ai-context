/**
 * P0.4 Evidence domain selfcheck.
 * Run: npx --yes tsx src/lib/integration/evidence-p0-4.selfcheck.ts
 */

import {
  createsBusinessVerdictFromEvidence,
  createsFindingFromEvidence,
  mapBackendEvidenceToView,
} from "@/lib/integration/evidence-api-adapter";
import { mapEvidenceSummary } from "@/lib/integration/evidence-summary-adapter";
import { normalizeEvidenceError } from "@/lib/integration/evidence-errors";
import type { EvidenceDto, EvidenceSummaryDto } from "@/lib/api/types/evidence";
import { ApiError } from "@/lib/api/errors";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

{
  assert(createsBusinessVerdictFromEvidence() === false, "no verdict");
  assert(createsFindingFromEvidence() === false, "no finding");
}

{
  const dto: EvidenceDto = {
    id: "e1",
    owner_id: "o",
    project_id: "p",
    investigation_id: "i",
    claim: "Средняя цена 8000–12000.",
    evidence_type: "comparison",
    investigation_area: "competitor_analysis",
    lifecycle_status: "draft",
    assessment_state: "unverified",
    confidence_level: "unknown",
    materiality: "critical",
    review_note: null,
    why_it_matters: null,
    version: 1,
    input_fingerprint: "f",
    supersedes_evidence_id: null,
    source_links: [
      {
        id: "l1",
        source_id: "s1",
        stance: "supports",
        locator_type: "page",
        locator_value: "1",
        excerpt: null,
        note: null,
      },
    ],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const view = mapBackendEvidenceToView(dto);
  assert(view.notABusinessVerdict === true, "not verdict");
  assert(view.supportingSourceIds.length === 1, "supports");
}

{
  const summary: EvidenceSummaryDto = {
    total: 2,
    by_assessment_state: { missing: 1 },
    by_area: {},
    by_confidence: {},
    by_materiality: {},
    accepted_count: 0,
    unsupported_critical_claims: 1,
    conflicting_critical_claims: 0,
    outdated_critical_claims: 0,
    missing_critical_claims: 1,
    verdict_readiness_contribution: "blocked",
    creates_business_verdict: false,
  };
  const view = mapEvidenceSummary(summary);
  assert(view.readinessContribution === "blocked", "blocked");
  assert(view.notABusinessVerdict === true, "summary not verdict");
}

{
  const err = normalizeEvidenceError(
    new ApiError("x", 409, { safe_message: "non_atomic_claim" }),
  );
  assert(err.kind === "non_atomic_claim", "atomic");
}

console.log("evidence-p0-4.selfcheck: OK");
