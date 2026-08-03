import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  CANONICAL_COMMERCIAL_ROUTES,
  FROZEN_PUBLIC_NAV_HREFS,
  PUBLIC_WORKSPACE_NAV,
  isLegacyProjectPipelinePath,
  isPublicWorkspaceNavVisible,
  projectIdFromLegacyPipelinePath,
  resolveLegacyCommercialRedirect,
  toCanonicalPublicNavigationTarget,
  workspaceProjectHref,
} from "./commercial-surface";
import { isHrefPubliclyNavVisible } from "@/lib/product-capabilities";

describe("commercial-surface", () => {
  it("defines canonical intake as 7-step wizard start", () => {
    assert.equal(CANONICAL_COMMERCIAL_ROUTES.intakeStart, "/workspace/projects/new");
  });

  it("public nav excludes frozen capabilities", () => {
    for (const href of FROZEN_PUBLIC_NAV_HREFS) {
      assert.equal(
        PUBLIC_WORKSPACE_NAV.some((item) => item.href === href),
        false,
        `frozen href leaked into public nav: ${href}`,
      );
    }
  });

  it("hides assistant/channels/review/assets from public nav unless developer mode", () => {
    assert.equal(isPublicWorkspaceNavVisible("/workspace/assistant"), false);
    assert.equal(isPublicWorkspaceNavVisible("/workspace/channels"), false);
    assert.equal(isPublicWorkspaceNavVisible("/workspace/review"), false);
    assert.equal(isPublicWorkspaceNavVisible("/workspace/assets"), false);
    assert.equal(isPublicWorkspaceNavVisible("/workspace/projects"), true);
    assert.equal(
      isPublicWorkspaceNavVisible("/workspace/assistant", { developerMode: true }),
      false,
      "developer flag alone must not bypass production environment",
    );
    assert.equal(
      isHrefPubliclyNavVisible("/workspace/assistant", {
        developerMode: true,
        nodeEnv: "development",
      }),
      true,
    );
  });

  it("maps legacy BIV intent target to canonical intake", () => {
    const mapped = toCanonicalPublicNavigationTarget({
      kind: "biv",
      task: "Проверить идею",
      scenario: "idea_validation",
    });
    assert.equal(mapped.kind, "canonical_intake");
  });

  it("redirects legacy task index to workspace home", () => {
    assert.equal(resolveLegacyCommercialRedirect("/workspace/tasks"), "/workspace");
    assert.equal(resolveLegacyCommercialRedirect("/workspace/tasks?intent=content"), "/workspace");
  });

  it("detects legacy project pipeline paths", () => {
    assert.equal(
      isLegacyProjectPipelinePath("/workspace/projects/abc/investigation"),
      true,
    );
    assert.equal(projectIdFromLegacyPipelinePath("/workspace/projects/abc/investigation"), "abc");
  });

  it("builds workspace project hydration href", () => {
    assert.equal(workspaceProjectHref("proj-1"), "/workspace?project=proj-1");
  });
});
