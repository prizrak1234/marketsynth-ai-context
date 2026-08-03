import { expect, type Page } from "@playwright/test";

import { apiJson, type E2ERunContext } from "./cph2";

const DRAFT_KEY = "marketsynth.product_alpha.intake_draft.v1";

export async function seedIntakeLocale(page: Page, options?: { developerMode?: boolean }): Promise<void> {
  await page.addInitScript(
    ({ devKey, developerMode }) => {
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
      window.localStorage.removeItem("marketsynth.e2e.api_key.v1");
      if (developerMode) {
        window.localStorage.setItem(devKey, "1");
      } else {
        window.localStorage.removeItem(devKey);
      }
    },
    { devKey: "marketsynth.home.developer_mode.v1", developerMode: options?.developerMode ?? false },
  );
}

export async function clearIntakeDraftStorage(page: Page): Promise<void> {
  await page.evaluate((draftKey) => {
    window.localStorage.removeItem(draftKey);
  }, DRAFT_KEY);
}

export async function waitForDraftPersisted(page: Page, timeoutMs = 10_000): Promise<string> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const draftId = await readDraftId(page);
    if (draftId.length > 0) return draftId;
    await page.waitForTimeout(250);
  }
  throw new Error("intake draft not persisted to localStorage");
}

export async function readDraftId(page: Page): Promise<string> {
  return page.evaluate((draftKey) => {
    const raw = window.localStorage.getItem(draftKey);
    if (!raw) return "";
    try {
      return (JSON.parse(raw) as { id?: string }).id ?? "";
    } catch {
      return "";
    }
  }, DRAFT_KEY);
}

export async function countBackendProjects(page: Page, ctx: E2ERunContext): Promise<number> {
  const projects = await apiJson<Array<{ id: string }>>(page, ctx, "GET", "/projects");
  return projects.length;
}

/** Minimal required fields through all seven steps to review (no research submit). */
export async function fillBasicsRequired(page: Page, projectName: string): Promise<void> {
  await page.locator("#name").fill(projectName);
  await page
    .locator("#ideaDescription")
    .fill("Проверить локальную клинику на устойчивость спроса до запуска рекламы");
  await page.locator("#businessType").selectOption("local_business");
  await page.locator("#projectStage").selectOption("preparing_launch");
  await page.locator("#geography").fill("Москва");
}

export async function fillIntakeWizardToReview(page: Page, projectName: string): Promise<void> {
  await page.goto("/workspace/projects/new");
  await expect(page.getByTestId("intake-wizard-shell")).toBeVisible({ timeout: 30_000 });

  await fillBasicsRequired(page, projectName);
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/idea/);

  await page.locator("#whatIsSold").fill("Стоматологические услуги для взрослых");
  await page.locator("#primaryProblem").fill("Пациенты откладывают лечение из-за страха и цены");
  await page.locator("#valueProposition").fill("Прозрачный прайс и бережное лечение");
  await page.locator("#deliveryModel").fill("clinic");
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/market/);

  await page.locator("#targetMarket").fill("Взрослые пациенты в Москве");
  await page.locator("#competitorsUnknown").check();
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/audience/);

  const seg = page.locator('[id^="seg-label-"]').first();
  await seg.fill("Владельцы клиник 1–3 кресла");
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/economics/);

  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/materials/);

  await expect(page.getByText("Product Alpha")).toHaveCount(0);
  await page.getByTestId("intake-next").click();
  await page.waitForURL(/\/workspace\/projects\/new\/review/);

  await expect(page.getByTestId("intake-review-customer")).toBeVisible({ timeout: 20_000 });
}

export async function assertReviewCustomerSafe(page: Page): Promise<void> {
  const review = page.getByTestId("intake-review-customer");
  await expect(page.getByTestId("intake-golden-path-submit")).toHaveCount(1);
  await expect(page.getByTestId("intake-review-back-edit")).toHaveCount(1);
  await expect(review).not.toContainText(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  await expect(review).not.toContainText(/fingerprint|backendSync|local_only|enum/i);
  await expect(page.getByTestId("intake-developer-diagnostics")).toHaveCount(0);
}

export async function installAutosaveFailure(page: Page): Promise<void> {
  await page.addInitScript((draftKey) => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function setItem(key: string, value: string) {
      if (key === draftKey) {
        throw new DOMException("QuotaExceededError", "QuotaExceededError");
      }
      return original.call(this, key, value);
    };
  }, DRAFT_KEY);
}
