import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { translate } from "@/lib/i18n/domain-labels";
import { getLandingPageMetadata } from "@/lib/landing/landing-metadata";
import {
  getLandingIntakeCapabilityId,
  getReservedLandingCapabilityNames,
  isLandingCapabilityActionAvailable,
  isSafeInternalNext,
  resolveLandingIntakeHref,
  resolveLandingLoginNextHref,
  resolveLandingPrimaryCtaHref,
} from "@/lib/landing/public-landing";
import {
  getPublicNavigationCapabilities,
  isCapabilityPubliclyAvailable,
} from "@/lib/product-capabilities/selectors";

describe("public landing resolver (Slice F)", () => {
  it("uses registry-resolved Intake CTA", () => {
    assert.equal(getLandingIntakeCapabilityId(), "project.intake");
    assert.equal(resolveLandingIntakeHref(), "/workspace/projects/new");
    assert.ok(isCapabilityPubliclyAvailable("project.intake"));
  });

  it("keeps planned/reserved capabilities off public landing actions", () => {
    for (const id of ["project.strategy", "project.launch", "workspace.analytics", "settings.crm"]) {
      assert.equal(isLandingCapabilityActionAvailable(id), false);
    }
    assert.equal(getPublicNavigationCapabilities().length, 3);
  });

  it("resolves authenticated CTA target to canonical intake", () => {
    assert.equal(resolveLandingPrimaryCtaHref(true), "/workspace/projects/new");
  });

  it("resolves unauthenticated CTA target to login with next", () => {
    assert.equal(
      resolveLandingPrimaryCtaHref(false),
      "/login?next=%2Fworkspace%2Fprojects%2Fnew",
    );
    assert.equal(
      resolveLandingLoginNextHref(),
      "/login?next=%2Fworkspace%2Fprojects%2Fnew",
    );
  });

  it("rejects unsafe next paths", () => {
    assert.equal(isSafeInternalNext("/workspace/projects/new"), true);
    assert.equal(isSafeInternalNext("//evil.example"), false);
    assert.equal(isSafeInternalNext("https://evil.example"), false);
  });

  it("provides RU landing copy keys", () => {
    assert.match(translate("ru", "landing.hero.headline"), /Прежде чем потратить/);
    assert.equal(translate("ru", "landing.hero.primaryCta"), "Проверить мою идею");
  });

  it("provides EN landing copy keys", () => {
    assert.match(translate("en", "landing.hero.headline"), /Before you spend/i);
    assert.equal(translate("en", "landing.hero.primaryCta"), "Validate my idea");
  });

  it("provides landing metadata", () => {
    const ruMeta = getLandingPageMetadata("ru");
    assert.match(String(ruMeta.title), /Marketsynth/);
    assert.match(String(ruMeta.description), /AI-маркетинговое агентство/);
    const enMeta = getLandingPageMetadata("en");
    assert.match(String(enMeta.title), /Marketsynth/i);
  });

  it("does not expose internal capabilities as landing actions", () => {
    for (const id of ["internal.assistant", "internal.review", "internal.channels"]) {
      assert.equal(isLandingCapabilityActionAvailable(id), false);
    }
  });

  it("fails safely for unknown capability", () => {
    assert.equal(isLandingCapabilityActionAvailable("unknown.capability"), false);
    assert.ok(getReservedLandingCapabilityNames().length >= 5);
  });
});
