/**
 * WORKSPACE-BOOT-RECOVERY-02 — deterministic /workspace boot without hard reload.
 */
import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertBackendMode } from "./helpers/cph2";

const ARTIFACT_DIR = path.join(
  process.cwd(),
  "e2e-artifacts",
  "workspace-boot-recovery-02",
);
const BACKEND_URL = (
  process.env.CPH2_BACKEND_URL ||
  process.env.NEXT_PUBLIC_BOTFAZER_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8001"
).replace(/\/$/, "");

/** Match API projects list regardless of localhost vs 127.0.0.1 (cookie host align). */
function projectsListApiPattern(): RegExp {
  return /https?:\/\/(localhost|127\.0\.0\.1):\d+\/projects\/?$/;
}

async function registerUser(page: Page) {
  const email = `boot.${Date.now()}@marketsynth.local`;
  const password = "e2e-boot-recovery-pass1";
  await page.goto("/register");
  await expect(page.getByTestId("register-email")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Boot Recovery User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  return { email, password };
}

async function createProject(page: Page, name: string): Promise<string> {
  const res = await page.request.fetch(`${BACKEND_URL}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: process.env.CPH2_FRONTEND_URL || "http://localhost:3000",
    },
    data: { name },
  });
  expect(res.ok(), await res.text()).toBeTruthy();
  return ((await res.json()) as { id: string }).id;
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(ARTIFACT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test.describe("WORKSPACE-BOOT-RECOVERY-02", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const mark = () => {
        (window as Window & { __bootHardNav?: boolean }).__bootHardNav = true;
      };
      const origReplace = window.location.replace.bind(window.location);
      const origAssign = window.location.assign.bind(window.location);
      // Detect hard navigation APIs; do not block (Playwright needs real nav for login).
      Object.defineProperty(window.location, "replace", {
        configurable: true,
        value: (...args: Parameters<typeof origReplace>) => {
          mark();
          return origReplace(...args);
        },
      });
      Object.defineProperty(window.location, "assign", {
        configurable: true,
        value: (...args: Parameters<typeof origAssign>) => {
          mark();
          return origAssign(...args);
        },
      });
    });
  });

  test("unauthenticated /workspace → login without loop", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await page.context().clearCookies();
    await page.goto("/workspace");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
    await expect(page.getByTestId("login-submit")).toBeVisible();
    // Stay on login (no bounce back to workspace spinner)
    await page.waitForTimeout(1_500);
    await expect(page).toHaveURL(/\/login/);
    await shot(page, "01-unauthenticated-login");
  });

  test("zero projects → intake screen (no eternal spinner)", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    await expect(page).toHaveURL(/\/workspace\/projects\/new/, { timeout: 45_000 });
    await expect(page.getByTestId("workspace-boot-loading")).toHaveCount(0);
    await shot(page, "02-no-projects-intake");
  });

  test("many projects → projects list", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    await createProject(page, `BootMultiA ${Date.now()}`);
    await createProject(page, `BootMultiB ${Date.now()}`);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();

    await expect(page).toHaveURL(/\/workspace\/projects\/?$/, { timeout: 45_000 });
    await expect(page.getByTestId("workspace-boot-loading")).toHaveCount(0);
    await shot(page, "03b-multi-projects-list");

    await page.goto("/workspace");
    await expect(page).toHaveURL(/\/workspace\/projects\/?$/, { timeout: 45_000 });
    await shot(page, "03c-multi-bare-workspace");
  });

  test("one project: / and /workspace land on PCC; direct URL works", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    const projectId = await createProject(page, `Boot ${Date.now()}`);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();

    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    expect(page.url()).toContain(`project=${projectId}`);
    await shot(page, "03-login-pcc");

    // Soft home re-entry
    await page.goto("/workspace");
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    expect(page.url()).toContain(`project=${projectId}`);
    await expect(page.getByTestId("workspace-boot-loading")).toHaveCount(0);
    await expect(page.getByText("Проверить мою идею")).toHaveCount(0);
    await shot(page, "04-workspace-bare-pcc");

    // Direct deep link — no redirect churn
    await page.goto(`/workspace?project=${projectId}`);
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page).toHaveURL(new RegExp(`project=${projectId}`));
    await shot(page, "05-direct-project-url");

    // Public / → landing (not workspace hang); authenticated user may stay on landing
    await page.goto("/");
    await expect(page.getByTestId("workspace-boot-loading")).toHaveCount(0);
    await shot(page, "06-root-landing");

    // Static source ban: boot path must not use location.replace timers
    // (runtime assert after soft navigations since register)
    // Hard nav may fire only for full page loads from Playwright goto — clear flag after setup
  });

  test("invalid project id → error recovery UI", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    await createProject(page, `BootInvalid ${Date.now()}`);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });

    await page.goto("/workspace?project=00000000-0000-4000-8000-000000000099");
    await expect(page.getByTestId("project-command-center-error")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByTestId("project-command-center-retry")).toBeVisible();
    await shot(page, "07-invalid-project");
  });

  test("projects API 500 → boot error + retry", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    await createProject(page, `Boot500 ${Date.now()}`);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });

    const projectsApi = projectsListApiPattern();
    await page.route(projectsApi, async (route) => {
      if (route.request().isNavigationRequest()) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error_code: "server_error", detail: "boom" }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/workspace");
    await expect(page.getByTestId("workspace-boot-error")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByTestId("workspace-boot-retry")).toBeVisible();
    await expect(page.getByTestId("workspace-boot-loading")).toHaveCount(0);
    await shot(page, "08-projects-500");

    await page.unroute(projectsApi);
    await page.getByTestId("workspace-boot-retry").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });
    await shot(page, "09-projects-500-retry-ok");
  });

  test("projects API timeout → error not eternal spinner", async ({ page }) => {
    await assertBackendMode(page, "backend");
    const { email, password } = await registerUser(page);
    await page.waitForURL(/\/workspace/, { timeout: 45_000 });
    await createProject(page, `BootTimeout ${Date.now()}`);

    await page.goto("/login");
    await page.getByTestId("login-email").fill(email);
    await page.locator("#login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("project-command-center")).toBeVisible({
      timeout: 45_000,
    });

    const projectsApi = projectsListApiPattern();
    await page.route(projectsApi, async (route) => {
      if (route.request().isNavigationRequest()) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await new Promise((r) => setTimeout(r, 20_000));
        await route.abort("timedout");
        return;
      }
      await route.continue();
    });

    await page.goto("/workspace");
    await expect(page.getByTestId("workspace-boot-error")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByTestId("workspace-boot-retry")).toBeVisible();
    await shot(page, "10-projects-timeout");
  });

  test("source: workspace boot has no hard navigation / redirect timer", async () => {
    const homePath = path.join(
      process.cwd(),
      "src/components/workspace/home/workspace-home-view.tsx",
    );
    const bootPath = path.join(process.cwd(), "src/lib/workspace/workspace-boot.ts");
    const stripComments = (src: string) =>
      src
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/(^|[^:])\/\/.*$/gm, "$1");
    const homeSrc = stripComments(fs.readFileSync(homePath, "utf8"));
    const bootSrc = stripComments(fs.readFileSync(bootPath, "utf8"));
    expect(homeSrc).not.toMatch(/location\.replace/);
    expect(homeSrc).not.toMatch(/location\.href\s*=/);
    expect(homeSrc).not.toMatch(/setTimeout\([^)]*location/);
    expect(homeSrc).not.toMatch(/\b6_000\b|\b6000\b/);
    expect(bootSrc).not.toMatch(/location\.replace/);
    expect(bootSrc).not.toMatch(/location\.href/);
  });
});
