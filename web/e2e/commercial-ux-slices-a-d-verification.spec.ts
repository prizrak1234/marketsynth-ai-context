import { expect, test } from "@playwright/test";

import { fillIntakeWizard } from "./helpers/cph2";
import {
  bivLogin,
  createRunRequestTracker,
  waitForAsyncRunPost,
} from "./helpers/biv-golden-path";
import {
  assertLayoutHealthy,
  assertNoHydrationErrors,
  attachConsoleCollector,
  captureScreenshot,
  openMobileNavIfNeeded,
  setViewport,
  VIEWPORTS,
} from "./helpers/commercial-ux-verification";
import {
  bindDeterministicFixture,
  cleanupRuntime01fContext,
  loadRuntime01fContext,
  waitForTerminalUi,
} from "./helpers/runtime-01f-golden-path";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

/**
 * PRODUCT-01.4-COMMERCIAL-UX-A-D-VERIFICATION-01
 * Production-browser evidence for Slices A–D (presentation only).
 */
test.describe("Commercial UX Slices A–D verification", () => {
  test.describe.configure({ mode: "serial", timeout: 420_000 });

  let ctx: ReturnType<typeof loadRuntime01fContext>;
  let consoleErrors: string[] = [];
  let partialProjectId = "";
  let partialProjectName = "";

  test.beforeAll(() => {
    try {
      ctx = loadRuntime01fContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
  });

  test.afterAll(() => {
    if (!ctx) return;
    cleanupRuntime01fContext(ctx);
  });

  test.beforeEach(async ({ page }) => {
    if (!ctx) return;
    consoleErrors = attachConsoleCollector(page);
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
    await bivLogin(page, ctx);
  });

  test.afterEach(async () => {
    await assertNoHydrationErrors(consoleErrors);
  });

  async function seedOutcome(
    page: import("@playwright/test").Page,
    outcome: "partial" | "verdict" | "technical",
    projectName: string,
  ) {
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    bindDeterministicFixture(ctx!.runId, outcome);
    await page.goto("/workspace/projects/new");
    await page.waitForURL(/\/workspace\/projects\/new/, { timeout: 30_000 });
    await fillIntakeWizard(page, projectName);
    await expect(page.getByTestId("intake-golden-path-submit")).toBeEnabled({ timeout: 30_000 });
    await page.getByTestId("intake-golden-path-submit").click();
    await page.waitForURL(/\/workspace\?project=/, { timeout: 60_000 });
    if (outcome !== "technical") {
      await waitForAsyncRunPost(tracker, 120_000);
    }
    await waitForTerminalUi(page, outcome, 180_000);
    const projectId = new URL(page.url()).searchParams.get("project");
    expect(projectId).toBeTruthy();
    return { projectId: projectId!, tracker };
  }

  for (const [key, vp] of Object.entries(VIEWPORTS)) {
    test(`viewport matrix — workspace home (${vp.label})`, async ({ page }) => {
      await setViewport(page, key as keyof typeof VIEWPORTS);
      await page.goto("/workspace");
      await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
      await assertLayoutHealthy(page);
      await captureScreenshot(page, `01-workspace-home-${vp.label}`);
      if (key === "mobile") {
        await openMobileNavIfNeeded(page);
        await captureScreenshot(page, `01b-workspace-home-mobile-nav-${vp.label}`);
      }
    });
  }

  test("research progress — desktop capture during run", async ({ page }) => {
    await setViewport(page, "desktop");
    bindDeterministicFixture(ctx!.runId, "verdict");
    const projectName = `E2E-UXAD-Progress-${Date.now()}`;
    await page.goto("/workspace/projects/new");
    await fillIntakeWizard(page, projectName);
    await page.getByTestId("intake-golden-path-submit").click();
    await page.waitForURL(/\/workspace\?project=/, { timeout: 60_000 });
    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 60_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "02-research-progress-1440x900");
  });

  test("partial result — desktop and mobile screenshots", async ({ page }) => {
    const projectName = `E2E-UXAD-Partial-${Date.now()}`;
    const { projectId } = await seedOutcome(page, "partial", projectName);
    partialProjectId = projectId;
    partialProjectName = projectName;

    await setViewport(page, "desktop");
    await page.goto(`/workspace?project=${projectId}`);
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible({ timeout: 60_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "03-partial-result-1440x900");

    await setViewport(page, "mobile");
    await page.goto(`/workspace?project=${projectId}`);
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible({ timeout: 60_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "04-partial-result-390x844");
  });

  test("full verdict — desktop screenshot", async ({ page }) => {
    await setViewport(page, "desktop");
    const projectName = `E2E-UXAD-Verdict-${Date.now()}`;
    const { projectId } = await seedOutcome(page, "verdict", projectName);
    await page.goto(`/workspace?project=${projectId}`);
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByTestId("biv-report-hydrated")).toBeVisible();
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "05-full-verdict-1440x900");
  });

  test("research failure — desktop screenshot", async ({ page }) => {
    await setViewport(page, "desktop");
    const projectName = `E2E-UXAD-Failure-${Date.now()}`;
    await seedOutcome(page, "technical", projectName);
    await expect(page.getByTestId("biv-research-failed")).toBeVisible({ timeout: 60_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "06-research-failure-1440x900");
  });

  test("projects populated — desktop and mobile", async ({ page }) => {
    expect(partialProjectId).toBeTruthy();
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects");
    await expect(page.getByTestId("projects-list")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(partialProjectName)).toBeVisible();
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "07-projects-populated-1440x900");

    await setViewport(page, "mobile");
    await page.goto("/workspace/projects");
    await expect(page.getByTestId("projects-list")).toBeVisible({ timeout: 60_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "08-projects-populated-390x844");
  });

  test("projects loading — delayed API screenshot", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.route(/\/\/localhost:8000\/projects\/?(\?.*)?$/, async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await new Promise((r) => setTimeout(r, 1500));
      await route.continue();
    });
    await page.goto("/workspace/projects");
    const loading = page.getByTestId("projects-loading");
    await expect(loading).toBeVisible({ timeout: 10_000 });
    await captureScreenshot(page, "09-projects-loading-1440x900");
    await expect(page.getByTestId("projects-list").or(page.getByTestId("projects-empty"))).toBeVisible({
      timeout: 30_000,
    });
  });

  test("projects empty — screenshot when list is empty", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.route(/\/\/localhost:8000\/projects\/?(\?.*)?$/, async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
    await page.goto("/workspace/projects");
    await expect(page.getByTestId("projects-empty")).toBeVisible({ timeout: 30_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "10-projects-empty-1440x900");
  });

  test("golden path — partial cold restore without POST /runs", async ({ page }) => {
    expect(partialProjectId).toBeTruthy();
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    await page.addInitScript(() => {
      window.localStorage.removeItem("ms_terminal_partial_biv_research");
      window.sessionStorage.removeItem("ms_active_biv_research");
    });
    const postsBefore = tracker.asyncPosts.length;
    await page.goto(`/workspace?project=${partialProjectId}`);
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible({ timeout: 60_000 });
    expect(tracker.asyncPosts.length).toBe(postsBefore);
    await page.goto("/workspace/projects");
    await expect(page.getByText(partialProjectName)).toBeVisible({ timeout: 30_000 });
    await page.getByText(partialProjectName).click();
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible({ timeout: 60_000 });
  });
});
