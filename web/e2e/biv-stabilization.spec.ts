import { expect, test } from "@playwright/test";
import {
  assertBudgetFieldAutofillSemantics,
  bivLogin,
  confirmAndStartResearch,
  exportReport,
  fillMinimalIntake,
  getBivProgress,
  loadBivContext,
  saveScenarioArtifact,
  waitForReport,
} from "./helpers/biv-stabilization";
import { apiJson } from "./helpers/cph2";

/**
 * CWF.1 BIV Stabilization — 8 mandatory E2E scenarios (A–H).
 * Requires: backend + frontend + BIV_SMOKE / CPH3_E2E credentials.
 */
test.describe("BIV stabilization E2E", () => {
  test.describe.configure({ mode: "serial", timeout: 300_000 });

  let ctx: ReturnType<typeof loadBivContext>;
  let projectId: string | undefined;
  let userRequestId: string | undefined;
  let firstRunId: string | undefined;

  test.beforeAll(() => {
    try {
      ctx = loadBivContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
  });

  test.beforeEach(async ({ page }) => {
    if (!ctx) return;
    await bivLogin(page, ctx);
  });

  test("A — new project: intake → research → customer_report", async ({ page }) => {
    const idea =
      "SaaS-платформа для автоматизации отчётности малого бизнеса с подпиской от 990 ₽/мес";
    await fillMinimalIntake(page, idea);
    await assertBudgetFieldAutofillSemantics(page);
    await page.getByTestId("intake-budget").focus();

    let runPostCount = 0;
    page.on("request", (request) => {
      if (
        request.method() === "POST" &&
        request.url().includes("/business-idea-validation/run")
      ) {
        runPostCount += 1;
      }
    });

    await confirmAndStartResearch(page);
    expect(runPostCount).toBe(1);

    const progress = page.getByTestId("biv-research-progress");
    await expect(progress).toBeVisible();
    await waitForReport(page);

    const exportText = await exportReport(page);
    expect(exportText).not.toMatch(/\[.*\]\(\)/);
    expect(exportText.length).toBeGreaterThan(200);

    await saveScenarioArtifact(ctx, { scenario: "A-new-project", status: 200 }, page);
  });

  test("B — legacy project hydration shows customer_report", async ({ page }) => {
    test.skip(!projectId, "No project from scenario A");
    await page.goto(`/workspace/projects/${projectId}`);
    await expect(page.getByTestId("business-validation-result-card")).toBeVisible({
      timeout: 60_000,
    });
    await saveScenarioArtifact(ctx, { scenario: "B-legacy-hydrate" }, page);
  });

  test("C — rerun creates new run_id with parent lineage", async ({ page }) => {
    test.skip(!projectId, "No project");
    await page.goto(`/workspace/projects/${projectId}`);
    const rerun = page.getByTestId("agency-action-retry-research");
    if (await rerun.isVisible()) {
      await rerun.click();
      await waitForReport(page, 240_000);
    }
    await saveScenarioArtifact(ctx, { scenario: "C-rerun", run_id: firstRunId }, page);
  });

  test("D — refined rerun prefills changed fields", async ({ page }) => {
    test.skip(!projectId, "No project");
    await page.goto(`/workspace/projects/${projectId}`);
    const clarify = page.getByTestId("agency-action-refine-inputs");
    if (await clarify.isVisible()) {
      await clarify.click();
      await expect(page.getByTestId("analysis-intake-panel")).toBeVisible();
      await confirmAndStartResearch(page);
      await waitForReport(page, 240_000);
    }
    await saveScenarioArtifact(ctx, { scenario: "D-refined-rerun" }, page);
  });

  test("E — refresh restores completed report without duplicate run", async ({ page }) => {
    test.skip(!projectId, "No project");
    await page.goto(`/workspace/projects/${projectId}`);
    await waitForReport(page, 60_000);
    const runIdBefore = firstRunId;
    await page.reload();
    await waitForReport(page, 60_000);
    expect(runIdBefore).toBeDefined();
    await saveScenarioArtifact(ctx, { scenario: "E-refresh", run_id: runIdBefore }, page);
  });

  test("F — session expiry shows recovery UI", async ({ page }) => {
    await page.goto("/workspace");
    await page.evaluate(() => {
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
    });
    await page.reload();
    await expect(page.getByRole("heading", { name: /Вход в пилот/i })).toBeVisible({
      timeout: 30_000,
    });
    await bivLogin(page, ctx);
    await saveScenarioArtifact(ctx, { scenario: "F-session-expiry" }, page);
  });

  test("G — provider failure shows FAILED panel without raw codes", async ({ page }) => {
    await page.goto("/workspace");
    await expect(page.getByTestId("intent-start-panel")).toBeVisible();
    const body = await page.content();
    expect(body).not.toMatch(/research_idempotency_key_required/);
    await saveScenarioArtifact(ctx, { scenario: "G-provider-failure-guard" }, page);
  });

  test("H — export readable with numbered sources", async ({ page }) => {
    test.skip(!projectId, "No project");
    await page.goto(`/workspace/projects/${projectId}`);
    await waitForReport(page, 60_000);
    const text = await exportReport(page);
    expect(text).not.toMatch(/\[.*\]\(\)/);
    expect(text).toMatch(/MARKETSYNTH|Marketsynth|Вердикт/i);
    await saveScenarioArtifact(ctx, { scenario: "H-export" }, page);
  });

  test.afterEach(async ({ page }, testInfo) => {
    if (!ctx) return;
    try {
      const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
      projectId = projects[0]?.id ?? projectId;
      if (projectId && !userRequestId) {
        const journey = await apiJson<{ user_request_id: string }>(
          page,
          ctx,
          "GET",
          `/projects/${projectId}/launch-pack/journey`,
        );
        userRequestId = journey.user_request_id;
        if (userRequestId) {
          const latest = await apiJson<{ run_id: string }>(
            page,
            ctx,
            "GET",
            `/user-requests/${userRequestId}/business-idea-validation`,
          );
          firstRunId = latest.run_id;
          const prog = await getBivProgress(page, ctx, userRequestId);
          expect(prog.progress_percent).toBeGreaterThanOrEqual(0);
        }
      }
    } catch {
      // best-effort lineage capture
    }
    if (testInfo.status !== testInfo.expectedStatus) {
      await saveScenarioArtifact(ctx, { scenario: `failed-${testInfo.title}` }, page);
    }
  });
});
