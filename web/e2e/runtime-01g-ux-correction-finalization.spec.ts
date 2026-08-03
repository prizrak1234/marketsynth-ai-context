import { expect, test } from "@playwright/test";

import { bivLogin } from "./helpers/biv-golden-path";
import { assertCustomerSafeDom } from "./helpers/customer-surface-dom";
import {
  bindDeterministicFixture,
  cleanupRuntime01fContext,
  loadRuntime01fContext,
  startCanonicalGoldenPathFromLanding,
  submitSevenStepIntake,
  waitForTerminalUi,
} from "./helpers/runtime-01f-golden-path";
import { createRunRequestTracker, waitForAsyncRunPost } from "./helpers/biv-golden-path";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

const ARTIFACT_DIR = "e2e-artifacts/ux-correction";

test.use({ trace: "on" });

async function capture(page: import("@playwright/test").Page, name: string) {
  await page.screenshot({ path: `${ARTIFACT_DIR}/${name}.png`, fullPage: true });
}

test.describe("RUNTIME-01G UX correction finalization — post-submit customer surfaces", () => {
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
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
    await bivLogin(page, ctx);
  });

  test("verdict — progress, refresh, terminal report", async ({ page }) => {
    if (!ctx) return;
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    bindDeterministicFixture(ctx.runId, "verdict");

    await page.setViewportSize({ width: 1920, height: 1080 });
    await startCanonicalGoldenPathFromLanding(page, ctx, `E2E-01G-Verdict-${Date.now()}`);
    await submitSevenStepIntake(page);
    await waitForAsyncRunPost(tracker, 120_000);

    await expect(page.getByTestId("biv-research-progress")).toBeVisible({ timeout: 60_000 });
    await assertCustomerSafeDom(page);
    await capture(page, "progress-running-1920");

    const postsBefore = tracker.asyncPosts.length;
    await page.reload();
    await page.waitForURL(/\/workspace(\?project=|$)/, { timeout: 60_000 });
    expect(tracker.asyncPosts.length).toBe(postsBefore);
    const progressAfterRefresh = page.getByTestId("biv-research-progress");
    const reportAfterRefresh = page.getByTestId("business-validation-result-card");
    await expect(progressAfterRefresh.or(reportAfterRefresh)).toBeVisible({ timeout: 90_000 });
    await capture(page, "progress-after-refresh-1920");

    if (!(await reportAfterRefresh.isVisible())) {
      await waitForTerminalUi(page, "verdict", 180_000);
    }
    await assertCustomerSafeDom(page);
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible();
    await expect(page.getByTestId("biv-research-progress")).toHaveCount(0);
    await capture(page, "verdict-1920");

    await page.setViewportSize({ width: 1366, height: 768 });
    await capture(page, "verdict-1366");
  });

  test("partial — honest insufficiency surface", async ({ page }) => {
    if (!ctx) return;
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    bindDeterministicFixture(ctx.runId, "partial");

    await page.setViewportSize({ width: 1920, height: 1080 });
    await startCanonicalGoldenPathFromLanding(page, ctx, `E2E-01G-Partial-${Date.now()}`);
    await submitSevenStepIntake(page);
    await waitForAsyncRunPost(tracker, 120_000);
    await waitForTerminalUi(page, "partial", 180_000);

    await assertCustomerSafeDom(page);
    await expect(page.getByTestId("biv-partial-research-panel")).toBeVisible();
    await expect(page.getByTestId("biv-partial-stop-reason")).toBeVisible();
    await expect(page.getByTestId("biv-partial-rerun")).toHaveCount(1);
    await expect(page.getByTestId("business-validation-result-card")).toHaveCount(0);
    await capture(page, "partial-1920");
  });

  test("technical failure — safe message without false verdict", async ({ page }) => {
    if (!ctx) return;
    const tracker = createRunRequestTracker();
    tracker.attach(page);
    bindDeterministicFixture(ctx.runId, "technical");

    await page.setViewportSize({ width: 1920, height: 1080 });
    await startCanonicalGoldenPathFromLanding(page, ctx, `E2E-01G-Technical-${Date.now()}`);
    await submitSevenStepIntake(page);
    await waitForAsyncRunPost(tracker, 120_000);
    await waitForTerminalUi(page, "technical", 180_000);

    await assertCustomerSafeDom(page);
    await expect(page.getByTestId("biv-research-failed")).toBeVisible();
    await expect(page.getByTestId("biv-partial-research-panel")).toHaveCount(0);
    await expect(page.getByTestId("business-validation-result-card")).toHaveCount(0);
    await expect(page.getByTestId("biv-research-failed-retry")).toHaveCount(1);
    await capture(page, "technical-failure-1920");
  });
});
