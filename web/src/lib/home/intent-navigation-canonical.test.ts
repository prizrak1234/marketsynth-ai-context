import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { toCanonicalPublicNavigationTarget } from "@/lib/routes/commercial-surface";

describe("intent-navigation canonical freeze", () => {
  it("maps biv target to canonical intake for public surface", () => {
    const mapped = toCanonicalPublicNavigationTarget({
      kind: "biv",
      task: "idea",
      scenario: "idea_validation",
    });
    assert.equal(mapped.kind, "canonical_intake");
  });

  it("preserves assistant target for developer flows", () => {
    const mapped = toCanonicalPublicNavigationTarget({
      kind: "assistant",
      task: "content",
      scenario: "content",
    });
    assert.equal(mapped.kind, "assistant");
  });
});
