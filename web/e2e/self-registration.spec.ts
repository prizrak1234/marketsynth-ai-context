import { expect, test } from "@playwright/test";
import { assertBackendMode, loadE2EContext } from "./helpers/cph2";

test("register unique member → workspace → refresh → logout → login", async ({
  page,
}) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  const email = `e2e.reg.${Date.now()}@marketsynth.local`;
  const password = "e2e-reg-pass-12";

  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("E2E Member");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });

  const apiKey = await page.evaluate(() =>
    window.localStorage.getItem("marketsynth.e2e.api_key.v1"),
  );
  expect(apiKey).toBeNull();

  await page.reload();
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });

  await page.getByTestId("login-email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
});

test("duplicate registration shows conflict", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  const email = `e2e.dup.${Date.now()}@marketsynth.local`;
  const password = "e2e-dup-pass-12";

  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("One");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });

  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Two");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await expect(page.getByTestId("register-error")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("register-error")).toHaveAttribute(
    "data-error-code",
    "email_taken",
  );
  await expect(page.getByTestId("register-duplicate-login")).toBeVisible();
  await expect(page.getByTestId("register-duplicate-reset")).toBeVisible();
  await page.getByTestId("register-duplicate-reset").click();
  await page.waitForURL(/\/forgot-password/, { timeout: 15_000 });
  await expect(page.getByTestId("forgot-password-form")).toBeVisible();
});

test("login shows register when signup enabled", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByTestId("register-link")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("activate-invite-link")).toBeVisible();
});
