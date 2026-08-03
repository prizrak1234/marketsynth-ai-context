import { expect, test } from "@playwright/test";

import { assertCustomerSafeDom } from "./helpers/customer-surface-dom";
import { assertBackendMode } from "./helpers/cph2";
import { bivLogin, createRunRequestTracker, fillMinimalIntake } from "./helpers/biv-golden-path";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";
import {
  bindDeterministicFixture,
  cleanupRuntime01gContext,
  clearBivStorageHints,
  collectScenarioEvidence,
  confirmIntakeAndStartResearch,
  confirmIntakeDoubleClick,
  enqueueSecondRunSameProject,
  fetchLatestRun,
  loadRuntime01gContext,
  openProjectWorkspace,
  prepareIsolatedProject,
  queryActiveRunCount,
  queryInvestigation,
  queryRunSnapshot,
  runTerminalRestoreScenario,
  saveScenarioEvidence,
  verifyNewBrowserContextTechnicalFailure,
  waitForAsyncRunPost,
  waitForLatestRunTerminal,
  waitForTerminalUi,
  assertWorkspaceTerminalUi,
  resolveBivLifecycleLabel,
} from "./helpers/runtime-01g-concurrent-run-recovery";
import { bivLifecycleStatusLabel } from "../src/lib/biv/biv-lifecycle-labels";

test.describe("RUNTIME-01G concurrent run and failure recovery", () => {
  test.describe.configure({ mode: "serial", timeout: 420_000 });

  let ctx: ReturnType<typeof loadRuntime01gContext>;

  test.beforeAll(() => {
    try {
      ctx = loadRuntime01gContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
  });

  test.afterAll(() => {
    if (!ctx) return;
    cleanupRuntime01gContext(ctx);
  });

  test.beforeEach(async ({ page }) => {
    if (!ctx) return;
    await assertBackendMode(page, "backend");
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
    await bivLogin(page, ctx);
  });

  test("A — double click submit keeps one active run", async ({ page }) => {
    if (!ctx) return;
    bindDeterministicFixture(ctx.runId, "verdict");
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    const isolated = await prepareIsolatedProject(page, ctx, "A-double-click");
    await confirmIntakeDoubleClick(page, "E2E double click submit", isolated.projectId);
    await waitForAsyncRunPost(tracker, 120_000);
    expect(tracker.asyncPosts.length).toBeLessThanOrEqual(2);

    let latestRunning = await fetchLatestRun(page, ctx, isolated.projectId);
    if (!latestRunning) {
      latestRunning = await waitForLatestRunTerminal(page, ctx, isolated.projectId, "verdict", 180_000);
    }
    expect(latestRunning).toBeTruthy();
    if (latestRunning!.status === "queued" || latestRunning!.status === "running") {
      expect(queryActiveRunCount(isolated.projectId)).toBeLessThanOrEqual(1);
    }

    const latest = await waitForLatestRunTerminal(page, ctx, isolated.projectId, "verdict", 180_000);
    await openProjectWorkspace(page, isolated.projectId);
    await assertWorkspaceTerminalUi(page, "verdict", 60_000);
    const evidence = await collectScenarioEvidence("A-double-click", page, ctx, tracker, isolated.projectId, {
      runId: latest!.run_id,
      userRequestId: latest!.user_request_id,
    });

    expect(evidence.active_run_count).toBe(0);
    expect(evidence.investigation?.superseded).not.toBe(true);
    expect(evidence.post_runs_count).toBeLessThanOrEqual(2);
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible({ timeout: 60_000 });
  });

  test("B — two tabs same project share one active run", async ({ browser }) => {
    if (!ctx) return;
    bindDeterministicFixture(ctx.runId, "verdict");
    const context = await browser.newContext();
    const pageA = await context.newPage();
    const pageB = await context.newPage();
    const trackerA = createRunRequestTracker();
    const trackerB = createRunRequestTracker();
    trackerA.attach(pageA);
    trackerB.attach(pageB);

    for (const page of [pageA, pageB]) {
      await assertBackendMode(page, "backend");
      await page.addInitScript(() => {
        window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
        window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
      });
      await bivLogin(page, ctx);
    }

    const isolated = await prepareIsolatedProject(pageA, ctx, "B-two-tabs");
    const idea = `E2E two tabs ${Date.now()}`;
    await fillMinimalIntake(pageA, idea, { projectId: isolated.projectId });
    await openProjectWorkspace(pageB, isolated.projectId);
    await fillMinimalIntake(pageB, idea, { projectId: isolated.projectId });

    await Promise.all([
      pageA.getByTestId("intake-confirm-button").click(),
      pageB.getByTestId("intake-confirm-button").click(),
    ]);

    await waitForAsyncRunPost(trackerA, 120_000);
    await waitForAsyncRunPost(trackerB, 120_000);

    const latestA = await fetchLatestRun(pageA, ctx, isolated.projectId);
    const latestB = await fetchLatestRun(pageB, ctx, isolated.projectId);
    expect(latestA).toBeTruthy();
    expect(latestB).toBeTruthy();
    expect(latestA!.run_id).toBe(latestB!.run_id);

    const evidence = await collectScenarioEvidence(
      "B-two-tabs",
      pageA,
      ctx,
      trackerA,
      isolated.projectId,
      { runId: latestA!.run_id, userRequestId: latestA!.user_request_id },
    );
    evidence.post_runs_count = trackerA.asyncPosts.length + trackerB.asyncPosts.length;
    await saveScenarioEvidence("B-two-tabs", evidence, pageA);

    expect(evidence.active_run_count).toBeLessThanOrEqual(1);
    expect(evidence.investigation?.superseded).not.toBe(true);
    await waitForLatestRunTerminal(pageA, ctx, isolated.projectId, "verdict", 180_000);
    await openProjectWorkspace(pageA, isolated.projectId);
    await openProjectWorkspace(pageB, isolated.projectId);
    await assertWorkspaceTerminalUi(pageA, "verdict", 60_000);
    await assertWorkspaceTerminalUi(pageB, "verdict", 60_000);
    await context.close();
  });

  test("C — refresh during running restores via latest-run without duplicate POST", async ({ page }) => {
    if (!ctx) return;
    bindDeterministicFixture(ctx.runId, "verdict");
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    const isolated = await prepareIsolatedProject(page, ctx, "C-refresh-running");
    await confirmIntakeAndStartResearch(page, "E2E refresh running", isolated.projectId);
    await waitForAsyncRunPost(tracker, 120_000);
    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 30_000 });

    const latestBefore = await fetchLatestRun(page, ctx, isolated.projectId);
    expect(latestBefore).toBeTruthy();
    expect(["queued", "running", "succeeded"]).toContain(latestBefore!.status);

    const postsBefore = tracker.asyncPosts.length;
    await clearBivStorageHints(page);
    await page.reload();
    await expect(page.getByTestId("workspace-home")).toBeVisible({ timeout: 60_000 });
    expect(tracker.asyncPosts.length).toBe(postsBefore);

    const latestAfter = await fetchLatestRun(page, ctx, isolated.projectId);
    expect(latestAfter?.run_id).toBe(latestBefore!.run_id);
    await expect(
      page
        .getByTestId("biv-research-progress")
        .or(page.getByTestId("business-validation-result-card")),
    ).toBeVisible({ timeout: 90_000 });

    const evidence = await collectScenarioEvidence("C-refresh-running", page, ctx, tracker, isolated.projectId, {
      runId: latestAfter!.run_id,
      userRequestId: latestAfter!.user_request_id,
    });
    expect(evidence.post_runs_count).toBe(1);
  });

  test("D — technical failure restore in new browser context", async ({ page, context }) => {
    if (!ctx) return;
    bindDeterministicFixture(ctx.runId, "technical");
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    const isolated = await prepareIsolatedProject(page, ctx, "D-technical-restore");
    await confirmIntakeAndStartResearch(page, "E2E technical restore", isolated.projectId);
    await waitForAsyncRunPost(tracker, 120_000);
    const latest = await waitForLatestRunTerminal(page, ctx, isolated.projectId, "technical", 180_000);
    await openProjectWorkspace(page, isolated.projectId);
    await assertWorkspaceTerminalUi(page, "technical", 60_000);

    expect(latest.has_output).toBe(false);
    expect(latest.status).toBe("failed");

    await assertCustomerSafeDom(page);
    await verifyNewBrowserContextTechnicalFailure(context, ctx, isolated.projectId);

    const evidence = await collectScenarioEvidence("D-technical-restore", page, ctx, tracker, isolated.projectId, {
      runId: latest.run_id,
      userRequestId: latest.user_request_id,
    });
    expect(evidence.has_output).toBe(false);
    expect(evidence.progress_state).toBe("failed");
  });

  test("E — partial restore shows honest label and terminal progress", async ({ page }) => {
    if (!ctx) return;
    await runTerminalRestoreScenario(page, ctx, {
      scenario: "E-partial-restore",
      outcome: "partial",
      projectNameSuffix: "partial-restore",
      expectedLabel: "Результат ограничен данными",
    });
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible();
    await expect(page.getByTestId("biv-research-progress")).toHaveCount(0);
  });

  test("F — verdict restore shows completed label", async ({ page }) => {
    if (!ctx) return;
    await runTerminalRestoreScenario(page, ctx, {
      scenario: "F-verdict-restore",
      outcome: "verdict",
      projectNameSuffix: "verdict-restore",
      expectedLabel: "Исследование завершено",
      newContext: true,
    });
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible();
  });

  test("G — recent project lifecycle status labels", async ({ page }) => {
    if (!ctx) return;

    const running = await prepareIsolatedProject(page, ctx, "G-running");
    bindDeterministicFixture(ctx.runId, "verdict");
    const runningTracker = createRunRequestTracker();
    runningTracker.attach(page);
    await confirmIntakeAndStartResearch(page, "E2E label running", running.projectId);
    await waitForAsyncRunPost(runningTracker, 120_000);
    let runningLabelCaptured: string | null = null;
    for (let attempt = 0; attempt < 30; attempt += 1) {
      const runningLatest = await fetchLatestRun(page, ctx, running.projectId);
      if (
        runningLatest &&
        (runningLatest.status === "queued" || runningLatest.status === "running")
      ) {
        runningLabelCaptured = bivLifecycleStatusLabel(runningLatest);
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (runningLabelCaptured) {
      expect(runningLabelCaptured).toBe("Исследование выполняется");
    }

    bindDeterministicFixture(ctx.runId, "verdict");
    const succeeded = await prepareIsolatedProject(page, ctx, "G-succeeded");
    const succeededTracker = createRunRequestTracker();
    succeededTracker.attach(page);
    await confirmIntakeAndStartResearch(page, "E2E label succeeded", succeeded.projectId);
    await waitForAsyncRunPost(succeededTracker, 120_000);
    await waitForLatestRunTerminal(page, ctx, succeeded.projectId, "verdict", 180_000);
    await openProjectWorkspace(page, succeeded.projectId);
    const succeededEvidence = await collectScenarioEvidence(
      "G-label-succeeded",
      page,
      ctx,
      succeededTracker,
      succeeded.projectId,
      { projectName: succeeded.name },
    );
    expect(succeededEvidence.recent_project_label).toBe("Исследование завершено");

    bindDeterministicFixture(ctx.runId, "partial");
    const partial = await prepareIsolatedProject(page, ctx, "G-partial");
    const partialTracker = createRunRequestTracker();
    partialTracker.attach(page);
    await confirmIntakeAndStartResearch(page, "E2E label partial", partial.projectId);
    await waitForAsyncRunPost(partialTracker, 120_000);
    await waitForLatestRunTerminal(page, ctx, partial.projectId, "partial", 180_000);
    await openProjectWorkspace(page, partial.projectId);
    const partialEvidence = await collectScenarioEvidence(
      "G-label-partial",
      page,
      ctx,
      partialTracker,
      partial.projectId,
      { projectName: partial.name },
    );
    expect(partialEvidence.recent_project_label).toBe("Результат ограничен данными");

    bindDeterministicFixture(ctx.runId, "technical");
    const failed = await prepareIsolatedProject(page, ctx, "G-failed");
    const failedTracker = createRunRequestTracker();
    failedTracker.attach(page);
    await confirmIntakeAndStartResearch(page, "E2E label failed", failed.projectId);
    await waitForAsyncRunPost(failedTracker, 120_000);
    await waitForLatestRunTerminal(page, ctx, failed.projectId, "technical", 180_000);
    await openProjectWorkspace(page, failed.projectId);
    const failedEvidence = await collectScenarioEvidence(
      "G-label-failed",
      page,
      ctx,
      failedTracker,
      failed.projectId,
      { projectName: failed.name },
    );
    expect(failedEvidence.recent_project_label).toBe("Исследование прервано");

    const pending = await prepareIsolatedProject(page, ctx, "G-pending", { seedDraft: true });
    await fillMinimalIntake(page, "E2E label pending", { projectId: pending.projectId });
    const pendingEvidence = await collectScenarioEvidence(
      "G-label-pending",
      page,
      ctx,
      createRunRequestTracker(),
      pending.projectId,
      { projectName: pending.name },
    );
    expect(pendingEvidence.recent_project_label).toBe("Ожидает проверки");
  });

  test("incident regression — active run B reuses A, investigation stays mutable, A succeeds", async ({
    page,
  }) => {
    if (!ctx) return;
    bindDeterministicFixture(ctx.runId, "verdict");
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    const isolated = await prepareIsolatedProject(page, ctx, "incident-regression");
    await fillMinimalIntake(page, "E2E incident regression", { projectId: isolated.projectId });
    await page.getByTestId("intake-confirm-button").click();
    await page.waitForTimeout(250);
    const second = await enqueueSecondRunSameProject(page, ctx, isolated.projectId);
    await waitForAsyncRunPost(tracker, 120_000);

    const runA = await fetchLatestRun(page, ctx, isolated.projectId);
    expect(runA).toBeTruthy();
    const invBefore = queryInvestigation(runA!.run_id);
    expect(invBefore.superseded).not.toBe(true);

    expect(second.run_id).toBe(runA!.run_id);
    expect(second.lineage_reused).toBe(true);
    expect(queryActiveRunCount(isolated.projectId)).toBeLessThanOrEqual(1);

    const invDuring = queryInvestigation(runA!.run_id);
    expect(invDuring.superseded).not.toBe(true);

    await waitForLatestRunTerminal(page, ctx, isolated.projectId, "verdict", 180_000);
    const snapshot = queryRunSnapshot(runA!.run_id);
    expect(snapshot.status).toBe("succeeded");
    expect(snapshot.error_code).not.toBe("investigation_immutable");
    expect(snapshot.has_output).toBe(true);

    const evidence = await collectScenarioEvidence(
      "incident-regression",
      page,
      ctx,
      tracker,
      isolated.projectId,
      { runId: runA!.run_id, userRequestId: runA!.user_request_id },
    );
    expect(evidence.investigation?.superseded).not.toBe(true);
  });
});
