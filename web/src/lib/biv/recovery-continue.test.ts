import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError } from "@/lib/api/client";
import type { AnalysisContextRecord } from "@/lib/api/endpoints/analysis-contexts";

import {
  planRecoveryContinue,
  shouldOpenFormAfterConfirmError,
} from "./recovery-continue";

function context(overrides: Partial<AnalysisContextRecord> = {}): AnalysisContextRecord {
  return {
    context_id: "ctx-1",
    owner_id: "owner-1",
    project_id: "project-1",
    state: "hydrated_unconfirmed",
    source_mode: null,
    data_source_label: null,
    idea_description: "Онлайн-школа",
    product_or_service: null,
    target_customer: null,
    geography: null,
    business_model: null,
    pricing_or_revenue_model: null,
    current_stage: null,
    budget_context: null,
    known_competitors: null,
    analysis_goal: null,
    target_customer_unknown: false,
    geography_unknown: false,
    confirmed_by_user: false,
    confirmed_at: null,
    input_snapshot_hash: "abc",
    source_snapshot_id: null,
    is_active: true,
    missing_fields: [],
    warnings: [],
    created_at: "2026-07-29T00:00:00.000Z",
    updated_at: "2026-07-29T00:00:00.000Z",
    ...overrides,
  };
}

describe("planRecoveryContinue", () => {
  it("opens incomplete form when required fields are missing", () => {
    const plan = planRecoveryContinue(
      context({
        missing_fields: ["product_or_service", "analysis_goal"],
      }),
    );
    assert.deepEqual(plan, {
      action: "open_incomplete_form",
      missingFields: ["product_or_service", "analysis_goal"],
    });
  });

  it("confirms when specificity gate passes on client-visible fields", () => {
    const plan = planRecoveryContinue(context({ missing_fields: [] }));
    assert.equal(plan.action, "confirm");
  });
});

describe("shouldOpenFormAfterConfirmError", () => {
  it("returns true for analysis_context_incomplete", () => {
    assert.equal(
      shouldOpenFormAfterConfirmError(
        new ApiError("incomplete", 400, { error_code: "analysis_context_incomplete" }, "bad"),
      ),
      true,
    );
  });

  it("returns false for other API errors", () => {
    assert.equal(
      shouldOpenFormAfterConfirmError(
        new ApiError("stale", 409, { error_code: "analysis_context_stale" }, "stale"),
      ),
      false,
    );
  });
});
