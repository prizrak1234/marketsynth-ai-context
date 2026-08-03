import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

async function registerCommercialUser(page: import("@playwright/test").Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-01g-pass12";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Commercial Home User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
  return { email, password };
}

test.describe("RUNTIME-01G commercial home surface correction", () => {
  test("commercial home hides Developer Workspace link without developer flag", async ({
    page,
  }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
    }, HOME_DEVELOPER_MODE_KEY);
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "e2e.01g.devlink");

    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await expect(page.getByTestId("home-open-developer-workspace")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
  });

  test("developer flag reveals Developer Workspace link in non-production dev server", async ({
    page,
  }) => {
    test.skip(process.env.NODE_ENV === "production", "Developer link is dev-server scoped");
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "e2e.01g.devon");
    await page.evaluate((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.reload();
    await expect(page.getByTestId("home-open-developer-workspace")).toBeVisible();
  });

  test("recent projects empty state is commercial (no unavailable spam)", async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
    }, HOME_DEVELOPER_MODE_KEY);
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "e2e.01g.empty");

    const recent = page.getByTestId("home-recent-projects-empty");
    const list = page.getByTestId("home-recent-projects");
    await expect(recent.or(list)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Недоступно")).toHaveCount(0);
  });

  test("1920x1080 commercial home screenshot", async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
    }, HOME_DEVELOPER_MODE_KEY);
    await page.setViewportSize({ width: 1920, height: 1080 });
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "e2e.01g.1920");

    await expect(page.getByTestId("canonical-entry-cta")).toBeVisible();
    await expect(page.getByTestId("home-open-developer-workspace")).toHaveCount(0);
    await page.screenshot({
      path: "test-results/runtime-01g-commercial-home-1920.png",
      fullPage: true,
    });
  });

  test("1366x768 commercial home screenshot", async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
    }, HOME_DEVELOPER_MODE_KEY);
    await page.setViewportSize({ width: 1366, height: 768 });
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "e2e.01g.1366");

    await expect(page.getByTestId("canonical-entry-headline")).toBeVisible();
    await expect(page.getByTestId("canonical-entry-cta")).toBeVisible();
    await page.screenshot({
      path: "test-results/runtime-01g-commercial-home-1366.png",
      fullPage: true,
    });
  });
});
