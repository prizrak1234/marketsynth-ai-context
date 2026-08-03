import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

async function registerCommercialUser(page: import("@playwright/test").Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-cap-reg-pass1";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Capability Registry User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
  return { email, password };
}

test.describe("PRODUCT-01.5 capability registry navigation", () => {
  test("A production nav remains Home / Projects / Settings", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.nav");

    await expect(page.getByTestId("nav-workspace")).toBeVisible();
    await expect(page.getByTestId("nav-workspace-projects")).toBeVisible();
    await expect(page.getByTestId("nav-workspace-settings")).toBeVisible();
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-review")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-channels")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-assets")).toHaveCount(0);
  });

  test("B reserved modules absent from commercial home", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.reserved");

    await expect(page.getByTestId("intent-card-create-content")).toHaveCount(0);
    await expect(page.getByTestId("intent-card-prepare-launch")).toHaveCount(0);
    await expect(page.getByTestId("intent-card-grow-business")).toHaveCount(0);
  });

  test("C malicious localStorage cannot expose internal nav in production build", async ({
    page,
  }) => {
    if (process.env.CAP_REGISTRY_PRODUCTION_BUILD !== "true") {
      throw new Error(
        "Scenario C requires CAP_REGISTRY_PRODUCTION_BUILD=true (production browser gate phase)",
      );
    }
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.lsprod");
    await page.evaluate((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.reload();
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await page.goto("/workspace/assistant");
    await page.waitForURL(/\/workspace\/?$/, { timeout: 15_000 });
  });

  test("D developer environment exposes approved internal surfaces with flag", async ({ page }) => {
    if (process.env.CAP_REGISTRY_DEVELOPMENT_BUILD !== "true") {
      throw new Error(
        "Scenario D requires CAP_REGISTRY_DEVELOPMENT_BUILD=true (development browser gate phase)",
      );
    }
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.dev");
    await page.evaluate((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.reload();
    await expect(page.getByTestId("nav-workspace-assistant")).toBeVisible();
  });

  test("E home cards contain no dead CTA in commercial entry", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.home");

    await expect(page.getByTestId("canonical-entry-cta")).toBeVisible();
    await expect(page.getByTestId("canonical-entry-cta")).toHaveAttribute(
      "href",
      "/workspace/projects/new",
    );
  });

  test("F research CTA still opens canonical intake", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    const cta = page.getByTestId("public-landing-cta");
    await expect(cta).toHaveAttribute("href", /login\?next=%2Fworkspace%2Fprojects%2Fnew/);
  });

  test("G project deep link contract unchanged", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.project");
    await page.goto("/workspace?project=00000000-0000-4000-8000-000000000001");
    await expect(page).toHaveURL(/project=00000000-0000-4000-8000-000000000001/);
  });

  test("H mobile navigation follows same registry as desktop", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.mobile");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByTestId("workspace-nav-menu").click();
    const drawer = page.getByTestId("workspace-nav-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByTestId("nav-workspace")).toBeVisible();
    await expect(drawer.getByTestId("nav-workspace-projects")).toBeVisible();
    await expect(drawer.getByTestId("nav-workspace-settings")).toBeVisible();
    await expect(drawer.getByTestId("nav-workspace-assistant")).toHaveCount(0);
  });

  test("I direct legacy research route redirects to workspace home", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.legacy");
    await page.goto("/workspace/research");
    await page.waitForURL(/\/workspace\/?$/, { timeout: 15_000 });
  });

  test("J legacy assistant route keeps approved redirect for commercial users", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "capreg.assistant");
    await page.goto("/workspace/assistant");
    await page.waitForURL(/\/workspace\/?$/, { timeout: 15_000 });
  });
});
