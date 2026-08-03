import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

async function registerAndOpenWorkspace(page: import("@playwright/test").Page) {
  const email = `e2e.01e.prod.${Date.now()}@marketsynth.local`;
  const password = "e2e-01e-pass12";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Prod Boundary User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?(\?|$)/, { timeout: 30_000 });
  await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible({
    timeout: 30_000,
  });
}

test.describe("RUNTIME-01E production build developer-mode boundary", () => {
  test.beforeEach(async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
  });

  test("localStorage flag does not expand nav or show legacy entry", async ({ page }) => {
    await registerAndOpenWorkspace(page);
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await expect(page.getByTestId("intent-card-create-content")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-channels")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-review")).toHaveCount(0);
  });

  test("localStorage flag does not open legacy assistant route", async ({ page }) => {
    await registerAndOpenWorkspace(page);
    await page.goto("/workspace/assistant", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/workspace\/?(\?|$)/, { timeout: 30_000 });
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await expect(page.getByTestId("workspace-assistant")).toHaveCount(0);
  });

  test("localStorage flag does not open developer workspace console", async ({ page }) => {
    await registerAndOpenWorkspace(page);
    await page.goto("/workspace/developer", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/workspace\/?(\?|$)/, { timeout: 30_000 });
    await expect(page.getByTestId("developer-workspace")).toHaveCount(0);
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
  });

  test("localStorage flag does not open legacy project pipeline route", async ({ page }) => {
    await registerAndOpenWorkspace(page);
    await page.goto("/workspace/projects/test-project-id/verdict", {
      waitUntil: "domcontentloaded",
    });
    // LegacyProjectPipelineGuard → workspaceProjectHref(projectId) in production.
    await expect(page).toHaveURL(/\/workspace\?project=test-project-id/, {
      timeout: 30_000,
    });
    await expect(page.getByTestId("legacy-commercial-notice")).toHaveCount(0);
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
  });
});
