import { expect, test } from "@playwright/test";

import { assertBackendMode } from "./helpers/cph2";
import { captureScreenshot, setViewport } from "./helpers/commercial-ux-verification";
import { seedIntakeLocale } from "./helpers/commercial-intake-verification";
import { bivLogin, loadBivContext } from "./helpers/biv-golden-path";
import { cleanupBivE2eRun, provisionBivE2eRun } from "./helpers/biv-e2e-isolation";

/**
 * Development-bundle only: developer diagnostics visible with explicit flag.
 * Production gate uses commercial-ux-slice-e-verification.spec.ts for absence proof.
 */
test.describe("Commercial UX Slice E — dev diagnostics screenshot", () => {
  test.describe.configure({ mode: "serial" });

  let ctx: ReturnType<typeof loadBivContext> | undefined;

  test.beforeAll(() => {
    const runId = process.env.SLICE_E_DEV_RUN_ID || `slice-e-dev-${Date.now()}`;
    process.env.SLICE_E_DEV_RUN_ID = runId;
    process.env.CPH3_RUN_ID = runId;
    const provision = provisionBivE2eRun(runId);
    process.env.CPH3_E2E_EMAIL = provision.email;
    process.env.CPH3_E2E_PASSWORD = provision.password ?? "";
    ctx = loadBivContext();
  });

  test.afterAll(() => {
    if (ctx?.runId) cleanupBivE2eRun(ctx.runId, { dryRun: false });
  });

  test("review-dev-diagnostics — visible in development with explicit flag", async ({ page }) => {
    if (!ctx) test.skip(true, "blocked:missing_context");
    await assertBackendMode(page, "backend");
    await seedIntakeLocale(page, { developerMode: true });
    await bivLogin(page, ctx!);
    await setViewport(page, "desktop");
    await page.goto("/workspace/projects/new/review");
    await expect(page.getByTestId("intake-review-customer")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("intake-developer-diagnostics")).toBeVisible();
    await page.getByTestId("intake-developer-diagnostics").locator("button").click();
    await captureScreenshot(page, "review-dev-diagnostics");
  });
});
