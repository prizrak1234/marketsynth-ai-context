import { expect, type APIRequestContext, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

export type E2ERunContext = {
  runId: string;
  projectPrefix: string;
  backendUrl: string;
  frontendUrl: string;
  email: string;
  password: string;
  emailB?: string;
  passwordB?: string;
  mode: string;
  artifactDir: string;
};

export function loadE2EContext(): E2ERunContext {
  const runId = process.env.CPH2_RUN_ID || process.env.CPH3_RUN_ID || `r${Date.now()}`;
  const backendUrl = (process.env.CPH2_BACKEND_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  );
  const frontendUrl = (process.env.CPH2_FRONTEND_URL || "http://localhost:3000").replace(
    /\/$/,
    "",
  );
  const email = process.env.CPH3_E2E_EMAIL || "";
  const password = process.env.CPH3_E2E_PASSWORD || "";
  if (!email || !password) {
    throw new Error("CPH3_E2E_EMAIL / CPH3_E2E_PASSWORD required (no API-key shortcut)");
  }
  const mode =
    process.env.NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE ||
    process.env.CPH2_INTEGRATION_MODE ||
    "backend";
  if (mode === "mock") {
    throw new Error("E2E refused: integration mode is mock");
  }
  const artifactDir = path.join(
    process.cwd(),
    "test-results",
    "cph3-lineage",
    runId,
  );
  fs.mkdirSync(artifactDir, { recursive: true });
  return {
    runId,
    projectPrefix: `E2E-PILOT-${runId}`,
    backendUrl,
    frontendUrl,
    email,
    password,
    emailB: process.env.CPH3_E2E_EMAIL_B,
    passwordB: process.env.CPH3_E2E_PASSWORD_B,
    mode,
    artifactDir,
  };
}

/** CPH.3: set integration mode only — never inject API keys into localStorage. */
export async function assertBackendMode(page: Page, mode: string): Promise<void> {
  await page.addInitScript(
    ({ m, legacyKey }) => {
      window.localStorage.setItem("marketsynth.integration.mode.v1", m);
      window.localStorage.removeItem(legacyKey);
    },
    { m: mode, legacyKey: "marketsynth.e2e.api_key.v1" },
  );
}

export async function loginViaUi(page: Page, ctx: E2ERunContext): Promise<void> {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  if (/\/workspace/.test(page.url())) {
    return;
  }
  await expect(page.getByRole("heading", { name: /Вход в пилот/i })).toBeVisible({
    timeout: 30_000,
  });
  const submit = page.getByTestId("login-submit");
  await expect(submit).toBeVisible({ timeout: 30_000 });
  await expect(submit).toBeEnabled({ timeout: 30_000 });
  await page.getByLabel("Email").fill(ctx.email);
  await page.getByLabel("Пароль").fill(ctx.password);
  await submit.click();
  await page.waitForURL(/\/workspace/, { timeout: 60_000 });
  // Guard: no permanent API key left in localStorage
  const legacy = await page.evaluate(() =>
    window.localStorage.getItem("marketsynth.e2e.api_key.v1"),
  );
  expect(legacy).toBeNull();
}

/** Align loopback API host with frontend so HttpOnly session cookies are sent. */
function alignedBackendOrigin(ctx: E2ERunContext): string {
  try {
    const front = new URL(ctx.frontendUrl);
    const back = new URL(ctx.backendUrl);
    const loopback = (h: string) => h === "localhost" || h === "127.0.0.1";
    if (loopback(front.hostname) && loopback(back.hostname) && front.hostname !== back.hostname) {
      back.hostname = front.hostname;
    }
    return back.origin;
  } catch {
    return ctx.backendUrl;
  }
}

/** Cookie-authenticated API call (shares browser context after UI login). */
export async function apiJson<T>(
  page: Page,
  ctx: E2ERunContext,
  method: string,
  urlPath: string,
  body?: unknown,
): Promise<T> {
  const res = await page.request.fetch(`${alignedBackendOrigin(ctx)}${urlPath}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Origin: ctx.frontendUrl,
    },
    data: body,
  });
  if (!res.ok()) {
    throw new Error(`${method} ${urlPath} → ${res.status()} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

/** Unauthenticated probe (no cookies). */
export async function apiUnauthJson(
  request: APIRequestContext,
  ctx: E2ERunContext,
  method: string,
  urlPath: string,
): Promise<{ status: number; body: string }> {
  const res = await request.fetch(`${ctx.backendUrl}${urlPath}`, {
    method,
    headers: { "Content-Type": "application/json" },
  });
  return { status: res.status(), body: await res.text() };
}

export async function writeLineage(
  ctx: E2ERunContext,
  lineage: Record<string, unknown>,
): Promise<void> {
  const file = path.join(ctx.artifactDir, "lineage.json");
  fs.writeFileSync(
    file,
    JSON.stringify({ runId: ctx.runId, ...lineage }, null, 2),
    "utf8",
  );
}

export async function fillIntakeWizard(page: Page, projectName: string): Promise<void> {
  await page.goto("/workspace/projects/new");
  await expect(page.getByRole("heading", { name: /Проверка идеи перед исследованием/i })).toBeVisible();

  await page.locator("#name").fill(projectName);
  await page
    .locator("#ideaDescription")
    .fill("Проверить локальную клинику на устойчивость спроса до запуска рекламы");
  await page.locator("#businessType").selectOption("local_business");
  await page.locator("#projectStage").selectOption("preparing_launch");
  await page.locator("#geography").fill("Москва");
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/idea/);

  await expect(page.getByRole("heading", { name: "Продукт или услуга" })).toBeVisible();
  await page.locator("#whatIsSold").fill("Стоматологические услуги для взрослых");
  await page.locator("#primaryProblem").fill("Пациенты откладывают лечение из-за страха и цены");
  await page.locator("#valueProposition").fill("Прозрачный прайс и бережное лечение");
  await page.locator("#deliveryModel").fill("clinic");
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/market/);

  await expect(page.getByRole("heading", { name: "Рынок и конкуренция" })).toBeVisible();
  await page.locator("#targetMarket").fill("Взрослые пациенты в Москве");
  await page.locator("#competitorsUnknown").check();
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/audience/);

  await expect(page.getByRole("heading", { name: "Целевая аудитория" })).toBeVisible();
  const seg = page.locator('[id^="seg-label-"]').first();
  await seg.fill("Владельцы клиник 1–3 кресла");
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/economics/);

  await expect(page.getByRole("heading", { name: "Экономика и ограничения" })).toBeVisible();
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/materials/);

  await expect(page.getByRole("heading", { name: "Материалы" })).toBeVisible();
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/review/);

  await expect(page.getByTestId("intake-readiness-chip")).toBeVisible({ timeout: 20_000 });
}

export async function captureStep(
  page: Page,
  ctx: E2ERunContext,
  name: string,
): Promise<void> {
  await page.screenshot({
    path: path.join(ctx.artifactDir, `${name}.png`),
    fullPage: true,
  });
}
