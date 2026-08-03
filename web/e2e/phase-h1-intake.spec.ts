import { expect, test } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";

test("H1 conversational intake persists and appears in Tasks", async ({ page }) => {
  await assertBackendMode(page, "backend");
  await page.addInitScript(() => {
    window.localStorage.setItem("marketsynth.integration.mode.v1", "backend");
  });

  const email = `e2e.h1.${Date.now()}@marketsynth.local`;
  const password = "e2e-h1-pass-12xx";
  await page.goto("/register");
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("H1 User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });

  await page.getByTestId("home-intent-input").fill(
    "Напиши 10 постов для Telegram о бурении.",
  );
  await page.getByTestId("home-intent-submit").click();
  await expect(page.getByTestId("home-route-result")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("home-no-investigation")).toBeVisible();
  await expect(page.getByTestId("home-assigned-specialist")).toContainText(/Контент|Content/i);

  await page.reload();
  await expect(page.getByTestId("home-route-result").first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("Напиши 10 постов для Telegram о бурении.")).toBeVisible();

  await page.getByTestId("nav-workspace-tasks").click();
  await expect(page.getByTestId("workspace-tasks-page")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("task-card").first()).toBeVisible();
  await expect(page.getByTestId("task-card").first()).toContainText("постов");
  await expect(page.getByTestId("task-card").first()).toContainText("Маршрутизирована");
  await expect(page.getByTestId("task-card").first().getByText(/^routed$/)).toHaveCount(0);

  await page.goto("/workspace");
  await page.getByTestId("home-intent-input").fill("Нужен сайт.");
  await page.getByTestId("home-intent-submit").click();
  await expect(page.getByTestId("home-route-result").last()).toBeVisible();
  await expect(page.getByText(/лендинг|корпоративн|интернет-магазин/i)).toBeVisible();
});
