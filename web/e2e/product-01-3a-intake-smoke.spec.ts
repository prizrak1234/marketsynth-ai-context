import { expect, test } from "@playwright/test";
import {
  apiJson,
  assertBackendMode,
  loadE2EContext,
  loginViaUi,
} from "./helpers/cph2";

/**
 * PRODUCT-01.3A.1 — intake smoke regression.
 * Click «Проверить идею» → intake form visible, no raw Not Found.
 */
test.describe("PRODUCT-01.3A intake gate smoke", () => {
  test.beforeEach(async ({ page }) => {
    try {
      loadE2EContext();
    } catch {
      test.skip(true, "blocked_by_missing_e2e_credentials");
    }
    await assertBackendMode(page, "backend");
    await page.addInitScript(() => {
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    });
    const ctx = loadE2EContext();
    await loginViaUi(page, ctx);
  });

  test("analysis-context API routes exist", async ({ page }) => {
    const ctx = loadE2EContext();
    const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
    const projectId = projects[0]?.id;
    test.skip(!projectId, "No project — create one in pilot");

    const current = await apiJson<{ context: unknown | null }>(
      page,
      ctx,
      "GET",
      `/projects/${projectId}/analysis-contexts/current`,
    );
    expect(current).toHaveProperty("context");
  });

  test("click validate idea opens intake form without Not Found", async ({ page }) => {
    await page.goto("/workspace");
    await expect(page.getByTestId("intent-start-panel")).toBeVisible();

    const validateCard = page.getByTestId("intent-card-validate-idea");
    await validateCard.click();

    await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Not Found")).toHaveCount(0);
    await expect(page.getByTestId("agency-analysis-stages")).toHaveCount(0);
  });

  test("minimal valid intake enables confirm button", async ({ page }) => {
    await page.goto("/workspace");
    await page.getByTestId("intent-card-validate-idea").click();
    await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("intake-product").fill("Курсы английского языка");
    await page.getByTestId("intake-audience").fill("Взрослые 25–45 лет");
    await page.getByTestId("intake-geography").fill("Россия, онлайн");
    await page.getByTestId("intake-goal").fill("Проверить спрос перед запуском");

    const confirm = page.getByTestId("intake-confirm-button");
    await expect(confirm).toBeEnabled({ timeout: 5_000 });
    await expect(page.getByTestId("intake-missing-fields")).toHaveCount(0);
  });

  test("missing required field shows readable alert with field link", async ({ page }) => {
    await page.goto("/workspace");
    await page.getByTestId("intent-card-validate-idea").click();
    await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("intake-goal").fill("");
    const alert = page.getByTestId("intake-missing-fields");
    await expect(alert).toBeVisible();
    await expect(page.getByTestId("intake-missing-link-analysis_goal")).toBeVisible();

    const contrast = await alert.evaluate((el) => {
      const style = window.getComputedStyle(el);
      const color = style.color;
      const bg = style.backgroundColor;
      return { color, bg };
    });
    expect(contrast.color).not.toBe("rgb(255, 255, 255)");
    expect(contrast.bg).not.toBe("rgb(255, 255, 255)");
  });

  test("optional unknown pricing does not block confirm", async ({ page }) => {
    await page.goto("/workspace");
    await page.getByTestId("intent-card-validate-idea").click();
    await expect(page.getByTestId("analysis-intake-panel")).toBeVisible({ timeout: 15_000 });

    await page.getByTestId("intake-product").fill("Курсы английского");
    await page.getByTestId("intake-audience").fill("Взрослые 25–45");
    await page.getByTestId("intake-geography").fill("Россия");
    await page.getByTestId("intake-goal").fill("Проверить спрос");

    const pricingRow = page.getByTestId("intake-pricing").locator("xpath=ancestor::label[1]");
    await pricingRow.getByRole("checkbox").check();

    await expect(page.getByTestId("intake-confirm-button")).toBeEnabled({ timeout: 5_000 });
    await expect(page.getByTestId("intake-research-gaps")).toBeVisible();
  });
});
