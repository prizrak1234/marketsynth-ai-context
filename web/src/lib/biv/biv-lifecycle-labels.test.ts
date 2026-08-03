import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  BIV_LIFECYCLE_PARTIAL,
  BIV_LIFECYCLE_QUEUED,
  bivLifecycleStatusLabel,
} from "@/lib/biv/biv-lifecycle-labels";
import type { BusinessIdeaValidationProjectLatestRunSummary } from "@/lib/api/endpoints/business-idea-validation";

function summary(
  overrides: Partial<BusinessIdeaValidationProjectLatestRunSummary>,
): BusinessIdeaValidationProjectLatestRunSummary {
  return {
    project_id: "p1",
    run_id: "r1",
    user_request_id: "u1",
    status: "running",
    created_at: "2026-07-30T17:00:00Z",
    has_output: false,
    retry_allowed: false,
    ...overrides,
  };
}

describe("biv lifecycle labels (PRODUCT-01.3B)", () => {
  it("maps queued", () => {
    assert.equal(
      bivLifecycleStatusLabel(summary({ status: "queued" })),
      BIV_LIFECYCLE_QUEUED,
    );
  });

  it("maps running", () => {
    assert.equal(
      bivLifecycleStatusLabel(summary({ status: "running" })),
      "Исследование выполняется",
    );
  });

  it("maps partial", () => {
    assert.equal(
      bivLifecycleStatusLabel(
        summary({ status: "failed", result_kind: "partial_research" }),
      ),
      BIV_LIFECYCLE_PARTIAL,
    );
  });

  it("maps technical failure", () => {
    assert.equal(
      bivLifecycleStatusLabel(summary({ status: "failed", has_output: false })),
      "Исследование прервано",
    );
  });

  it("maps verdict", () => {
    assert.equal(
      bivLifecycleStatusLabel(summary({ status: "succeeded" })),
      "Исследование завершено",
    );
  });
});
