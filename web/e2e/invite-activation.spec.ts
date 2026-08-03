import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import path from "node:path";
import {
  assertBackendMode,
  loadE2EContext,
} from "./helpers/cph2";

const ROOT = path.resolve(__dirname, "../..");

function createInvite(email: string): string {
  const out = execFileSync(
    "uv",
    [
      "run",
      "python",
      "scripts/create_pilot_invite.py",
      "--email",
      email,
      "--ttl-hours",
      "24",
      "--replace",
      "--require-db",
      "botfazer_cph1",
    ],
    {
      cwd: ROOT,
      encoding: "utf-8",
      env: process.env,
    },
  );
  const urlFile = path.join(process.env.TEMP || process.env.TMP || "", "ms_pilot_invite.url");
  if (!fs.existsSync(urlFile)) {
    throw new Error(`activation url file missing after invite create.\n${out}`);
  }
  const url = fs.readFileSync(urlFile, "utf-8").trim();
  if (!url.includes("?token=mpi_")) {
    throw new Error("activation URL missing token query");
  }
  return url;
}

test("pilot invite activation → workspace → refresh → logout → login", async ({
  page,
}) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");

  const email = `e2e.invite.${Date.now()}@marketsynth.local`;
  const password = "e2e-invite-pass-1";
  const url = createInvite(email);

  await page.goto(url);
  await expect(page.getByTestId("invite-form")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("invite-email")).toHaveValue(email);
  await page.getByTestId("invite-display-name").fill("E2E Invitee");
  await page.getByTestId("invite-password").fill(password);
  await page.getByTestId("invite-password-confirm").fill(password);
  await page.getByTestId("invite-notice").check();
  await page.getByTestId("invite-submit").click();
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

  await page.goto("/login");
  await expect(page.getByTestId("activate-invite-link")).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 30_000 });
  await expect(page.getByTestId("logout-button")).toBeVisible();
});

test("bare activate-invite shows token entry not invalid", async ({ page }) => {
  await page.goto("/activate-invite");
  await expect(page.getByTestId("invite-token-entry")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("invite-token-entry")).toHaveAttribute(
    "data-invite-state",
    "token_missing",
  );
  await expect(page.getByText(/недействительн/i)).toHaveCount(0);
  await expect(
    page.getByText(/одноразовая ссылка или код от оператора/i),
  ).toBeVisible();
});

test("paste token on bare page unlocks status check", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  const email = `e2e.paste.${Date.now()}@marketsynth.local`;
  const url = createInvite(email);
  const token = new URL(url).searchParams.get("token");
  expect(token).toBeTruthy();

  await page.goto("/activate-invite");
  await page.getByTestId("invite-token-input").fill(token!);
  await page.getByTestId("invite-token-continue").click();
  await expect(page.getByTestId("invite-form")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("invite-email")).toHaveValue(email);
});

test("login page links invite activation without free signup", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByTestId("activate-invite-link")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("activate-invite-hint")).toBeVisible();
  await expect(page.getByRole("link", { name: /Свободная регистрация/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Зарегистрироваться/i })).toHaveCount(0);
  await expect(page.getByText(/Активировать приглашение/i)).toBeVisible();
  await expect(page.getByText(/отключена/i)).toBeVisible();
});
