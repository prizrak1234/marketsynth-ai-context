import { expect, test } from "@playwright/test";
import { assertBackendMode, fillIntakeWizard } from "./helpers/cph2";
import { HOME_DEVELOPER_MODE_KEY } from "../src/lib/home/developer-mode";

const ARTIFACT_DIR = "e2e-artifacts/ux-correction";

async function registerUser(page: import("@playwright/test").Page) {
  const email = `e2e.ux.${Date.now()}@marketsynth.local`;
  const password = "e2e-ux-pass12";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("UX User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
}

async function capture(page: import("@playwright/test").Page, name: string) {
  await page.screenshot({ path: `${ARTIFACT_DIR}/${name}.png`, fullPage: true });
}

test.describe("RUNTIME-01G UX correction — customer review surface", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.removeItem(key);
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
  });

  test("commercial review hides backend diagnostics from DOM", async ({ page }) => {
    await assertBackendMode(page, "backend");
    await registerUser(page);
    await fillIntakeWizard(page, "Онлайн-курсы английского для взрослых в России");
    await page.goto("/workspace/projects/new/review");

    await expect(page.getByTestId("intake-review-customer")).toBeVisible();
    await expect(page.getByTestId("intake-golden-path-submit")).toHaveCount(1);
    await expect(page.getByTestId("intake-review-back-edit")).toBeVisible();
    await expect(page.getByText("Сохранить полный бриф")).toHaveCount(0);
    await expect(page.getByText("Сохранить черновик")).toHaveCount(0);
    await expect(page.getByText("Backend Project")).toHaveCount(0);
    await expect(page.getByText("Brief fingerprint")).toHaveCount(0);
    await expect(page.getByText("conditionally_ready")).toHaveCount(0);
    await expect(page.getByText("Intake readiness")).toHaveCount(0);
    await expect(page.getByTestId("intake-developer-diagnostics")).toHaveCount(0);
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  });

  test("developer mode exposes collapsed diagnostics only", async ({ page }) => {
    test.skip(process.env.NODE_ENV === "production", "Developer diagnostics are dev-only");
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, "1");
      window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    }, HOME_DEVELOPER_MODE_KEY);
    await assertBackendMode(page, "backend");
    await registerUser(page);
    await fillIntakeWizard(page, "Сервис подписки на обеды для офисов");
    await page.goto("/workspace/projects/new/review");
    await expect(page.getByTestId("intake-developer-diagnostics")).toBeVisible();
    await expect(page.getByText("Backend Project ID")).toHaveCount(0);
    await page.getByTestId("intake-developer-diagnostics").getByRole("button").click();
    await expect(page.getByText("Backend Project ID")).toBeVisible();
    await page.screenshot({
      path: "e2e-artifacts/ux-correction/review-dev-diagnostics-1920.png",
      fullPage: true,
    });
  });

  test("golden path screenshots 1920 and 1366", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await assertBackendMode(page, "backend");
    await registerUser(page);

    await page.goto("/");
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await capture(page, "landing-1920");

    await page.goto("/workspace");
    await expect(page.getByTestId("canonical-commercial-entry")).toBeVisible();
    await capture(page, "workspace-1920");

    await page.goto("/workspace/projects/new");
    await expect(page.getByRole("heading", { name: /Проверка идеи перед исследованием/i })).toBeVisible();
    await capture(page, "intake-step1-1920");

    await page.locator("#name").fill("Маркетплейс локальных мастеров");
    await page.locator("#ideaDescription").fill("Платформа для поиска мастеров рядом с домом");
    await page.locator("#businessType").selectOption("marketplace");
    await page.locator("#projectStage").selectOption("validating_demand");
    await page.locator("#geography").fill("Казань");
    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/idea/);
    await page.locator("#whatIsSold").fill("Услуги мастеров на дому");
    await page.locator("#primaryProblem").fill("Сложно найти проверенного мастера");
    await page.locator("#valueProposition").fill("Рейтинг и гарантия качества");
    await page.locator("#deliveryModel").fill("marketplace");
    await capture(page, "intake-middle-1920");

    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/market/);
    await page.locator("#targetMarket").fill("Домовладельцы в Казани");
    await page.locator("#competitorsUnknown").check();
    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/audience/);
    const seg = page.locator('[id^="seg-label-"]').first();
    await seg.fill("Семьи с детьми");
    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/economics/);
    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/materials/);
    await page.getByRole("button", { name: "Далее" }).click();
    await page.waitForURL(/\/workspace\/projects\/new\/review/);
    await expect(page.getByTestId("intake-readiness-status")).toBeVisible();
    await capture(page, "review-1920");

    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("/");
    await capture(page, "landing-1366");
    await page.goto("/workspace/projects/new/review");
    await capture(page, "review-1366");
  });
});
