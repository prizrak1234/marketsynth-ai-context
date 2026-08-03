import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { workspaceProjectHref } from "@/lib/integration/enrich-workspace-projects-biv";

describe("enrich workspace projects biv (PRODUCT-01.3B)", () => {
  it("builds commercial home deep link with project context", () => {
    assert.equal(
      workspaceProjectHref("4ecfb41a-b9ef-4b60-aa04-dfd7b6e01ae8"),
      "/workspace?project=4ecfb41a-b9ef-4b60-aa04-dfd7b6e01ae8",
    );
  });
});
