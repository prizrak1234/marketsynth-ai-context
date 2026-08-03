import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";
import { LOCALE_STORAGE_KEY } from "../src/lib/i18n/config";

const ARTIFACT_DIR = path.join(
  process.cwd(),
  "e2e-artifacts",
  "commercial-ux-slice-f-landing",
);

const VIEWPORTS = [
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "laptop-1280", width: 1280, height: 800 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-390", width: 390, height: 844 },
] as const;

async function registerCommercialUser(page: Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-slice-f-pass1";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Slice F Landing User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
  return { email, password };
}

async function captureLanding(page: Page, filename: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, filename),
    fullPage: true,
  });
}

test.describe("Commercial UX Slice F — landing", () => {
  test.beforeAll(() => {
    fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  });

  test("A public landing loads without auth", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await expect(page.getByTestId("public-landing-hero")).toBeVisible();
  });

  test("B no AppShell sidebar on landing", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await expect(page.getByTestId("nav-workspace")).toHaveCount(0);
    await expect(page.getByTestId("workspace-nav-menu")).toHaveCount(0);
  });

  test("C hero and core value visible", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await expect(page.getByTestId("public-landing-headline")).toBeVisible();
    await expect(page.getByTestId("public-landing-core-value")).toBeVisible();
    await expect(page.getByTestId("public-landing-how-it-works")).toBeVisible();
  });

  test("D unauthenticated CTA opens login with correct next", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    const cta = page.getByTestId("public-landing-cta");
    await expect(cta).toHaveAttribute("href", /login\?next=%2Fworkspace%2Fprojects%2Fnew/);
    await captureLanding(page, "landing-cta-login-next.png");
  });

  test("E login then intake", async ({ browser }) => {
    const authPage = await browser.newPage();
    await assertBackendMode(authPage, "backend");
    const { email, password } = await registerCommercialUser(authPage, "slicef.e");
    await authPage.close();

    const context = await browser.newContext();
    const page = await context.newPage();
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await page.getByTestId("public-landing-cta").click();
    await page.waitForURL(/\/login/, { timeout: 15_000 });
    await page.getByTestId("login-email").fill(email);
    await page.getByLabel("Пароль").fill(password);
    await page.getByTestId("login-submit").click();
    await page.waitForURL(/\/workspace\/projects\/new/, { timeout: 30_000 });
    await captureLanding(page, "intake-after-auth.png");
    await context.close();
  });

  test("F authenticated CTA opens intake", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "slicef.auth");
    await page.goto("/");
    await expect(page.getByTestId("public-landing-cta")).toHaveAttribute(
      "href",
      "/workspace/projects/new",
    );
    await page.getByTestId("public-landing-cta").click();
    await page.waitForURL(/\/workspace\/projects\/new/, { timeout: 15_000 });
    await captureLanding(page, "landing-authenticated.png");
  });

  test("G no POST /runs from landing visit", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const runs: string[] = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/runs\b/.test(req.url())) {
        runs.push(req.url());
      }
    });
    await page.goto("/");
    await page.getByTestId("public-landing-cta").click();
    await page.waitForTimeout(1_000);
    expect(runs).toEqual([]);
  });

  test("H no project created before intake action", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "slicef.noproj");
    let postProjects = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/projects\b/.test(req.url())) {
        postProjects += 1;
      }
    });
    await page.goto("/");
    await page.waitForTimeout(500);
    expect(postProjects).toBe(0);
  });

  test("I reserved/internal modules absent from landing DOM", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("intent-card-create-content")).toHaveCount(0);
    await expect(page.getByTestId("intent-card-prepare-launch")).toHaveCount(0);
  });

  test("J malicious localStorage flag ignored in production build", async ({ page }) => {
    if (process.env.SLICE_F_PRODUCTION_BUILD !== "true") {
      throw new Error("Scenario J requires SLICE_F_PRODUCTION_BUILD=true");
    }
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await page.evaluate((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.reload();
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("public-landing-hero")).toBeVisible();
  });

  test("K mobile header navigation", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await page.getByTestId("public-landing-mobile-menu-button").click();
    await expect(page.getByTestId("public-landing-mobile-menu")).toBeVisible();
    await expect(page.getByTestId("public-header-mobile-primary-cta")).toBeVisible();
    await captureLanding(page, "landing-mobile-menu.png");
  });

  test("L four viewport layout without horizontal overflow", async ({ page }) => {
    await assertBackendMode(page, "backend");
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      expect(overflow, viewport.name).toBe(false);
      await captureLanding(page, `landing-${viewport.name}.png`);
    }
  });

  test("M keyboard tab reaches primary actions", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await page.keyboard.press("Tab");
    const skip = page.locator('a[href="#main-content"]');
    await expect(skip).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(page.getByTestId("public-landing-brand")).toBeFocused();
  });

  test("N EN locale renders English headline", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, "en");
    }, LOCALE_STORAGE_KEY);
    await page.goto("/");
    await expect(page.getByTestId("public-landing-headline")).toContainText(/Before you spend/i);
    await captureLanding(page, "landing-en.png");
  });

  test("O browser Back returns to landing from login", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    await page.getByTestId("public-landing-cta").click();
    await page.waitForURL(/\/login/);
    await page.goBack();
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
  });

  test("P no console errors on landing load", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/");
    await expect(page.getByTestId("public-landing-hero")).toBeVisible();
    expect(errors.filter((e) => !/favicon|404/.test(e))).toEqual([]);
  });

  test("Q unauthenticated landing screenshot baseline", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await captureLanding(page, "landing-unauthenticated.png");
  });
});
