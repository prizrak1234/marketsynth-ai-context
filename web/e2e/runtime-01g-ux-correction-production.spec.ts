import { expect, test } from "@playwright/test";
import { assertBackendMode, fillIntakeWizard } from "./helpers/cph2";
import { assertCustomerSafeDom } from "./helpers/customer-surface-dom";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

const ARTIFACT_DIR = "e2e-artifacts/ux-correction";

async function registerUser(page: import("@playwright/test").Page) {
  const email = `e2e.ux.prod.${Date.now()}@marketsynth.local`;
  const password = "e2e-ux-prod-pass12";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("UX Prod User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
}

test.describe("RUNTIME-01G UX correction — production DOM boundary", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, "1");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
  });

  test("GET / and /workspace work in production build", async ({ page }) => {
    const landing = await page.goto("/");
    expect(landing?.status()).toBe(200);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await expect(page.getByTestId("public-landing-cta")).toBeVisible();

    const workspace = await page.goto("/workspace");
    expect(workspace?.status()).toBeLessThan(400);
  });

  test("production review is customer-safe even with developer localStorage flag", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await assertBackendMode(page, "backend");
    await registerUser(page);
    await fillIntakeWizard(page, "Кофейня self-service для офисных кластеров");
    await page.goto("/workspace/projects/new/review");

    await expect(page.getByTestId("intake-golden-path-submit")).toHaveCount(1);
    await expect(page.getByTestId("intake-review-back-edit")).toHaveCount(1);
    await expect(page.getByText("Сохранить полный бриф")).toHaveCount(0);
    await expect(page.getByText("Сохранить черновик")).toHaveCount(0);
    await expect(page.getByTestId("intake-developer-diagnostics")).toHaveCount(0);
    await assertCustomerSafeDom(page);
    await page.screenshot({
      path: `${ARTIFACT_DIR}/review-production-1920.png`,
      fullPage: true,
    });
  });

  test("production CTA from landing targets canonical intake flow", async ({ page }) => {
    await page.goto("/");
    const cta = page.getByTestId("public-landing-cta");
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute("href");
    expect(href).toMatch(/login\?next=.*projects%2Fnew|\/workspace\/projects\/new/);
  });
});
