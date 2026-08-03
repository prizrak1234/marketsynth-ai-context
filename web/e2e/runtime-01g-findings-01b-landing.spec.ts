import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";
import { CANONICAL_COMMERCIAL_ROUTES, loginNextHref } from "../src/lib/routes/commercial-surface";

const LANDING_URL = "http://localhost:3000/";
const ARTIFACT_DIR = "e2e-artifacts/findings-01b";

test.describe("FINDINGS-01B canonical public landing", () => {
  test("GET / returns 200 with hero and CTA after direct navigation", async ({ page }) => {
    const response = await page.goto(LANDING_URL);
    expect(response?.status()).toBe(200);

    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await expect(page.getByRole("link", { name: "Проверить мою идею" })).toBeVisible();
    await expect(page.getByText("Прежде чем потратить ваши деньги")).toBeVisible();
    await expect(page.getByText("Проверим, стоит ли вообще запускать проект.")).toBeVisible();
    await expect(page.getByTestId("workspace-nav")).toHaveCount(0);
    await expect(page.getByText("Операционный контур")).toHaveCount(0);
  });

  test("hard reload keeps landing available", async ({ page }) => {
    await page.goto(LANDING_URL);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await page.reload({ waitUntil: "networkidle" });
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await expect(page.getByRole("link", { name: "Проверить мою идею" })).toBeVisible();
  });

  test("fresh browser context opens / without storage", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const response = await page.goto(LANDING_URL);
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await context.close();
  });

  test("unauthenticated CTA targets login with canonical intake next", async ({ page }) => {
    await page.goto(LANDING_URL);
    const cta = page.getByRole("link", { name: "Проверить мою идею" });
    await expect(cta).toHaveAttribute(
      "href",
      loginNextHref(CANONICAL_COMMERCIAL_ROUTES.intakeStart),
    );
  });

  test("authenticated CTA path reaches 7-step intake", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const email = `e2e.01b.intake.${Date.now()}@marketsynth.local`;
    const password = "e2e-01b-pass12";
    await page.goto("/register");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-display-name").fill("Landing User");
    await page.getByTestId("register-password").fill(password);
    await page.getByTestId("register-password-confirm").fill(password);
    await page.getByTestId("register-notice").check();
    await page.getByTestId("register-submit").click();
    await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await page.goto(LANDING_URL);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    const cta = page.getByTestId("public-landing-cta");
    await expect(cta).toHaveAttribute("href", CANONICAL_COMMERCIAL_ROUTES.intakeStart, {
      timeout: 15_000,
    });
    await cta.click();
    await page.waitForURL(/\/workspace\/projects\/new\/?$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("1920x1080 public landing screenshot", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(LANDING_URL);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await page.screenshot({
      path: `${ARTIFACT_DIR}/landing-1920.png`,
      fullPage: true,
    });
  });

  test("1366x768 public landing screenshot", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto(LANDING_URL);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await page.screenshot({
      path: `${ARTIFACT_DIR}/landing-1366.png`,
      fullPage: true,
    });
  });
});
