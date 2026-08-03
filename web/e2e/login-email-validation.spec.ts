import { expect, test } from "@playwright/test";
import { assertBackendMode, loadE2EContext, loginViaUi } from "./helpers/cph2";

test("incomplete email blocked before API login", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login");
  await page.getByTestId("login-email").fill("joker.sam90");
  await page.getByLabel("Пароль").fill("some-password-xx");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("login-email-error")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("login-email-error")).toContainText(/полный email/i);
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await expect(page).toHaveURL(/\/login/);
});

test("uppercase email normalizes and login succeeds", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login");
  await page.getByTestId("login-email").fill(ctx.email.toUpperCase());
  await page.getByLabel("Пароль").fill(ctx.password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 60_000 });
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });
});

test("whitespace around email trims on submit", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login");
  await page.getByTestId("login-email").fill(`  ${ctx.email}  `);
  await page.getByLabel("Пароль").fill(ctx.password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 60_000 });
});

test("client error clears when email field changes", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login");
  await page.getByTestId("login-email").fill("joker.sam90");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("login-email-error")).toBeVisible();
  await page.getByTestId("login-email").fill("joker.sam90@gmail.com");
  await expect(page.getByTestId("login-email-error")).toHaveCount(0);
});

test("full normalized email login refresh and logout", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  await page.reload();
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });
});
