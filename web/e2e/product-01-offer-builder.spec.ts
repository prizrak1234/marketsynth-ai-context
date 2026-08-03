import { expect, test } from "@playwright/test";
import {
  apiJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
} from "./helpers/cph2";

/**
 * PRODUCT-01.2 — Offer Builder owner acceptance E2E.
 * Requires live backend + frontend + PostgreSQL + CPH3_E2E_EMAIL/PASSWORD.
 */
test.describe.configure({ mode: "serial" });

function requireE2ECredentials(): ReturnType<typeof loadE2EContext> {
  try {
    return loadE2EContext();
  } catch {
    test.skip(true, "blocked_by_missing_e2e_credentials");
    throw new Error("unreachable");
  }
}

test.describe("PRODUCT-01 Offer Builder — live stack", () => {
  test.beforeEach(async ({ page }) => {
    requireE2ECredentials();
    await assertBackendMode(page, "backend");
    await page.addInitScript(() => {
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    });
    const ctx = loadE2EContext();
    await loginViaUi(page, ctx);
  });

  test("1 UI hygiene — no internal diagnostics", async ({ page }) => {
    await page.goto("/workspace");
    await expect(page.getByText("NEXT_PUBLIC_BOTFAZER_API_KEY")).toHaveCount(0);
    await expect(
      page.getByText("b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4"),
    ).toHaveCount(0);
    await expect(page.getByText("ms.skill.offer_builder")).toHaveCount(0);
    await expect(page.getByText("ms.skill.positioning")).toHaveCount(0);
  });

  test("2 no generic assistant redirect from launch pack", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[0]?.id;
    test.skip(!projectId, "No project — seed BIV context first");

    await page.goto(`/workspace/projects/${projectId}`);
    await expect(page).not.toHaveURL(/\/workspace\/assistant/);
    const prepareCta = page.getByTestId("cwf-cta-prepare_launch");
    if (await prepareCta.isVisible()) {
      await prepareCta.click();
      await expect(page).not.toHaveURL(/\/workspace\/assistant/);
      await expect(page.getByTestId("launch-pack-decision-panel")).toBeVisible();
    }
  });

  test("3 eligible path — prepare launch shows offer or building", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[0]?.id;
    test.skip(!projectId, "No project — complete BIV with proceed verdict first");

    await page.goto(`/workspace/projects/${projectId}`);
    await expect(page.getByTestId("launch-pack-decision-panel")).toBeVisible({
      timeout: 30_000,
    });

    const offerCard = page.getByTestId("offer-review-card");
    const building = page.getByTestId("cwf-offer-building");
    const prepareCta = page.getByTestId("cwf-cta-prepare_launch");

    if (await offerCard.isVisible()) {
      await expect(page.getByTestId("offer-detail-view")).toBeVisible();
      await expect(page.getByTestId("offer-upstream-bridge-notice")).toBeVisible();
      return;
    }

    if (await prepareCta.isVisible()) {
      await prepareCta.click();
      await expect(
        offerCard.or(building).or(page.getByTestId("cwf-launch-pack-requested")),
      ).toBeVisible({ timeout: 60_000 });
    }
  });

  test("4 approval — approve and reload restores state", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[0]?.id;
    test.skip(!projectId, "No project");

    await page.goto(`/workspace/projects/${projectId}`);
    const offerCard = page.getByTestId("offer-review-card");
    test.skip(!(await offerCard.isVisible()), "No offer on project");

    const approveBtn = page.getByTestId("offer-approve-btn");
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      await expect(page.getByTestId("offer-approved-badge")).toBeVisible({ timeout: 30_000 });
    } else {
      await expect(page.getByTestId("offer-approved-badge")).toBeVisible();
    }

    await page.reload();
    await expect(page.getByTestId("offer-approved-badge")).toBeVisible({ timeout: 30_000 });
  });

  test("5 revision — request revision increments version", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[0]?.id;
    test.skip(!projectId, "No project");

    await page.goto(`/workspace/projects/${projectId}`);
    test.skip(!(await page.getByTestId("offer-review-card").isVisible()), "No offer");

    const revisionBtn = page.getByTestId("offer-revision-btn");
    test.skip(!(await revisionBtn.isVisible()), "Offer not in reviewable state");

    const versionBefore = await page.getByTestId("offer-review-card").textContent();
    await revisionBtn.click();
    await page.getByTestId("offer-revision-form").waitFor({ state: "visible" });
    await page.locator("#offer-revision-comment").fill("E2E: adjust value proposition wording");
    await page.getByTestId("offer-revision-submit").click();
    await page.waitForTimeout(2000);
    await page.reload();
    await expect(page.getByTestId("offer-review-card")).toBeVisible();
    const versionAfter = await page.getByTestId("offer-review-card").textContent();
    expect(versionAfter).not.toEqual(versionBefore);
  });

  test("6 rejection — reject shows rejected state", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[1]?.id ?? projects[0]?.id;
    test.skip(!projectId, "No project — use dedicated rejection test project");

    await page.goto(`/workspace/projects/${projectId}`);
    const rejectBtn = page.getByTestId("offer-reject-btn");
    test.skip(!(await rejectBtn.isVisible()), "No reviewable offer for rejection scenario");

    await rejectBtn.click();
    await page.getByTestId("offer-reject-form").waitFor({ state: "visible" });
    await page.getByTestId("offer-reject-submit").click();
    await expect(page.getByTestId("offer-rejected-badge")).toBeVisible({ timeout: 30_000 });
  });

  test("7 blocked verdict — no offer card", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects.find((_, i) => i > 0)?.id;
    test.skip(!projectId, "Need project with non-eligible verdict");

    await page.goto(`/workspace/projects/${projectId}`);
    const blocked = page.getByTestId("cwf-offer-blocked");
    const launchBlocked = page.getByTestId("cwf-launch-pack-blocked");
    if ((await blocked.count()) > 0 || (await launchBlocked.count()) > 0) {
      await expect(page.getByTestId("offer-review-card")).toHaveCount(0);
    } else {
      test.skip(true, "Project has eligible verdict — use insufficient_evidence seed");
    }
  });
});
