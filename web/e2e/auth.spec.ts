import { expect, test } from "@playwright/test";
import {
  apiUnauthJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
} from "./helpers/cph2";

test("login page initially has no error", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login?next=%2Fworkspace");
  await expect(page.getByTestId("login-submit")).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(1000);
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await expect(page.getByText(/Неверный логин или пароль/i)).toHaveCount(0);
});

test("login success + session survives refresh", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  await page.reload();
  await expect(page.getByTestId("logout-button")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(ctx.email.split("@")[0], { exact: false }).first()).toBeVisible();
});

test("login failure shows safe error only after submit", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/login");
  await expect(page.getByTestId("login-error")).toHaveCount(0);
  await page.getByLabel("Email").fill("nobody@marketsynth.local");
  await page.getByLabel("Пароль").fill("wrong-password-xx");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("login-error")).toHaveAttribute(
    "data-error-kind",
    "invalid_credentials",
  );
  await expect(page.getByText(/Неверный логин или пароль/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("logout invalidates session and redirects", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  await page.getByTestId("logout-button").click();
  await page.waitForURL(/\/login/, { timeout: 30_000 });
  await page.goto("/workspace");
  await page.waitForURL(/\/login/, { timeout: 30_000 });
});

test("unauthenticated workspace redirects to login without credentials error", async ({
  page,
}) => {
  loadE2EContext();
  await assertBackendMode(page, "backend");
  await page.goto("/workspace");
  await page.waitForURL(/\/login/, { timeout: 30_000 });
  await page.waitForTimeout(800);
  await expect(page.getByTestId("login-error")).toHaveCount(0);
});

test("unauthenticated API rejected", async ({ request }) => {
  const ctx = loadE2EContext();
  const res = await apiUnauthJson(request, ctx, "GET", "/auth/me");
  expect(res.status).toBe(401);
});

test("no permanent API key in localStorage after login", async ({ page }) => {
  const ctx = loadE2EContext();
  await assertBackendMode(page, "backend");
  await loginViaUi(page, ctx);
  const key = await page.evaluate(() =>
    window.localStorage.getItem("marketsynth.e2e.api_key.v1"),
  );
  expect(key).toBeNull();
});

test("user A cannot open user B project by URL", async ({ browser }) => {
  const ctx = loadE2EContext();
  if (!ctx.emailB || !ctx.passwordB) {
    test.skip();
    return;
  }
  const pageA = await browser.newPage();
  const pageB = await browser.newPage();
  await assertBackendMode(pageA, "backend");
  await assertBackendMode(pageB, "backend");

  await pageB.goto("/login");
  await pageB.getByLabel("Email").fill(ctx.emailB);
  await pageB.getByLabel("Пароль").fill(ctx.passwordB);
  await pageB.getByTestId("login-submit").click();
  await pageB.waitForURL(/\/workspace/, { timeout: 60_000 });
  const created = await pageB.request.post(`${ctx.backendUrl}/projects`, {
    data: { name: `E2E-B-${ctx.runId}`, description: "iso" },
    headers: { Origin: ctx.frontendUrl, "Content-Type": "application/json" },
  });
  expect(created.ok()).toBeTruthy();
  const projectId = (await created.json()).id as string;

  await pageA.goto("/login");
  await pageA.getByLabel("Email").fill(ctx.email);
  await pageA.getByLabel("Пароль").fill(ctx.password);
  await pageA.getByTestId("login-submit").click();
  await pageA.waitForURL(/\/workspace/, { timeout: 60_000 });
  await pageA.goto(`/workspace/projects/${projectId}/investigation`);
  await expect(
    pageA.getByText(/не найден|Not found|нет|Mock не подставляется|недоступ|blocked|404/i).first(),
  ).toBeVisible({ timeout: 30_000 });
  await pageA.close();
  await pageB.close();
});
