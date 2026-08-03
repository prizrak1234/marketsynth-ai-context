import { expect, test } from "@playwright/test";

import { assertBackendMode } from "./helpers/cph2";



async function registerAndOpenWorkspace(page: import("@playwright/test").Page) {

  const email = `e2e.intent.${Date.now()}@marketsynth.local`;

  const password = "e2e-intent-pass12";

  await page.goto("/register");

  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });

  await page.getByTestId("register-email").fill(email);

  await page.getByTestId("register-display-name").fill("Intent User");

  await page.getByTestId("register-password").fill(password);

  await page.getByTestId("register-password-confirm").fill(password);

  await page.getByTestId("register-notice").check();

  await page.getByTestId("register-submit").click();

  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

}



test.describe("CWF.1a commercial entry (RUNTIME-01E freeze)", () => {

  test.beforeEach(async ({ page }) => {

    await assertBackendMode(page, "backend");

    await page.addInitScript(() => {

      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");

      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");

    });

    await registerAndOpenWorkspace(page);

  });



  test("Russian navigation shows frozen public nav only", async ({ page }) => {

    await expect(page.getByTestId("workspace-nav")).toBeVisible();

    await expect(page.getByTestId("nav-workspace")).toContainText("Главная");

    await expect(page.getByTestId("nav-workspace-projects")).toContainText("Проекты");

    await expect(page.getByTestId("nav-workspace-settings")).toBeVisible();

    await expect(page.getByTestId("nav-workspace-review")).toHaveCount(0);

    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);

    await expect(page.getByTestId("nav-workspace-channels")).toHaveCount(0);

    await expect(page.getByTestId("nav-workspace-assets")).toHaveCount(0);

  });



  test("start page renders canonical commercial entry", async ({ page }) => {

    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();

    await expect(page.getByTestId("canonical-entry-cta")).toContainText("Проверить мою идею");

    await expect(page.getByTestId("intent-start-panel")).toHaveCount(0);

    await expect(page.getByTestId("intent-card-create-content")).toHaveCount(0);

  });



  test("canonical CTA opens 7-step intake", async ({ page }) => {

    await page.getByTestId("canonical-entry-cta").click();

    await page.waitForURL(/\/workspace\/projects\/new\/?$/, { timeout: 15_000 });

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  });



  test("projects list remains accessible utility", async ({ page }) => {

    await page.getByTestId("nav-workspace-projects").click();

    await expect(page.getByTestId("projects-empty")).toBeVisible();

  });

});


