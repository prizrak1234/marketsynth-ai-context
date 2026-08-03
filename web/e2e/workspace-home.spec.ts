import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";

test("workspace opens conversational home", async ({ page }) => {
  await assertBackendMode(page, "backend");

  // Register ephemeral user for clean empty home
  const email = `e2e.home.${Date.now()}@marketsynth.local`;
  const password = "e2e-home-pass-12";
  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Home User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await expect(page.getByTestId("workspace-home")).toBeVisible();
  await expect(page.getByTestId("home-greeting")).toContainText("Здравствуйте");
  await expect(page.getByTestId("home-intent-input")).toBeVisible();
  await expect(page.getByTestId("home-scenarios")).toBeVisible();
  await expect(page.getByTestId("workspace-operations-dashboard")).toHaveCount(0);
  await expect(page.getByTestId("home-recent-projects-empty")).toBeVisible();

  // Content request → no Investigation
  await page.getByTestId("home-intent-input").fill(
    "Сделай контент-план для Telegram на месяц.",
  );
  await page.getByTestId("home-intent-submit").click();
  await expect(page.getByTestId("home-route-result")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("home-no-investigation")).toBeVisible();
  await expect(page.getByTestId("home-next-action")).toHaveAttribute(
    "href",
    /\/workspace\/tasks/,
  );

  // Idea → Project Intake
  await page.getByTestId("home-intent-input").fill("Хочу открыть стоматологию.");
  await page.getByTestId("home-intent-submit").click();
  await expect(page.locator('[data-route-category="idea_validation"]').last()).toBeVisible();
  await expect(page.getByTestId("home-next-action").last()).toHaveAttribute(
    "href",
    /\/workspace\/projects\/new/,
  );

  // Telegram bot → specialist
  await page.getByTestId("home-intent-input").fill(
    "Создай Telegram-бота для записи клиентов.",
  );
  await page.getByTestId("home-intent-submit").click();
  await expect(page.locator('[data-route-category="telegram_bot"]').last()).toBeVisible();
  await page.getByTestId("home-next-action").last().click();
  await page.waitForURL(/\/workspace\/tasks\?intent=telegram_bot/, { timeout: 15_000 });
  await expect(page.getByTestId("task-no-investigation")).toBeVisible();

  // Ambiguous → clarification
  await page.goto("/workspace");
  await page.getByTestId("home-intent-input").fill("Хочу рекламу");
  await page.getByTestId("home-intent-submit").click();
  await expect(page.locator('[data-route-kind="clarify"]').last()).toBeVisible();

  // Operations dashboard preserved
  await page.getByTestId("nav-workspace-projects").click();
  await page.waitForURL(/\/workspace\/projects\/?$/, { timeout: 15_000 });
  await expect(page.getByTestId("workspace-operations-dashboard")).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByTestId("workspace-home")).toHaveCount(0);

  // Nav: Главная
  await page.getByTestId("nav-workspace").click();
  await expect(page.getByTestId("workspace-home")).toBeVisible();
});
