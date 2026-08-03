import { expect, test, type Page } from "@playwright/test";
import { assertBackendMode } from "./helpers/cph2";

async function registerCommercialUser(page: Page, prefix: string) {
  const email = `${prefix}.${Date.now()}@marketsynth.local`;
  const password = "e2e-skill-runtime-pass1";
  await page.goto("/register");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-display-name").fill("Skill Runtime User");
  await page.getByTestId("register-password").fill(password);
  await page.getByTestId("register-password-confirm").fill(password);
  await page.getByTestId("register-notice").check();
  await page.getByTestId("register-submit").click();
  await page.waitForURL(/\/workspace\/?$/, { timeout: 30_000 });
}

test.describe("Product Skill Runtime UI", () => {
  test("skills list shows copywriter available and avito unconfigured", async ({
    page,
  }) => {
    await assertBackendMode(page, "backend");
    await registerCommercialUser(page, "skill.rt");
    await page.goto("/workspace/settings/skills");
    await expect(page.getByTestId("product-skills-panel")).toBeVisible({
      timeout: 30_000,
    });
    await expect(
      page.getByTestId("product-skill-marketsynth.copywriter"),
    ).toBeVisible();
    await expect(
      page.getByTestId("product-skill-marketsynth.avito"),
    ).toBeVisible();
    await expect(
      page.getByTestId("product-skill-status-marketsynth.avito"),
    ).toContainText(/подключ|Needs connection|Требуется/i);
    await expect(page.getByTestId("product-skills-panel")).not.toContainText(
      "AVITO_CLIENT_SECRET",
    );
    await expect(page.getByTestId("product-skills-panel")).not.toContainText(
      "owner_preview",
    );
  });
});
