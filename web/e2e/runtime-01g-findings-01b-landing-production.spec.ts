import { expect, test } from "@playwright/test";

const productionPort = process.env.CPH2_PRODUCTION_PORT || "3000";
const landingUrl = `http://localhost:${productionPort}/`;

test.describe("FINDINGS-01B production build root landing", () => {
  test("GET / returns 200 on production server", async ({ page }) => {
    const response = await page.goto(landingUrl);
    expect(response?.status()).toBe(200);
    await expect(page.getByTestId("public-landing-page")).toBeVisible();
    await expect(page.getByTestId("public-landing-cta")).toBeVisible();
  });
});
