import { expect, test } from "@playwright/test";
import {
  appendIsolationLog,
  cleanupBivE2eRun,
  countProjects,
  createIsolatedTestProject,
  openProjectWorkspace,
  provisionBivE2eRun,
} from "./helpers/biv-e2e-isolation";
import {
  assertIntakeAutofillSemantics,
  bivLogin,
  captureUserRequestId,
  confirmIntake,
  createRunRequestTracker,
  fillMinimalIntake,
  getLatestRunMeta,
  loadBivContext,
  saveScenarioArtifact,
  waitForCustomerReportReady,
  waitForReport,
  waitForRunMeta,
  waitForRunPost,
  waitForRunSucceeded,
  stubTerminalResearchRun,
} from "./helpers/biv-golden-path";

/**
 * LEGACY REGRESSION — short BIV intake on workspace (sync POST .../run).
 * Canonical commercial PASS: runtime-01f-canonical-golden-path.spec.ts (async POST .../runs).
 */
test.describe("BIV golden path [legacy sync /run regression]", () => {
  test.describe.configure({ mode: "serial", timeout: 2_400_000 });

  const idea =
    "SaaS для автоматизации отчётности малого бизнеса с подпиской от 990 ₽/мес";

  let ctx: ReturnType<typeof loadBivContext>;
  let tracker = createRunRequestTracker();
  let projectsBeforeSuite = 0;

  let ghProjectId: string | undefined;
  let ghUserRequestId: string | undefined;
  let ghRunId: string | undefined;
  const inFlightUserRequestIds: string[] = [];

  test.beforeAll(() => {
    const runId = process.env.BIV_STABILIZATION_RUN_ID || `biv-${Date.now()}`;
    process.env.BIV_STABILIZATION_RUN_ID = runId;
    process.env.CPH2_RUN_ID = runId;
    process.env.CPH3_RUN_ID = runId;

    const provision = provisionBivE2eRun(runId);
    process.env.CPH3_E2E_EMAIL = provision.email;
    process.env.CPH3_E2E_PASSWORD = provision.password ?? "";

    try {
      ctx = loadBivContext();
      appendIsolationLog(ctx.artifactDir, provision);
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
  });

  test.afterAll(() => {
    if (!ctx) return;
    const runId = ctx.runId;
    const cleanup = cleanupBivE2eRun(runId, { dryRun: false });
    appendIsolationLog(ctx.artifactDir, cleanup);
  });

  test.beforeEach(async ({ page }) => {
    if (!ctx) return;
    await page.unrouteAll({ behavior: "ignoreErrors" });
    tracker = createRunRequestTracker();
    tracker.attach(page);
    await bivLogin(page, ctx);
    if (projectsBeforeSuite === 0) {
      projectsBeforeSuite = await countProjects(page, ctx);
    }
  });

  test("A — budget + intake autofill semantics in Chromium", async ({ page }) => {
    const project = await createIsolatedTestProject(page, ctx, "A");
    await fillMinimalIntake(page, idea, { projectId: project.projectId });
    await assertIntakeAutofillSemantics(page);

    const budget = page.getByTestId("intake-budget");
    await budget.fill("500000");
    await budget.focus();
    await budget.blur();
    await expect(budget).toHaveValue("500000");
    await expect(budget).not.toHaveValue(/@/);

    await saveScenarioArtifact(ctx, { scenario: "A-budget-autofill", payload: { project_id: project.projectId } }, page);
  });

  test("B — confirm once → one POST → one run_id", async ({ page }) => {
    stubTerminalResearchRun(page);
    const project = await createIsolatedTestProject(page, ctx, "B");
    await fillMinimalIntake(page, idea, { projectId: project.projectId });
    await confirmIntake(page);

    await waitForRunPost(tracker);
    expect(tracker.posts.length).toBe(1);
    expect(new Set(tracker.idempotencyKeys).size).toBe(1);

    const userRequestId = await captureUserRequestId(page, ctx, tracker);
    expect(userRequestId).toBeTruthy();

    await saveScenarioArtifact(
      ctx,
      {
        scenario: "B-one-post",
        post_count: tracker.posts.length,
        idempotency_key: tracker.idempotencyKeys[0],
        user_request_id: userRequestId,
        payload: { project_id: project.projectId, stubbed_run: true },
      },
      page,
    );
  });

  test("C — double confirm click → still one POST", async ({ page }) => {
    stubTerminalResearchRun(page);
    const project = await createIsolatedTestProject(page, ctx, "C");
    await fillMinimalIntake(page, `${idea} — double click guard`, { projectId: project.projectId });
    const postsBefore = tracker.posts.length;
    await page.evaluate(() => {
      const form = document.querySelector(
        '[data-testid="analysis-intake-panel"]',
      ) as HTMLFormElement | null;
      form?.requestSubmit();
      form?.requestSubmit();
    });
    await waitForRunPost(tracker, 120_000);
    expect(tracker.posts.length - postsBefore).toBe(1);
    await saveScenarioArtifact(ctx, { scenario: "C-double-click", post_count: tracker.posts.length }, page);
  });

  test("D — refresh during running resumes same run", async ({ page }) => {
    const project = await createIsolatedTestProject(page, ctx, "D");
    await fillMinimalIntake(page, `${idea} — refresh running`, { projectId: project.projectId });
    await confirmIntake(page);
    await waitForRunPost(tracker, 120_000);
    expect(tracker.posts.length).toBe(1);
    const reqId = await captureUserRequestId(page, ctx, tracker);
    expect(reqId).toBeTruthy();
    const before = await waitForRunMeta(page, ctx, reqId!);
    const postsBeforeReload = tracker.posts.length;

    await page.reload();
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
    expect((await page.getByTestId("workspace-home").innerText()).trim().length).toBeGreaterThan(40);

    const after = await waitForRunMeta(page, ctx, reqId!);
    expect(after.run_id).toBe(before.run_id);
    expect(tracker.posts.length).toBe(postsBeforeReload);
    inFlightUserRequestIds.push(reqId!);

    await saveScenarioArtifact(
      ctx,
      { scenario: "D-refresh-running", run_id: after.run_id, post_count: tracker.posts.length },
      page,
    );
  });

  test("E — failure panel visible (no blank screen)", async ({ page }) => {
    const project = await createIsolatedTestProject(page, ctx, "E");
    await page.route(
      (url) => url.href.includes("business-idea-validation/run"),
      async (route) => {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({
            error_code: "research_failed",
            safe_message: "Исследование не удалось завершить",
          }),
        });
      },
    );

    await fillMinimalIntake(page, `${idea} — forced failure`, { projectId: project.projectId });
    await page.getByTestId("intake-confirm-button").click();

    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("biv-research-failed")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("workspace-home")).toBeVisible();
    await saveScenarioArtifact(ctx, { scenario: "E-failure-panel" }, page);
  });

  test("F — workspace never renders empty shell", async ({ page }) => {
    await page.goto("/workspace");
    await expect(page.getByTestId("workspace-home")).toBeVisible();
    const home = page.getByTestId("workspace-home");
    const text = (await home.innerText()).trim();
    expect(text.length).toBeGreaterThan(0);
    await saveScenarioArtifact(ctx, { scenario: "F-no-blank-shell" }, page);
  });

  test("G — completed report visible", async ({ page }) => {
    if (inFlightUserRequestIds.length > 0) {
      await Promise.all(
        inFlightUserRequestIds.map((pendingId) =>
          waitForRunSucceeded(page, ctx, pendingId, 600_000),
        ),
      );
      inFlightUserRequestIds.length = 0;
    }

    const project = await createIsolatedTestProject(page, ctx, "G");
    ghProjectId = project.projectId;
    await fillMinimalIntake(page, `${idea} — completed report`, { projectId: project.projectId });
    await confirmIntake(page);
    await waitForRunPost(tracker, 120_000);
    expect(tracker.posts.length).toBe(1);

    ghUserRequestId = await captureUserRequestId(page, ctx, tracker);
    expect(ghUserRequestId).toBeTruthy();

    const report = await waitForCustomerReportReady(
      page,
      ctx,
      ghUserRequestId!,
      project.projectId,
    );
    ghRunId = report.run_id;

    await saveScenarioArtifact(
      ctx,
      {
        scenario: "G-completed",
        run_id: report.run_id,
        user_request_id: ghUserRequestId,
        payload: {
          project_id: project.projectId,
          state_sequence: ["research_running", "report_building", "completed"],
          backend_completed_at: report.backend_completed_at,
          customer_report_ready_at: report.customer_report_ready_at,
          ui_hydrated_at: report.ui_hydrated_at,
        },
      },
      page,
    );
  });

  test("H — refresh completed preserves report, no new POST", async ({ page }) => {
    test.skip(!ghProjectId || !ghUserRequestId || !ghRunId, "Requires completed run from scenario G");

    await openProjectWorkspace(page, ghProjectId!);
    const postsBefore = tracker.posts.length;
    const before = await getLatestRunMeta(page, ctx, ghUserRequestId!);
    expect(before.run_id).toBe(ghRunId);

    await page.reload();
    await waitForReport(page, 60_000);
    const after = await getLatestRunMeta(page, ctx, ghUserRequestId!);
    expect(after.run_id).toBe(ghRunId);
    expect(tracker.posts.length).toBe(postsBefore);

    await saveScenarioArtifact(
      ctx,
      {
        scenario: "H-refresh-completed",
        run_id: after.run_id,
        post_count: tracker.posts.length,
        payload: { project_id: ghProjectId, refresh_post_count: tracker.posts.length - postsBefore },
      },
      page,
    );
  });

  test("I — exact owner browser case end-to-end", async ({ page }) => {
    const project = await createIsolatedTestProject(page, ctx, "I");
    await fillMinimalIntake(page, idea, { projectId: project.projectId });
    await page.getByTestId("intake-budget").fill("300000");
    await assertIntakeAutofillSemantics(page);

    const postsAtStart = tracker.posts.length;
    await confirmIntake(page);
    await waitForRunPost(tracker, 120_000);
    expect(tracker.posts.length - postsAtStart).toBe(1);

    const reqId = await captureUserRequestId(page, ctx, tracker);
    expect(reqId).toBeTruthy();

    const completed = await waitForCustomerReportReady(page, ctx, reqId!, project.projectId);

    await page.reload();
    await waitForReport(page, 60_000);
    const afterRefresh = await getLatestRunMeta(page, ctx, reqId!);
    expect(afterRefresh.run_id).toBe(completed.run_id);

    await page.goto("/workspace/projects");
    await expect(page.getByTestId("workspace-projects-list")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(project.name, { exact: true })).toBeVisible({ timeout: 60_000 });
    await openProjectWorkspace(page, project.projectId);
    await waitForReport(page, 60_000);

    await saveScenarioArtifact(
      ctx,
      {
        scenario: "I-owner-case",
        run_id: completed.run_id,
        post_count: tracker.posts.length - postsAtStart,
        user_request_id: reqId,
        payload: {
          project_id: project.projectId,
          run_rows: 1,
          reopen_persisted: true,
        },
      },
      page,
    );
  });
});
