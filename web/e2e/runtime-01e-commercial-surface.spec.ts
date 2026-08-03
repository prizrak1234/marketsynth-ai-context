import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

test.describe("RUNTIME-01E commercial surface freeze", () => {
  test("landing CTA targets canonical 7-step intake via login", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.goto("/");
    const cta = page.getByRole("link", { name: "Проверить мою идею" });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", /login\?next=%2Fworkspace%2Fprojects%2Fnew/);
  });

  test("authenticated workspace shows canonical entry without legacy intent cards", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    const email = `e2e.01e.${Date.now()}@marketsynth.local`;
    const password = "e2e-01e-pass12";
    await page.goto("/register");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-display-name").fill("Surface User");
    await page.getByTestId("register-password").fill(password);
    await page.getByTestId("register-password-confirm").fill(password);
    await page.getByTestId("register-notice").check();
    await page.getByTestId("register-submit").click();
    await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await expect(page.getByTestId("canonical-entry-cta")).toBeVisible();
    await expect(page.getByTestId("intent-card-create-content")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-channels")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-review")).toHaveCount(0);
    await expect(page.getByTestId("nav-workspace-projects")).toBeVisible();
  });

  test("legacy assistant route redirects to workspace for commercial users", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const email = `e2e.01e.legacy.${Date.now()}@marketsynth.local`;
    const password = "e2e-01e-pass12";
    await page.goto("/register");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-display-name").fill("Legacy User");
    await page.getByTestId("register-password").fill(password);
    await page.getByTestId("register-password-confirm").fill(password);
    await page.getByTestId("register-notice").check();
    await page.getByTestId("register-submit").click();
    await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await page.goto("/workspace/assistant");
    await page.waitForURL(/\/workspace\/?$/, { timeout: 15_000 });
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
  });
});

test.describe("RUNTIME-01E developer-mode boundary (e2e dev server)", () => {
  test("commercial nav stays frozen without developer localStorage flag", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    const email = `e2e.01e.devflag.${Date.now()}@marketsynth.local`;
    const password = "e2e-01e-pass12";
    await page.goto("/register");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-display-name").fill("Dev Flag User");
    await page.getByTestId("register-password").fill(password);
    await page.getByTestId("register-password-confirm").fill(password);
    await page.getByTestId("register-notice").check();
    await page.getByTestId("register-submit").click();
    await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await expect(page.getByTestId("nav-workspace-assistant")).toHaveCount(0);
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await expect(page.getByTestId("home-open-developer-workspace")).toHaveCount(0);
  });

  test("unauthenticated user with localStorage flag cannot access workspace assistant", async ({
    page,
  }) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.goto("/workspace/assistant");
    await page.waitForURL(/\/login/, { timeout: 15_000 });
  });

  test("development server allows legacy nav when localStorage flag is set", async ({ page }) => {
    test.skip(
      process.env.NODE_ENV === "production",
      "Legacy developer nav is environment-scoped to non-production builds",
    );
    await assertBackendMode(page, "backend");
    const email = `e2e.01e.devnav.${Date.now()}@marketsynth.local`;
    const password = "e2e-01e-pass12";
    await page.goto("/register");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-display-name").fill("Dev Nav User");
    await page.getByTestId("register-password").fill(password);
    await page.getByTestId("register-password-confirm").fill(password);
    await page.getByTestId("register-notice").check();
    await page.getByTestId("register-submit").click();
    await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

    await page.evaluate((key) => {
      window.localStorage.setItem(key, "1");
    }, HOME_DEVELOPER_MODE_KEY);
    await page.reload();
    await expect(page.getByTestId("nav-workspace-assistant")).toBeVisible();
    await page.goto("/workspace/assistant");
    await expect(page.getByTestId("workspace-assistant")).toBeVisible({ timeout: 15_000 });
  });
});
