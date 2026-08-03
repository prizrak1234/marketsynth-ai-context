import { expect, test } from "@playwright/test";

import {
  assertLayoutHealthy,
  assertNoHydrationErrors,
  attachConsoleCollector,
  captureScreenshot,
  setViewport,
  VIEWPORTS,
} from "./helpers/commercial-ux-verification";
import {
  assertReviewCustomerSafe,
  clearIntakeDraftStorage,
  countBackendProjects,
  fillIntakeWizardToReview,
  fillBasicsRequired,
  installAutosaveFailure,
  readDraftId,
  waitForDraftPersisted,
  seedIntakeLocale,
} from "./helpers/commercial-intake-verification";
import {
  bivLogin,
  createRunRequestTracker,
  loadBivContext,
  waitForAsyncRunPost,
} from "./helpers/biv-golden-path";
import { cleanupBivE2eRun, provisionBivE2eRun } from "./helpers/biv-e2e-isolation";
import { bindDeterministicFixture } from "./helpers/runtime-01f-golden-path";

/** PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01E-VERIFICATION — production browser gate. */
test.describe("Commercial UX Slice E — intake verification gate", () => {
  test.describe.configure({ mode: "serial", timeout: 240_000 });

  let ctx: ReturnType<typeof loadBivContext>;
  let blockedReason: string | null = null;

  test.beforeAll(() => {
    const runId = process.env.SLICE_E_VERIFICATION_RUN_ID || `slice-e-${Date.now()}`;
    process.env.SLICE_E_VERIFICATION_RUN_ID = runId;
    process.env.CPH3_RUN_ID = runId;
    try {
      const provision = provisionBivE2eRun(runId);
      process.env.CPH3_E2E_EMAIL = provision.email;
      process.env.CPH3_E2E_PASSWORD = provision.password ?? "";
      if (!process.env.CPH3_E2E_PASSWORD) {
        blockedReason = "provision_missing_password";
        return;
      }
      ctx = loadBivContext();
    } catch (err) {
      blockedReason = err instanceof Error ? err.message : "provision_failed";
    }
  });

  test.afterAll(() => {
    if (ctx?.runId) {
      cleanupBivE2eRun(ctx.runId, { dryRun: false });
    }
  });

  test.beforeEach(async ({ page }) => {
    if (blockedReason || !ctx) {
      test.skip(true, `blocked:${blockedReason ?? "missing_context"}`);
    }
    await seedIntakeLocale(page);
    await bivLogin(page, ctx!);
    await clearIntakeDraftStorage(page);
  });

  test("A — full 7-step happy path to review without research", async ({ page }) => {
    const consoleErrors = attachConsoleCollector(page);
    await setViewport(page, "desktop");
    const projectName = `SliceE-Happy-${Date.now()}`;
    await fillIntakeWizardToReview(page, projectName);
    await assertReviewCustomerSafe(page);
    await expect(page.getByText(projectName)).toBeVisible();
    await captureScreenshot(page, "review-desktop");
    await assertLayoutHealthy(page);
    await assertNoHydrationErrors(consoleErrors);
  });

  test("B — required validation with customer-safe messages and focus", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await page.getByTestId("intake-next").click();
    await expect(page.getByTestId("intake-step-validation-banner")).toBeVisible();
    await expect(page.getByTestId("intake-step-validation-banner")).toContainText(
      /обязательн/i,
    );
    const focused = await page.evaluate(() => document.activeElement?.id ?? "");
    expect(["name", "ideaDescription", "businessType", "projectStage", "geography"]).toContain(
      focused,
    );
    await captureScreenshot(page, "validation-error");
  });

  test("C — optional fields skipped and review remains correct", async ({ page }) => {
    await setViewport(page, "desktop");
    await fillIntakeWizardToReview(page, `SliceE-Optional-${Date.now()}`);
    await expect(page.getByTestId("intake-review-section-economics")).toContainText("—");
    await assertReviewCustomerSafe(page);
  });

  test("D — conditional competitors hide fields and restore values", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new/market");
    await page.locator("#targetMarket").fill("Рынок SaaS для бухгалтерии");
    await page.locator("#competitorsUnknown").uncheck();
    await page.locator("#knownCompetitors").fill("Конкурент А");
    await page.locator("#competitorUrls").fill("https://example.com/competitor");
    await page.locator("#competitorsUnknown").check();
    await expect(page.locator("#knownCompetitors")).toHaveCount(0);
    await page.locator("#competitorsUnknown").uncheck();
    await expect(page.locator("#knownCompetitors")).toHaveValue("Конкурент А");
    await expect(page.locator("#competitorUrls")).toHaveValue("https://example.com/competitor");
  });

  test("E — mid-step reload preserves draft and step", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await fillBasicsRequired(page, "SliceE-Reload");
    await page.getByTestId("intake-next").click();
    await page.waitForURL(/\/idea/);
    const draftId = await waitForDraftPersisted(page);
    expect(draftId.length).toBeGreaterThan(0);
    const projectsBefore = await countBackendProjects(page, ctx!);
    await page.reload();
    await expect(page.getByTestId("intake-step-product")).toBeVisible();
    await expect(page).toHaveURL(/\/idea/);
    const storedBasics = await page.evaluate((draftKey) => {
      const raw = window.localStorage.getItem(draftKey);
      if (!raw) return null;
      return JSON.parse(raw) as { projectBasics?: { name?: string }; currentStep?: string };
    }, "marketsynth.product_alpha.intake_draft.v1");
    expect(storedBasics?.projectBasics?.name).toBe("SliceE-Reload");
    expect(storedBasics?.currentStep).toBe("product");
    expect(await readDraftId(page)).toBe(draftId);
    expect(await countBackendProjects(page, ctx!)).toBe(projectsBefore);
  });

  test("F — browser back and forward keeps steps aligned", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await fillBasicsRequired(page, "SliceE-Nav");
    await page.getByTestId("intake-next").click();
    await page.waitForURL(/\/idea/);
    await page.locator("#whatIsSold").fill("Услуга");
    await page.goBack();
    await expect(page.getByTestId("intake-step-basics")).toBeVisible();
    await expect(page.locator("#name")).toHaveValue("SliceE-Nav");
    await page.goForward();
    await expect(page.getByTestId("intake-step-product")).toBeVisible();
    await expect(page.locator("#whatIsSold")).toHaveValue("Услуга");
  });

  test("G — autosave success indicator", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await page.locator("#name").fill("SliceE-Autosave");
    await expect(page.getByTestId("intake-autosave-status").first()).toContainText(/Сохраняем|Изменения сохранены/, {
      timeout: 10_000,
    });
    await expect(page.getByTestId("intake-autosave-status").first()).toContainText("Изменения сохранены", {
      timeout: 10_000,
    });
  });

  test("H — autosave failure is customer-safe and keeps typed data", async ({ page }) => {
    await installAutosaveFailure(page);
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await page.locator("#name").fill("SliceE-Autosave-Fail");
    await expect(page.getByTestId("intake-autosave-status").first()).toContainText("Не удалось сохранить", {
      timeout: 15_000,
    });
    await expect(page.locator("#name")).toHaveValue("SliceE-Autosave-Fail");
    await expect(page.getByTestId("intake-golden-path-submit")).toHaveCount(0);
    await captureScreenshot(page, "autosave-error");
  });

  test("I — review actions and production diagnostics boundary", async ({ page }) => {
    await setViewport(page, "desktop");
    await fillIntakeWizardToReview(page, `SliceE-Review-${Date.now()}`);
    await assertReviewCustomerSafe(page);
    await captureScreenshot(page, "review-production-no-diagnostics");
  });

  test("K — submit contract: one async POST /runs, no sync /run, no double-click duplicate", async ({
    page,
  }) => {
    bindDeterministicFixture(ctx!.runId, "verdict");
    const tracker = createRunRequestTracker();
    tracker.attach(page);

    await setViewport(page, "desktop");
    await fillIntakeWizardToReview(page, `SliceE-Submit-${Date.now()}`);
    const submit = page.getByTestId("intake-golden-path-submit");
    await expect(submit).toBeEnabled({ timeout: 20_000 });
    await submit.dblclick();
    await waitForAsyncRunPost(tracker, 90_000);
    expect(tracker.posts.filter((r) => r.url().includes("/business-idea-validation/run"))).toHaveLength(
      0,
    );
    expect(
      tracker.asyncPosts.filter((r) => r.url().includes("/business-idea-validation/runs")),
    ).toHaveLength(1);
  });

  test("L — existing draft restore on direct step URL", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await fillBasicsRequired(page, "SliceE-Restore");
    await page.getByTestId("intake-next").click();
    await page.waitForURL(/\/idea/);
    await page.goto("/workspace/projects/new/market");
    await expect(page.locator("#targetMarket")).toBeVisible();
    await page.locator("#targetMarket").fill("Восстановленный рынок");
    await expect(page.getByTestId("intake-autosave-status").first()).toContainText("Изменения сохранены", {
      timeout: 10_000,
    });
    await page.reload();
    await expect(page.locator("#targetMarket")).toHaveValue("Восстановленный рынок");
    await expect(page.getByTestId("intake-step-market")).toBeVisible();
  });

  test("screenshots — step1 desktop and mobile", async ({ page }) => {
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new");
    await expect(page.getByTestId("intake-step-basics")).toBeVisible();
    await captureScreenshot(page, "step1-desktop");

    await setViewport(page, "mobile");
    await page.goto("/workspace/projects/new");
    await expect(page.getByTestId("intake-step-basics")).toBeVisible();
    await captureScreenshot(page, "step1-mobile");
  });

  test("screenshots — market, audience, economics, materials desktop", async ({ page }) => {
    await setViewport(page, "desktop");
    for (const [path, name] of [
      ["/workspace/projects/new/market", "market"],
      ["/workspace/projects/new/audience", "audience"],
      ["/workspace/projects/new/economics", "economics"],
      ["/workspace/projects/new/materials", "materials"],
    ] as const) {
      await page.goto(path);
      await expect(page.getByTestId(`intake-step-${name}`)).toBeVisible({ timeout: 30_000 });
      if (name === "materials") {
        await expect(page.getByText("Product Alpha")).toHaveCount(0);
        await expect(page.getByTestId("intake-materials-draft-notice")).toBeVisible();
      }
      await captureScreenshot(page, `${name}-desktop`);
    }
  });

  test("M — mobile full intake to review", async ({ page }) => {
    await setViewport(page, "mobile");
    await fillIntakeWizardToReview(page, `SliceE-Mobile-${Date.now()}`);
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "review-mobile");
  });

  test("N — tablet layout matrix on review", async ({ page }) => {
    await setViewport(page, "tablet");
    await page.goto("/workspace/projects/new/review");
    await expect(page.getByTestId("intake-review-customer")).toBeVisible({ timeout: 30_000 });
    await assertLayoutHealthy(page);
    await captureScreenshot(page, "review-768x1024");
  });

  test("viewport matrix — all breakpoints without horizontal overflow", async ({ page }) => {
    for (const key of Object.keys(VIEWPORTS) as Array<keyof typeof VIEWPORTS>) {
      await setViewport(page, key);
      await page.goto("/workspace/projects/new/review");
      await expect(page.getByTestId("intake-review-customer")).toBeVisible({ timeout: 30_000 });
      await assertLayoutHealthy(page);
    }
  });
});
