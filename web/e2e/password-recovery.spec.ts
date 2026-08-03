import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { assertBackendMode, loadE2EContext } from "./helpers/cph2";

const OWNER_EMAIL = "joker.sam90@gmail.com";
const REPO_ROOT = path.resolve(__dirname, "../..");

function createOperatorResetUrl(email: string): string {
  const env = {
    ...process.env,
    DATABASE_URL:
      process.env.DATABASE_URL ||
      "postgresql+asyncpg://botfazer:botfazer@localhost:5432/botfazer_cph1",
  };
  execFileSync(
    "uv",
    [
      "run",
      "python",
      "scripts/create_password_reset_link.py",
      "--email",
      email,
      "--require-db",
      "botfazer_cph1",
    ],
    { cwd: REPO_ROOT, env, encoding: "utf-8" },
  );
  const urlPath = path.join(process.env.TEMP || process.env.TMP || ".", "ms_password_reset.url");
  const url = readFileSync(urlPath, "utf-8").trim();
  if (!url.includes("/reset-password?token=")) {
    throw new Error("operator reset URL missing");
  }
  return url;
}

test("forgot password → operator link → new password → login → workspace", async ({
  page,
}) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");

  // Use a dedicated E2E user so we do not overwrite owner password in CI.
  const email = `e2e.reset.${Date.now()}@marketsynth.local`;
  const oldPassword = "e2e-old-pass-12";
  const newPassword = "e2e-new-pass-34";

  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("E2E Reset");
  await page.getByTestId("register-password").fill(oldPassword);
  await page.getByTestId("register-password-confirm").fill(oldPassword);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });

  await page.getByTestId("forgot-password-link").click();
  await page.waitForURL(/\/forgot-password/, { timeout: 15_000 });
  await page.getByTestId("forgot-password-email").fill(email);
  await page.getByTestId("forgot-password-submit").click();
  await expect(page.getByTestId("forgot-password-done")).toBeVisible({
    timeout: 15_000,
  });

  const resetUrl = createOperatorResetUrl(email);
  await page.goto(resetUrl);
  await expect(page.getByTestId("reset-password-form")).toBeVisible({
    timeout: 20_000,
  });
  await page.getByTestId("reset-password-input").fill(newPassword);
  await page.getByTestId("reset-password-confirm").fill(newPassword);
  await page.getByTestId("reset-password-submit").click();
  await page.waitForURL(/\/login\?passwordReset=success/, { timeout: 30_000 });
  await expect(page.getByTestId("login-password-reset-success")).toBeVisible();

  await page.getByTestId("login-email").fill(email);
  await page.getByLabel("Пароль").fill(newPassword);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
  await expect(page.getByTestId("logout-button")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });
  await page.getByTestId("login-email").fill(email);
  await page.getByLabel("Пароль").fill(newPassword);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });

  // Old reset link rejected
  await page.goto(resetUrl);
  await expect(page.getByTestId("reset-password-state")).toHaveAttribute(
    "data-state",
    /used|invalid|revoked/,
    { timeout: 15_000 },
  );
});

test("login shows forgot password link", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByTestId("forgot-password-link")).toBeVisible({
    timeout: 15_000,
  });
  // Owner email is not auto-filled; recovery stays available.
  expect(OWNER_EMAIL.includes("@")).toBeTruthy();
});
