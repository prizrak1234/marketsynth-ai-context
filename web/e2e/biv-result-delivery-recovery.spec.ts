import { expect, test } from "@playwright/test";

import { apiJson, fillIntakeWizard } from "./helpers/cph2";
import {
  cleanupRuntime01fContext,
  loadRuntime01fContext,
  runGoldenPathScenario,
  waitForTerminalUi,
  bindDeterministicFixture,
  fetchGoldenPathSession,
  type GoldenPathSession,
} from "./helpers/runtime-01f-golden-path";
import {
  bivLogin,
  createRunRequestTracker,
  waitForAsyncRunPost,
} from "./helpers/biv-golden-path";
import { openProjectWorkspace } from "./helpers/biv-e2e-isolation";

/**
 * PRODUCT-01.3B — BIV result delivery recovery (project hydration + Projects UI).
 */
test.describe("PRODUCT-01.3B BIV result delivery recovery", () => {
  test.describe.configure({ mode: "serial", timeout: 360_000 });

  let ctx: ReturnType<typeof loadRuntime01fContext>;

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
    await bivLogin(page, ctx);
  });

  async function seedPartialSession(
    page: import("@playwright/test").Page,
  ): Promise<GoldenPathSession & { projectName: string }> {
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    bindDeterministicFixture(ctx.runId, "partial");

    const projectName = `E2E-013B-Partial-${Date.now()}`;
    await page.goto("/workspace/projects/new");
    await page.waitForURL(/\/workspace\/projects\/new/, { timeout: 30_000 });
    await fillIntakeWizard(page, projectName);
    await expect(page.getByTestId("intake-golden-path-submit")).toBeEnabled({ timeout: 30_000 });
    await page.getByTestId("intake-golden-path-submit").click();
    await page.waitForURL(/\/workspace\?project=/, { timeout: 60_000 });
    await waitForAsyncRunPost(tracker, 120_000);
    await waitForTerminalUi(page, "partial");
    const session = await fetchGoldenPathSession(page, ctx, tracker);
    return { ...session, projectName };
  }

  test("A — partial cold restore without POST /runs", async ({ page }) => {
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    const session = await seedPartialSession(page);
    expect(session.runId).toBeTruthy();

    await page.addInitScript(() => {
      window.localStorage.removeItem("ms_terminal_partial_biv_research");
      window.sessionStorage.removeItem("ms_active_biv_research");
    });
    const postsBefore = tracker.asyncPosts.length;

    await page.goto(`/workspace?project=${session.projectId}`);
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
    await waitForTerminalUi(page, "partial");

    expect(tracker.asyncPosts.length).toBe(postsBefore);

    const latestRun = await apiJson<{ run_id: string; status: string; result_kind?: string }>(
      page,
      ctx,
      "GET",
      `/projects/${session.projectId}/business-idea-validation/latest-run`,
    );
    expect(latestRun.run_id).toBe(session.runId);
    expect(latestRun.status).toBe("failed");
    expect(latestRun.result_kind).toBe("partial_research");
  });

  test("B — Projects navigation shows lifecycle label and deep link", async ({ page }) => {
    const session = await seedPartialSession(page);

    await page.goto("/workspace/projects");
    await expect(page.getByTestId("workspace-projects-list")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("projects-list")).toBeVisible({ timeout: 30_000 });

    const item = page.getByTestId("projects-list-item").filter({
      hasText: session.projectName,
    });
    await expect(item.first()).toBeVisible({ timeout: 15_000 });
    await expect(item.first()).toContainText("Результат ограничен данными");
    await expect(item.first()).not.toContainText("Backend project");

    await item.first().click();
    await expect(page).toHaveURL(new RegExp(`project=${session.projectId}`));
    await waitForTerminalUi(page, "partial");
  });

  test("C — latest-run 500 shows recoverable error without intake fallback", async ({ page }) => {
    const session = await seedPartialSession(page);

    await page.route("**/business-idea-validation/latest-run", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "simulated hydration failure" }),
      });
    });

    await page.addInitScript(() => {
      window.localStorage.removeItem("ms_terminal_partial_biv_research");
      window.sessionStorage.removeItem("ms_active_biv_research");
    });

    const tracker = createRunRequestTracker();
    tracker.attach(page);
    await openProjectWorkspace(page, session.projectId);

    await expect(page.getByTestId("biv-research-failed")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("biv-partial-research-panel")).toHaveCount(0);
    await expect(page.getByTestId("intake-golden-path-submit")).toHaveCount(0);
    expect(tracker.asyncPosts.length).toBe(0);

    const failureText = await page.getByTestId("biv-research-failed").innerText();
    expect(failureText.toLowerCase()).not.toMatch(/traceback|api_key|secret|password/);
  });

  test("D — full success cold restore regression", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "013B-D-verdict",
      outcome: "verdict",
      projectName: `E2E-013B-Verdict-${Date.now()}`,
      verifyRestore: true,
    });
    expect(evidence.terminalStatus).toBe("succeeded");
    expect(evidence.restoreVerified).toBe(true);
  });

  test("E — technical failure cold restore regression", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "013B-E-technical",
      outcome: "technical",
      projectName: `E2E-013B-Technical-${Date.now()}`,
      verifyRestore: true,
    });
    expect(evidence.terminalStatus).toBe("failed");
    expect(evidence.restoreVerified).toBe(true);
  });

  test("F — active running restore regression", async ({ page }) => {
    const evidence = await runGoldenPathScenario(page, ctx, {
      scenario: "013B-F-running",
      outcome: "verdict",
      projectName: `E2E-013B-Running-${Date.now()}`,
      verifyRunningRefresh: true,
    });
    expect(evidence.asyncRunCalls).toBe(1);
    expect(evidence.refreshVerified).toBe(true);
  });

  test("G — incident regression: project latest-run/latest return 200 for partial", async ({
    page,
  }) => {
    const session = await seedPartialSession(page);

    const latestRun = await apiJson<{
      run_id: string;
      status: string;
      has_output: boolean;
      result_kind?: string;
    }>(
      page,
      ctx,
      "GET",
      `/projects/${session.projectId}/business-idea-validation/latest-run`,
    );
    expect(latestRun.run_id).toBe(session.runId);
    expect(latestRun.has_output).toBe(true);
    expect(latestRun.result_kind).toBe("partial_research");

    const latest = await apiJson<{ run_id: string; output?: { result_kind?: string } }>(
      page,
      ctx,
      "GET",
      `/projects/${session.projectId}/business-idea-validation/latest`,
    );
    expect(latest.run_id).toBe(session.runId);
    expect(latest.output?.result_kind).toBe("partial_research");
  });
});
