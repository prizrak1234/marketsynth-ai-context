import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  getCapability,
  getDeveloperNavigationCapabilities,
  getProjectStageCapabilities,
  getPublicHomeDirectionIntentIds,
  getPublicNavigationCapabilities,
  getReservedCapabilities,
  isCapabilityPubliclyAvailable,
  isDeveloperCapabilityVisible,
  isHomeIntentPubliclyAvailable,
  resolveCapabilityRoute,
} from "./selectors";
import { PRODUCT_CAPABILITY_REGISTRY } from "./registry";
import {
  assertValidCapabilityRegistry,
  validateCapabilityActivation,
  validateCapabilityRegistry,
} from "./validation";

describe("product capability registry", () => {
  it("validates registry invariants PASS", () => {
    assert.doesNotThrow(() => assertValidCapabilityRegistry());
    assert.equal(validateCapabilityRegistry().length, 0);
  });

  it("rejects duplicate capability ids", () => {
    const issues = validateCapabilityRegistry();
    const duplicate = issues.find((issue) => issue.code === "id.duplicate");
    assert.equal(duplicate, undefined);
  });

  it("rejects orphan parentId references", () => {
    const issues = validateCapabilityRegistry();
    assert.equal(
      issues.some((issue) => issue.code === "hierarchy.orphan_parent"),
      false,
    );
  });

  it("rejects circular hierarchy", () => {
    const issues = validateCapabilityRegistry();
    assert.equal(
      issues.some((issue) => issue.code === "hierarchy.circular"),
      false,
    );
  });

  it("rejects available public route capabilities without route", () => {
    const issues = validateCapabilityRegistry();
    assert.equal(
      issues.some((issue) => issue.code === "route.missing_public_available"),
      false,
    );
  });

  it("excludes reserved capabilities from public navigation", () => {
    const nav = getPublicNavigationCapabilities();
    const reservedRoutes = getReservedCapabilities()
      .map((capability) => capability.route)
      .filter(Boolean);
    for (const href of reservedRoutes) {
      assert.equal(
        nav.some((item) => item.href === href),
        false,
        `reserved route leaked to public nav: ${href}`,
      );
    }
  });

  it("excludes internal capabilities from production navigation", () => {
    assert.equal(
      isDeveloperCapabilityVisible("internal.assistant", {
        developerMode: false,
        nodeEnv: "production",
      }),
      false,
    );
    const nav = getPublicNavigationCapabilities();
    assert.equal(nav.some((item) => item.href === "/workspace/assistant"), false);
  });

  it("enables developer capabilities only in approved environment with flag", () => {
    assert.equal(
      isDeveloperCapabilityVisible("internal.assistant", {
        developerMode: true,
        nodeEnv: "production",
      }),
      false,
    );
    assert.equal(
      isDeveloperCapabilityVisible("internal.assistant", {
        developerMode: true,
        nodeEnv: "development",
      }),
      true,
    );
    const devNav = getDeveloperNavigationCapabilities({
      developerMode: true,
      nodeEnv: "development",
    });
    assert.ok(devNav.some((item) => item.href === "/workspace/assistant"));
  });

  it("preserves canonical project stage order for available stages", () => {
    const stages = getProjectStageCapabilities();
    assert.deepEqual(
      stages.map((stage) => stage.id),
      ["project.intake", "project.research", "project.content_director"],
    );
  });

  it("keeps future modules reserved or planned", () => {
    for (const id of [
      "project.strategy",
      "project.launch",
      "launch.visuals",
      "launch.publication",
      "workspace.analytics",
      "settings.billing",
      "settings.hr",
    ]) {
      const capability = getCapability(id);
      assert.ok(capability);
      assert.notEqual(capability?.availability, "available");
    }
  });

  it("exposes only registry-approved home direction intents", () => {
    assert.deepEqual(getPublicHomeDirectionIntentIds(), ["validate-idea"]);
    assert.equal(isHomeIntentPubliclyAvailable("validate-idea"), true);
    assert.equal(isHomeIntentPubliclyAvailable("create-content"), false);
    assert.equal(isHomeIntentPubliclyAvailable("prepare-launch"), false);
  });

  it("preserves project context in route resolution", () => {
    assert.equal(
      resolveCapabilityRoute("project.research", { projectId: "proj-123" }),
      "/workspace?project=proj-123",
    );
    assert.equal(
      resolveCapabilityRoute("project.content_director", { projectId: "proj-123" }),
      "/workspace?view=content_director&project=proj-123",
    );
  });

  it("exposes Content Director as public project capability", () => {
    assert.equal(isCapabilityPubliclyAvailable("project.content_director"), true);
    assert.equal(isCapabilityPubliclyAvailable("launch.visuals"), false);
  });

  it("fails safely for unknown capability", () => {
    assert.equal(getCapability("unknown.module"), undefined);
    assert.equal(isCapabilityPubliclyAvailable("unknown.module"), false);
    assert.equal(resolveCapabilityRoute("unknown.module"), null);
  });

  it("requires activation contract fields for available capabilities", () => {
    for (const capability of PRODUCT_CAPABILITY_REGISTRY) {
      if (capability.availability !== "available") continue;
      const issues = validateCapabilityActivation(capability);
      assert.equal(
        issues.length,
        0,
        `activation issues for ${capability.id}: ${issues.map((i) => i.code).join(",")}`,
      );
    }
  });

  it("does not treat localStorage as production bypass for internal nav", () => {
    const productionNav = getPublicNavigationCapabilities();
    assert.equal(productionNav.length, 3);
    assert.deepEqual(
      productionNav.map((item) => item.href),
      ["/workspace", "/workspace/projects", "/workspace/settings"],
    );
  });
});
