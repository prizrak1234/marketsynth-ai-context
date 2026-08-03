/**
 * Controlled Pilot Readiness Gate — mandatory manual login characterization.
 * Runs against page.request origin (Playwright baseURL) and optionally alias.
 */
import { expect, test } from "@playwright/test";
import { loadE2EContext } from "./helpers/cph2";

const ALIAS = "http://127.0.0.1:3000";

async function runLoginMatrix(page: import("@playwright/test").Page, origin: string) {
  await page.goto(`${origin}/login?next=%2Fworkspace`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await expect(page.getByText(/Неверный логин или пароль/i)).toHaveCount(0);

  await page.getByLabel("Email").fill("nobody@marketsynth.local");
  await page.getByLabel("Пароль").fill("wrong-password-xx");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("login-error")).toHaveAttribute(
    "data-error-kind",
    "invalid_credentials",
  );

  const ctx = loadE2EContext();
  await page.goto(`${origin}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Email").fill(ctx.email);
  await page.getByLabel("Пароль").fill(ctx.password);
  await page.getByTestId("login-submit").click();
  await page.waitForURL(/\/workspace/, { timeout: 60_000 });

  const cookies = await page.context().cookies();
  const session = cookies.find((c) => c.name === "ms_pilot_session");
  expect(session, "ms_pilot_session cookie").toBeTruthy();
  expect(session!.httpOnly).toBeTruthy();
  expect(session!.secure).toBeFalsy(); // local HTTP

  await page.reload({ waitUntil: "networkidle" });
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });
  await page.goto(`${origin}/workspace`);
  await page.waitForURL(/\/login/, { timeout: 30_000 });
}

test("GATE canonical localhost login matrix", async ({ page }) => {
  loadE2EContext();
  await runLoginMatrix(page, "http://localhost:3000");
});

test("GATE 127.0.0.1 alias login matrix", async ({ browser }) => {
  loadE2EContext();
  const context = await browser.newContext({ baseURL: ALIAS });
  const page = await context.newPage();
  try {
    await runLoginMatrix(page, ALIAS);
  } finally {
    await context.close();
  }
});
