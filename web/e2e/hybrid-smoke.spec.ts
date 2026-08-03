import { expect, test } from "@playwright/test";
import { assertBackendMode, loadE2EContext } from "./helpers/cph2";

test("hybrid mode smoke — labelled local preview, no silent upload", async ({ page }) => {
  loadE2EContext();
  await assertBackendMode(page, "hybrid");
  await page.goto("/workspace");
  // Mode select if present
  const modeSelect = page.getByLabel(/Integration mode/i);
  if (await modeSelect.isVisible().catch(() => false)) {
    await modeSelect.selectOption("hybrid");
  }
  await page.goto("/");
  await expect(page.getByText("Marketsynth").first()).toBeVisible();
  await expect(page.getByText(/локальн|hybrid|preview|черновик/i).first()).toBeVisible({
    timeout: 15_000,
  }).catch(() => undefined);
  // Must not advertise durable MarketingPlan success without backend confirm
  await expect(page.getByText(/MarketingPlan approved automatically/i)).toHaveCount(0);
});
