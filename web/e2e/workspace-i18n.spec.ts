import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";

test("Russian localization + Home hero + Settings locale switch", async ({
  page,
}) => {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
    // Do not force-overwrite locale on every navigation — Settings switch must persist.
    if (!window.localStorage.getItem("marketsynth.ui.locale.v1")) {
      window.localStorage.setItem("marketsynth.ui.locale.v1", "ru");
    }
  });

  const email = `e2e.i18n.${Date.now()}@marketsynth.local`;
  const password = "e2e-i18n-pass12";
  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("I18n User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await expect(page.getByTestId("home-hero")).toBeVisible();
  await expect(page.getByTestId("brand-logo-hero")).toBeVisible();
  await expect(page.getByTestId("home-brand-caption")).toHaveCount(0);
  const logoBox = await page.getByTestId("brand-logo-hero").boundingBox();
  expect(logoBox?.height ?? 0).toBeGreaterThanOrEqual(170);
  await expect(page.getByTestId("home-greeting")).toContainText("Здравствуйте");
  await expect(page.getByTestId("home-support")).toContainText(
    "AI-маркетинговое агентство",
  );
  await expect(page.getByTestId("home-offer")).toContainText(
    "Прежде чем потратить ваши деньги",
  );
  await expect(page.getByTestId("home-offer")).toContainText(
    "мы поможем их сохранить",
  );
  await expect(page.getByTestId("home-economic-value")).toContainText(
    "снижение неопределённости",
  );
  await expect(page.getByTestId("home-usp-viability")).toContainText(
    "Не рекламируем слабые идеи",
  );
  await expect(page.getByTestId("home-usp-routing")).toContainText(
    "команду под конкретную задачу",
  );
  await expect(page.getByTestId("home-usp-evidence")).toContainText(
    "на чём основан вывод",
  );
  await expect(page.getByTestId("home-usp-control")).toContainText(
    "только после вашего подтверждения",
  );
  await expect(page.getByText("Evidence")).toHaveCount(0);
  await expect(page.getByText("Runtime")).toHaveCount(0);
  await expect(page.getByTestId("home-question")).toContainText(
    "Что будем делать сегодня",
  );
  // Economic value / USP must appear before the work question
  const uspBeforeQuestion = await page.evaluate(() => {
    const usp = document.querySelector('[data-testid="home-usp"]');
    const q = document.querySelector('[data-testid="home-question"]');
    if (!usp || !q) return false;
    return Boolean(
      usp.compareDocumentPosition(q) & Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
  expect(uspBeforeQuestion).toBe(true);
  await expect(page.getByTestId("nav-workspace")).toContainText("Главная");

  // Ensure question is below hero greeting in DOM order
  const order = await page.evaluate(() => {
    const hero = document.querySelector('[data-testid="home-hero"]');
    const q = document.querySelector('[data-testid="home-question"]');
    if (!hero || !q) return false;
    return Boolean(
      hero.compareDocumentPosition(q) & Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
  expect(order).toBe(true);

  await page.getByTestId("home-intent-input").fill(
    "Сделай контент-план для Telegram на месяц.",
  );
  await page.getByTestId("home-intent-submit").click();
  await expect(page.getByTestId("home-route-result")).toBeVisible();

  await page.getByTestId("nav-workspace-tasks").click();
  await expect(page.getByTestId("workspace-tasks-page")).toBeVisible();
  await expect(page.getByText("Task engine")).toHaveCount(0);
  const statusOptions = page.getByTestId("tasks-filter-status").locator("option");
  await expect(statusOptions.filter({ hasText: "Маршрутизирована" })).toHaveCount(1);
  await expect(statusOptions.filter({ hasText: /^routed$/ })).toHaveCount(0);
  const typeOptions = page.getByTestId("tasks-filter-type").locator("option");
  await expect(typeOptions.filter({ hasText: "Telegram-бот" })).toHaveCount(1);
  await expect(typeOptions.filter({ hasText: /^telegram_bot$/ })).toHaveCount(0);

  await page.goto("/workspace/strategies");
  await expect(page.getByTestId("workspace-strategies-page")).toBeVisible();
  await expect(page.getByText("MarketingStrategy")).toHaveCount(0);
  await expect(page.getByText("CONDITIONAL_GO")).toHaveCount(0);
  await expect(page.getByText("approved GO")).toHaveCount(0);
  await expect(page.getByTestId("strategies-empty")).toContainText(
    "Запускать при условиях",
  );

  await page.getByTestId("nav-workspace-settings").click();
  await expect(page.getByTestId("settings-language")).toBeVisible();
  await expect(page.getByTestId("settings-security")).toBeVisible();
  await expect(page.getByTestId("settings-notifications")).toBeVisible();
  expect(
    await page.getByTestId("settings-timezone").locator("option").count(),
  ).toBeGreaterThan(20);
  await expect(
    page.getByTestId("settings-timezone").locator('option[value="Europe/Moscow"]'),
  ).toHaveCount(1);
  await page.getByTestId("settings-locale").selectOption("en");
  await expect(page.getByTestId("nav-workspace")).toContainText("Home");
  await page.reload();
  await expect(page.getByTestId("nav-workspace")).toContainText("Home");
  await page.getByTestId("settings-locale").selectOption("ru");
  await expect(page.getByTestId("nav-workspace")).toContainText("Главная");
});
